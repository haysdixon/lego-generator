"""Turn a 3D model (.stl, .obj or MagicaVoxel .vox) into a shape file you can build.

    python import_model.py MODEL.stl --studs 16
    python import_model.py MODEL.obj --studs 20 --set 11045-1          # colours matched to the set's colours
    python import_model.py MODEL.vox --studs 12 --name robot
    python import_model.py MODEL.stl --studs 16 --colour red            # one colour for the whole model

It writes shapes/NAME.py and shapes/NAME.npz (the voxels). Then preview and build it like any other shape:

    python preview_shape.py shapes/NAME.py --bricks-only
    python make_model.py 11045-1 shapes/NAME.py out/NAME.ldr --scale 1 --bricks-only --render

--studs is the model's longest side, seen from above, in studs (at --scale 1). Colours come from the .obj's
materials (.mtl Kd) or the .vox palette and snap to the nearest LEGO colour. An .stl has no colours: use --colour.
Up: .stl and .vox are taken as Z-up, .obj as Y-up; change it with --up. Turn the model to face the front (-Z)
with --turn 90/180/270.
"""
import argparse, csv, gzip, os, re, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

COLOURS = {   # the same names the templates use -> Rebrickable colour id
    'black': 0, 'blue': 1, 'green': 2, 'red': 4, 'dark pink': 5, 'pink': 5, 'bright green': 10, 'yellow': 14,
    'white': 15, 'tan': 19, 'orange': 25, 'magenta': 26, 'lime': 27, 'dark tan': 28, 'bright pink': 29,
    'light pink': 29, 'lavender': 30, 'reddish brown': 70, 'brown': 70, 'light grey': 71, 'light gray': 71,
    'dark grey': 72, 'dark gray': 72, 'medium blue': 73, 'nougat': 84, 'medium nougat': 84, 'dark purple': 85,
    'bright light orange': 191, 'golden': 191, 'bright light yellow': 226, 'dark brown': 308, 'dark red': 320,
    'dark azure': 321, 'azure': 321, 'medium azure': 322,
}


# ---------------------------------------------------------------------------------------------------- readers
def read_stl(path):
    data = open(path, 'rb').read()
    n = struct.unpack('<I', data[80:84])[0] if len(data) >= 84 else 0
    if len(data) == 84 + 50 * n:      # binary
        rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n, offset=84)
        return rec['v'].astype(float), None
    nums = re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)', data)
    tris = np.array(nums, dtype=float).reshape(-1, 3, 3)
    return tris, None


def read_obj(path):
    verts, tris, mats, cur = [], [], [], None
    kd = {}
    folder = os.path.dirname(os.path.abspath(path))
    for line in open(path, encoding='utf-8', errors='replace'):
        t = line.split()
        if not t:
            continue
        if t[0] == 'v':
            verts.append([float(v) for v in t[1:4]])
        elif t[0] == 'f':
            idx = [int(v.split('/')[0]) for v in t[1:]]
            idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
            for a in range(1, len(idx) - 1):          # fan into triangles
                tris.append((idx[0], idx[a], idx[a + 1])); mats.append(cur)
        elif t[0] == 'usemtl':
            cur = ' '.join(t[1:])
        elif t[0] == 'mtllib':
            mtl = os.path.join(folder, ' '.join(t[1:]))
            if os.path.exists(mtl):
                name = None
                for ml in open(mtl, encoding='utf-8', errors='replace'):
                    m = ml.split()
                    if m and m[0] == 'newmtl':
                        name = ' '.join(m[1:])
                    elif m and m[0] == 'Kd' and name is not None:
                        kd[name] = tuple(float(v) for v in m[1:4])
    V = np.array(verts, float)
    tri = V[np.array(tris, int)]
    rgb = None
    if kd:
        rgb = np.array([[c * 255 for c in kd.get(m, (0.6, 0.6, 0.6))] for m in mats], float)
    return tri, rgb


def read_vox(path):
    """MagicaVoxel: returns (occupancy[x, y, z] bool, rgb[x, y, z, 3]) in the file's own axes (Z up)."""
    data = open(path, 'rb').read()
    if data[:4] != b'VOX ':
        sys.exit(f'{path} is not a MagicaVoxel file')
    pos, size, xyzi, pal = 8, None, None, None
    while pos + 12 <= len(data):
        cid = data[pos:pos + 4]; n, m = struct.unpack('<II', data[pos + 4:pos + 12]); body = data[pos + 12:pos + 12 + n]
        if cid == b'MAIN':
            pos += 12; continue                     # children follow directly
        if cid == b'SIZE' and size is None:
            size = struct.unpack('<III', body[:12])
        elif cid == b'XYZI' and xyzi is None:
            k = struct.unpack('<I', body[:4])[0]
            xyzi = np.frombuffer(body[4:4 + 4 * k], np.uint8).reshape(-1, 4)
        elif cid == b'RGBA':
            pal = np.frombuffer(body[:1024], np.uint8).reshape(256, 4)[:, :3].astype(float)
        pos += 12 + n + m
    if size is None or xyzi is None:
        sys.exit(f'{path}: no voxels found')
    occ = np.zeros(size, bool); rgb = np.zeros(size + (3,), float)
    occ[xyzi[:, 0], xyzi[:, 1], xyzi[:, 2]] = True
    if pal is None:   # no palette in the file: plain grey (use --colour)
        rgb[...] = 160
    else:
        rgb[xyzi[:, 0], xyzi[:, 1], xyzi[:, 2]] = pal[(xyzi[:, 3].astype(int) - 1) % 256]
    return occ, rgb


# ---------------------------------------------------------------------------------------------------- voxelise
def cast(tri, shape, axis, rgb):
    """Shoot rays along one axis through the cell centres of a grid in cell units. Returns, per cell: inside or
    not, distance to the nearest surface along the ray, and that surface's colour."""
    b_ax, c_ax = [a for a in range(3) if a != axis]
    nb, nc, na = shape[b_ax], shape[c_ax], shape[axis]
    inside = np.zeros(shape, bool); dist = np.full(shape, np.inf); colr = np.zeros(shape + (3,), float)
    P = tri[:, :, [b_ax, c_ax, axis]]
    bmin, bmax = P[:, :, 0].min(1), P[:, :, 0].max(1)
    cmin, cmax = P[:, :, 1].min(1), P[:, :, 1].max(1)
    cc = np.arange(nc) + 0.5 + 1.3e-4               # tiny offset so rays miss edges and corners
    for b in range(nb):
        rb = b + 0.5 + 0.7e-4
        sel = np.nonzero((bmin <= rb) & (bmax >= rb))[0]
        if not len(sel):
            continue
        T = P[sel]
        x0, y0 = T[:, 0, 0], T[:, 0, 1]; x1, y1 = T[:, 1, 0], T[:, 1, 1]; x2, y2 = T[:, 2, 0], T[:, 2, 1]
        det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        ok = np.abs(det) > 1e-12
        T, sel, det = T[ok], sel[ok], det[ok]
        x0, y0, z0 = T[:, 0, 0], T[:, 0, 1], T[:, 0, 2]; x1, y1, z1 = T[:, 1, 0], T[:, 1, 1], T[:, 1, 2]
        x2, y2, z2 = T[:, 2, 0], T[:, 2, 1], T[:, 2, 2]
        facing = np.sign((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0))   # which way each face crosses the ray
        # barycentric coordinates of (rb, c) for every triangle x every c
        l1 = ((y1 - y2)[:, None] * (rb - x2)[:, None] + (x2 - x1)[:, None] * (cc[None, :] - y2[:, None])) / det[:, None]
        l2 = ((y2 - y0)[:, None] * (rb - x2)[:, None] + (x0 - x2)[:, None] * (cc[None, :] - y2[:, None])) / det[:, None]
        l3 = 1 - l1 - l2
        hit = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        ti, ci = np.nonzero(hit)
        if not len(ti):
            continue
        av = l1[ti, ci] * z0[ti] + l2[ti, ci] * z1[ti] + l3[ti, ci] * z2[ti]
        for c in np.unique(ci):
            m = ci == c
            order = np.argsort(av[m]); h = av[m][order]; tid = sel[ti[m]][order]
            wind = np.concatenate([[0], np.cumsum(facing[ti[m]][order])])
            centres = np.arange(na) + 0.5
            below = np.searchsorted(h, centres)
            j = np.clip(below, 1, len(h)) - 1; k = np.clip(below, 0, len(h) - 1)
            dj, dk = np.abs(centres - h[j]), np.abs(centres - h[k])
            near = np.where(dj <= dk, j, k); d = np.minimum(dj, dk)
            idx = [slice(None)] * 3; idx[b_ax] = b; idx[c_ax] = c
            # inside by the winding number (copes with overlapping parts), or by the even-odd rule (copes with
            # faces that point the wrong way)
            inside[tuple(idx)] = (wind[below] != 0) | (below % 2 == 1)
            dist[tuple(idx)] = d
            if rgb is not None:
                colr[tuple(idx)] = rgb[tid[near]]
    return inside, dist, colr


def voxelise_mesh(tri, rgb, studs):
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    size = hi - lo
    s = studs * 20 / max(size[0], size[2])          # LDraw units per model unit
    cell = np.array([20.0, 8.0, 20.0])
    shape = tuple(int(v) for v in np.maximum(np.ceil(size * s / cell), 1))
    g = (tri - lo) * s / cell                        # in cell units, model corner at 0
    pad = (np.array(shape) - size * s / cell) / 2   # centre the model in its cells
    pad[1] = 0
    g = g + pad
    votes = np.zeros(shape, int); best = np.full(shape, np.inf); colr = np.zeros(shape + (3,), float)
    for axis in range(3):
        ins, d, c = cast(g, shape, axis, rgb)
        votes += ins
        d = d * cell[axis]                            # compare distances in LDraw units
        closer = d < best
        best[closer] = d[closer]; colr[closer] = c[closer]
    return votes >= 2, colr                          # inside if 2 of the 3 directions agree (forgives small holes)


def voxelise_vox(occ, rgb, studs):
    sx, sy, sz = occ.shape                           # Z up in the file
    v = studs * 20 / max(sx, sy)                     # one voxel, in LDraw units
    shape = (max(int(np.ceil(sx * v / 20)), 1), max(int(np.ceil(sz * v / 8)), 1), max(int(np.ceil(sy * v / 20)), 1))
    ix = np.minimum(((np.arange(shape[0]) + 0.5) * 20 / v).astype(int), sx - 1)
    iy = np.minimum(((np.arange(shape[2]) + 0.5) * 20 / v).astype(int), sy - 1)
    iz = np.minimum(((np.arange(shape[1]) + 0.5) * 8 / v).astype(int), sz - 1)
    A, Bz, C = np.meshgrid(ix, iz, iy, indexing='ij')   # grid x <- file x, grid y (up) <- file z, grid z <- file y
    return occ[A, C, Bz], rgb[A, C, Bz]


# ---------------------------------------------------------------------------------------------------- colours
def lab(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def palette(data, set_num):
    """(ids, rgb) of the colours to match: the set's solid colours with --set, else the templates' list"""
    rgb = {}
    cf = os.path.join(data, 'colors.csv.gz')
    trans = set()
    if os.path.exists(cf):
        for r in csv.DictReader(gzip.open(cf, 'rt', encoding='utf-8')):
            rgb[int(r['id'])] = tuple(int(r['rgb'][i:i + 2], 16) for i in (0, 2, 4))
            if r['is_trans'] in ('True', 't'):
                trans.add(int(r['id']))
    if not rgb:
        sys.exit(f'colour list not found in {data}: run  python get_data.py  first')
    ids = sorted(set(COLOURS.values()))
    if set_num:
        inv = {r['id'] for r in csv.DictReader(gzip.open(os.path.join(data, 'inventories.csv.gz'), 'rt', encoding='utf-8'))
               if r['set_num'] == set_num}
        if not inv:
            sys.exit(f'set {set_num} not found (use the full number, e.g. 11045-1)')
        ids = sorted({int(r['color_id']) for r in csv.DictReader(gzip.open(os.path.join(data, 'inventory_parts.csv.gz'), 'rt', encoding='utf-8'))
                      if r['inventory_id'] in inv} - trans)
    ids = [i for i in ids if i in rgb]
    return np.array(ids), np.array([rgb[i] for i in ids], float)


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Turn a 3D model into a shape file.', epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model', help='.stl, .obj or .vox file')
    ap.add_argument('--studs', type=float, default=16, help="longest side seen from above, in studs (default 16)")
    ap.add_argument('--name', help='shape name (default: the model file name)')
    ap.add_argument('--colour', '--color', default='', help='one colour for the whole model (name or Rebrickable id)')
    ap.add_argument('--set', default='', help='match colours to this set\'s colours, e.g. 11045-1')
    ap.add_argument('--up', choices=('y', 'z'), help='which axis is up in the file (default: z for .stl/.vox, y for .obj)')
    ap.add_argument('--turn', type=int, default=0, choices=(0, 90, 180, 270), help='turn the model to face the front')
    ap.add_argument('--outdir', default=os.path.join(HERE, 'shapes'))
    ap.add_argument('--data', default=os.environ.get('REMAKE_DATA', os.path.join(HERE, 'data')))
    a = ap.parse_args()

    ext = os.path.splitext(a.model)[1].lower()
    name = re.sub(r'\W+', '_', a.name or os.path.splitext(os.path.basename(a.model))[0]).strip('_').lower() or 'model'
    up = a.up or ('y' if ext == '.obj' else 'z')

    if ext == '.vox':
        occ, rgb = read_vox(a.model)
        if up == 'y':
            occ, rgb = occ.transpose(0, 2, 1), rgb.transpose(0, 2, 1, 3)
        solid, colr = voxelise_vox(occ, rgb, a.studs)
        has_colour = True
    elif ext in ('.stl', '.obj'):
        tri, rgb = read_stl(a.model) if ext == '.stl' else read_obj(a.model)
        if not len(tri):
            sys.exit(f'{a.model}: no triangles found')
        # into the shape files' axes: Y up, the model's front toward -Z, without mirroring it
        if up == 'z':
            tri = tri[:, :, [0, 2, 1]]                        # (x, y, z) -> (x, z, y)
        else:
            tri = tri * np.array([1, 1, -1])                  # (x, y, z) -> (x, y, -z)
        solid, colr = voxelise_mesh(tri, rgb, a.studs)
        has_colour = rgb is not None
    else:
        sys.exit('use a .stl, .obj or .vox file')

    for _ in range(a.turn // 90):                             # quarter turns about the vertical axis
        solid = np.rot90(solid, axes=(0, 2)); colr = np.rot90(colr, axes=(0, 2))
    if not solid.any():
        sys.exit('nothing came out solid: is the model closed (watertight)? try a bigger --studs')

    # colours -> Rebrickable ids
    if a.colour:
        n = a.colour.strip().lower()
        one = int(n) if n.isdigit() else COLOURS.get(n)
        if one is None:
            sys.exit(f'unknown colour "{a.colour}". Use a Rebrickable id or one of: ' + ', '.join(sorted(COLOURS)))
        col = np.full(solid.shape, one, np.int32)
    elif has_colour:
        ids, prgb = palette(a.data, a.set)
        pl = lab(prgb)
        cells = lab(colr[solid])
        pick = np.argmin(((cells[:, None, :] - pl[None, :, :]) ** 2).sum(-1), 1)
        col = np.full(solid.shape, 71, np.int32)
        col[solid] = ids[pick]
    else:
        col = np.full(solid.shape, 71, np.int32)              # light grey
        print('this model has no colours: it is light grey (choose one with --colour, or edit COLOUR in the shape file)')

    nx, ny, nz = solid.shape
    os.makedirs(a.outdir, exist_ok=True)
    npz = os.path.join(a.outdir, name + '.npz')
    np.savez_compressed(npz, solid=solid, col=col)

    # what to expect: cells with nothing under them that are not on the table hang in the air
    below = np.zeros_like(solid); below[:, 1:, :] = solid[:, :-1, :]
    hanging = solid & ~below; hanging[:, 0, :] = False
    used = sorted({int(c) for c in np.unique(col[solid])})
    names = {v: k for k, v in reversed(list(COLOURS.items()))}

    items = [f'{k!r}: {v}' for k, v in COLOURS.items()]
    colours_src = '{\n' + ''.join('    ' + ', '.join(items[i:i + 6]) + ',\n' for i in range(0, len(items), 6)) + '}'
    py = os.path.join(a.outdir, name + '.py')
    with open(py, 'w', encoding='utf-8') as f:
        f.write(f"""GRID = ({nx + 4}, {nz + 4}, {ny + 6})   # the imported model plus a margin, at --scale 1. Bigger scales need a bigger GRID.
TITLE = {name.replace('_', ' ').title()!r}

# Made by import_model.py from {os.path.basename(a.model)} ({a.studs:g} studs long). The voxels are in {name}.npz,
# next to this file: keep the two together. Colours used: {', '.join(names.get(c, str(c)) for c in used)}.
#     python preview_shape.py shapes/{name}.py --bricks-only
#     python make_model.py 11045-1 shapes/{name}.py out/{name}.ldr --scale 1 --bricks-only --render
# Front is -Z. To change the size, run import_model.py again with another --studs (or build at a --scale below 1).

COLOUR = ''    # '' keeps the model's colours; a colour name or Rebrickable id paints the whole model, e.g. 'red'
SWAP = ''      # change some colours, e.g. '71=15, 72=0' (Rebrickable ids: from=to)

COLOURS = {colours_src}

for _k, _v in list(locals().items()):   # --var COLOUR=red
    if _k.isupper() and _k in os.environ:
        locals()[_k] = os.environ[_k]
_g = locals()

_d = np.load(os.path.join(SHAPE_DIR, {name + '.npz'!r}))
_s, _c = _d['solid'], _d['col']
_nx, _ny, _nz = _s.shape
ix = np.floor(X / 20 + _nx / 2).astype(int)   # which saved cell each grid cell falls in
iy = np.floor(Y / 8).astype(int)
iz = np.floor(Z / 20 + _nz / 2).astype(int)
ok = (ix >= 0) & (ix < _nx) & (iy >= 0) & (iy < _ny) & (iz >= 0) & (iz < _nz)
solid = np.zeros(X.shape, bool)
col = np.zeros(X.shape, int)
solid[ok] = _s[ix[ok], iy[ok], iz[ok]]
col[ok] = _c[ix[ok], iy[ok], iz[ok]]
if str(_g['COLOUR']).strip():
    _n = str(_g['COLOUR']).strip().lower()
    col[:] = int(_n) if _n.isdigit() else COLOURS[_n]
for _pair in str(_g['SWAP']).replace(' ', '').split(','):
    if '=' in _pair:
        _a, _b = _pair.split('=')
        col[col == int(_a)] = int(_b)
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
""")
    print(f'wrote {os.path.normpath(py)} and {os.path.basename(npz)}')
    print(f'  {nx} x {nz} studs, {ny} plates ({ny / 3:.1f} bricks) tall; {int(solid.sum())} cells; colours: '
          + ', '.join(names.get(c, str(c)) for c in used))
    share = hanging.sum() / max(solid.sum(), 1)
    if share > 0.05:
        print(f'  note: {share:.0%} of the cells hang over empty space. Overhangs can come out as loose pieces:'
              ' see "What builds well" in MAKING_SHAPES.md')


if __name__ == '__main__':
    main()
