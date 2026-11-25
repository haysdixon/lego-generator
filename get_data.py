"""Download what the generator needs (about 100 MB, once):
  - Rebrickable's free database downloads (every set's parts list) into ./data
  - the LDraw parts library (3D shapes of every LEGO part) into ./ldraw

    python get_data.py            # both
    python get_data.py --refresh  # re-download the Rebrickable files (new sets appear over time)
"""
import argparse, os, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RB = 'https://cdn.rebrickable.com/media/downloads/{}.csv.gz'
RB_FILES = ['sets', 'themes', 'inventories', 'inventory_parts', 'parts', 'colors']
LDRAW = 'https://library.ldraw.org/library/updates/complete.zip'

ap = argparse.ArgumentParser()
ap.add_argument('--refresh', action='store_true')
a = ap.parse_args()


def fetch(url, dest):
    print('downloading', url)
    req = urllib.request.Request(url, headers={'User-Agent': 'lego-remake (python urllib)'})
    with urllib.request.urlopen(req) as r, open(dest + '.part', 'wb') as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    os.replace(dest + '.part', dest)


os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
for f in RB_FILES:
    dest = os.path.join(HERE, 'data', f + '.csv.gz')
    if a.refresh or not os.path.exists(dest):
        fetch(RB.format(f), dest)

lib = os.path.join(HERE, 'ldraw')
if not os.path.exists(os.path.join(lib, 'LDConfig.ldr')):
    z = os.path.join(HERE, 'data', 'ldraw-complete.zip')
    if not os.path.exists(z):
        fetch(LDRAW, z)
    print('unzipping the LDraw library')
    with zipfile.ZipFile(z) as zf:
        zf.extractall(HERE)          # the zip holds a top-level ldraw/ folder
    if not os.path.exists(os.path.join(lib, 'LDConfig.ldr')):
        sys.exit('unexpected LDraw zip layout; unzip it so that ldraw/LDConfig.ldr exists')
print('ready: data/ and ldraw/ are in place')
