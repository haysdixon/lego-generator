"""Load a shape file into a voxel grid. Shared by generate.py and find_sets.py.

Grid: cells are 20 LDU (1 stud) in x and z, 8 LDU (1 plate) in y. Shape files work in LDU before scaling
(front = -Z, Y up from 0) and may set GRID = (NX, NZ, NY) at the top to change the grid size (default 18, 18, 48).
Helpers available to shape files: np, os, X, Y, Z, ell(center, radii), sell(center, radii, p) (superellipsoid,
p=2 is an ellipsoid, bigger p is boxier), box(lo, hi), SC, snap(v) (raw x/z onto a stud boundary), studs(n) and
SHAPE_DIR (the shape file's folder, for shapes that load a saved voxel file, as import_model.py writes)."""
import os, re
import numpy as np


def load(path, SC):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'^GRID\s*=\s*\((\d+),\s*(\d+),\s*(\d+)\)', src, re.M)
    NX, NZ, NY = (int(v) for v in m.groups()) if m else (18, 18, 48)
    cx = (np.arange(NX) - NX / 2 + 0.5) * 20; cz = (np.arange(NZ) - NZ / 2 + 0.5) * 20; cy = (np.arange(NY) + 0.5) * 8
    X, Y, Z = np.meshgrid(cx, cy, cz, indexing='ij'); X, Y, Z = X / SC, Y / SC, Z / SC

    def ell(c, rad):
        return ((X - c[0]) / rad[0]) ** 2 + ((Y - c[1]) / rad[1]) ** 2 + ((Z - c[2]) / rad[2]) ** 2 <= 1

    def sell(c, rad, p=4):
        return (np.abs((X - c[0]) / rad[0]) ** p + np.abs((Y - c[1]) / rad[1]) ** p + np.abs((Z - c[2]) / rad[2]) ** p) <= 1

    def box(lo, hi):
        return (X >= lo[0]) & (X <= hi[0]) & (Y >= lo[1]) & (Y <= hi[1]) & (Z >= lo[2]) & (Z <= hi[2])

    def snap(v, unit=20):
        """move a raw x/z coordinate onto the nearest stud boundary after scaling (so a 2-stud feature is exactly 2 studs)"""
        return round(v * SC / unit) * unit / SC

    def studs(n):
        """n studs expressed in raw (pre-scale) LDU"""
        return n * 20 / SC

    ns = dict(np=np, os=os, X=X, Y=Y, Z=Z, SC=SC, ell=ell, sell=sell, box=box, snap=snap, studs=studs,
              SHAPE_DIR=os.path.dirname(os.path.abspath(path)))
    exec(src, ns)
    solid, col = ns['solid'], ns['col']
    # COLMAP="29=5,19=84": use a set's own colours for ones it lacks (applied to the colour grid and KEYC)
    cmap = {int(a): int(b) for a, b in (t.split('=') for t in os.environ.get('COLMAP', '').split(',') if t)}
    for a, b in cmap.items():
        col[col == a] = b
    ns['KEYC'] = tuple(dict.fromkeys(cmap.get(c, c) for c in ns['KEYC']))
    # QY=3: quantise heights to whole bricks (for brick-only sets): each 3-layer band takes its majority
    qy = int(os.environ.get('QY', '1'))
    if qy > 1:
        for y0 in range(0, NY, qy):
            band = solid[:, y0:y0 + qy, :]
            keep = band.sum(1) * 2 >= band.shape[1]
            mid = col[:, min(y0 + qy // 2, NY - 1), :]
            solid[:, y0:y0 + qy, :] = keep[:, None, :]
            col[:, y0:y0 + qy, :] = mid[:, None, :]
    return dict(NX=NX, NZ=NZ, NY=NY, X=X, Y=Y, Z=Z, solid=solid, col=col, KEYC=ns['KEYC'], TITLE=ns['TITLE'])


def erode(m, ground=False):
    e = m.copy()
    for ax in range(3):
        for s in (1, -1):
            sh = np.roll(m, s, axis=ax); idx = [slice(None)] * 3; idx[ax] = 0 if s == 1 else -1
            sh[tuple(idx)] = (ground and ax == 1 and s == 1)
            e &= sh
    return e


def needs(shape):
    """Cells per colour the build must fill: visible cells and the 2-thick shell (generate.py leaves the core hollow)."""
    solid, col = shape['solid'], shape['col']
    vis = solid & ~erode(solid, True)
    shell = solid & ~erode(erode(solid))
    out = {}
    for c in np.unique(col[shell]):
        out[int(c)] = dict(visible=int((vis & (col == c)).sum()), shell=int((shell & (col == c)).sum()))
    return out
