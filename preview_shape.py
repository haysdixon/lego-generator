"""Quick look at a shape file BEFORE building it: draws the shape as little blocks, from two sides, in seconds.

    python preview_shape.py shapes/my_animal.py
    python preview_shape.py shapes/pig.py --scale 0.9 --bricks-only

Saves SHAPE_preview.png next to the shape file (or --out FILE). The preview shows the target shape, not real
LEGO pieces: use it to check proportions and colours, then build with make_model.py.
"""
import argparse, csv, gzip, os, sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'generator'))
import shapelib

ap = argparse.ArgumentParser(description='Quick block preview of a shape file.')
ap.add_argument('shape')
ap.add_argument('--scale', type=float, default=1.0, help='same as make_model.py (default 1)')
ap.add_argument('--bricks-only', action='store_true', help='same as make_model.py')
ap.add_argument('--colmap', default='')
ap.add_argument('--var', action='append', default=[], metavar='KEY=VALUE')
ap.add_argument('--out')
ap.add_argument('--data', default=os.environ.get('REMAKE_DATA', os.path.join(HERE, 'data')))
a = ap.parse_args()

os.environ['QY'] = '3' if a.bricks_only else '1'
os.environ['COLMAP'] = a.colmap
for kv in a.var:
    k, _, v = kv.partition('=')
    os.environ[k] = v
shp = shapelib.load(a.shape, a.scale)
solid, col = shp['solid'], shp['col']           # [x, y, z]: x = length, y = up (plates), z = width

rgb = {}
cf = os.path.join(a.data, 'colors.csv.gz')
if os.path.exists(cf):
    for r in csv.DictReader(gzip.open(cf, 'rt', encoding='utf-8')):
        rgb[int(r['id'])] = tuple(int(r['rgb'][i:i + 2], 16) for i in (0, 2, 4))
FALLBACK = {0: (5, 19, 29), 15: (255, 255, 255), 4: (201, 26, 9), 84: (170, 125, 85), 191: (248, 187, 61), 27: (187, 233, 11),
            5: (200, 112, 160), 19: (228, 205, 158), 29: (228, 173, 200), 321: (7, 139, 201)}


def shade(c, f):
    base = rgb.get(int(c)) or FALLBACK.get(int(c), (150, 150, 150))
    return tuple(int(min(255, v * f)) for v in base)


def view(flip):
    """isometric blocks; flip=True looks from the other corner"""
    s = solid[::-1, :, ::-1] if flip else solid
    c = col[::-1, :, ::-1] if flip else col
    NX, NY, NZ = s.shape
    U, V = 14, 0.4 * 14 * 1.15          # cell width on screen, plate height on screen (8/20 of a stud)
    pts = lambda x, y, z: ((x - z) * U * 0.866, (x + z) * U * 0.5 - y * V)
    W_ = int((NX + NZ) * U * 0.9) + 40; H_ = int((NX + NZ) * U * 0.5 + NY * V) + 40
    img = Image.new('RGB', (W_, H_), (245, 244, 240)); d = ImageDraw.Draw(img)
    ox, oy = NZ * U * 0.866 + 20, NY * V + 20
    filled = np.argwhere(s)
    order = filled[np.lexsort((filled[:, 1], filled[:, 0] + filled[:, 2]))]   # back to front, bottom to top
    for x, y, z in order:
        cc = c[x, y, z]
        def P(px, py, pz):
            u, v = pts(px, py, pz); return (u + ox, v + oy)
        top = y + 1 >= NY or not s[x, y + 1, z]
        if top:
            d.polygon([P(x, y + 1, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)], fill=shade(cc, 1.0), outline=shade(cc, 0.8))
        if x + 1 >= NX or not s[x + 1, y, z]:
            d.polygon([P(x + 1, y, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x + 1, y, z + 1)], fill=shade(cc, 0.78))
        if z + 1 >= NZ or not s[x, y, z + 1]:
            d.polygon([P(x, y, z + 1), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)], fill=shade(cc, 0.62))
    return img.crop(ImageChops.difference(img, Image.new('RGB', img.size, (245, 244, 240))).getbbox())


views = [view(False), view(True)]
pad = 30
sheet = Image.new('RGB', (sum(v.width for v in views) + pad * 3, max(v.height for v in views) + pad * 2), (245, 244, 240))
x = pad
for v in views:
    sheet.paste(v, (x, pad)); x += v.width + pad
out = a.out or os.path.splitext(a.shape)[0] + '_preview.png'
sheet.save(out)
n = int(solid.sum())
print(f'saved {out}  ({shp["TITLE"]}: {n} filled cells)')
