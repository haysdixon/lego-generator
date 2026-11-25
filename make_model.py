"""Build a new LEGO model from one set's parts.

    python make_model.py SET SHAPE.py OUT.ldr [options]

Runs the generator with several random seeds, keeps the cleanest result, and (optionally) renders it and writes
step-by-step instructions. Example (the Highland cow from LEGO 11045):

    python make_model.py 11045-1 shapes/highland.py out/highland.ldr --scale 0.7 --bricks-only --render

Several models from ONE box: build them one after another and pass the earlier ones with --after, so each new
model only uses the bricks the others left over.
"""
import argparse, collections, concurrent.futures as cf, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, 'generator')

ap = argparse.ArgumentParser(description='Build a new LEGO model from one set\'s parts.',
                             formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
ap.add_argument('set', help='Rebrickable set number, e.g. 11045-1')
ap.add_argument('shape', help='shape file (see shapes/)')
ap.add_argument('out', help='output .ldr file (open it in LeoCAD or Stud.io)')
ap.add_argument('--scale', type=float, default=0.8, help='size of the model (bigger = more pieces); default 0.8')
ap.add_argument('--seeds', default='1-4', help='random seeds to try, e.g. 1-6 or 1,3,5; default 1-4')
ap.add_argument('--tries', type=int, default=25, help='attempts per layer inside one run; default 25')
ap.add_argument('--bricks-only', action='store_true',
                help='snap heights to whole bricks; use for sets with few plates (e.g. 11045 Classic boxes)')
ap.add_argument('--colmap', default='', help='replace colours the set lacks, e.g. 19=84,29=5 (Rebrickable colour ids)')
ap.add_argument('--after', nargs='*', default=[], metavar='LDR',
                help='models already built from the same box; their parts are set aside first')
ap.add_argument('--add', default='', help='extra loose parts on top of the set, PART:COLOUR:QTY,...')
ap.add_argument('--var', action='append', default=[], metavar='KEY=VALUE',
                help='shape setting, e.g. --var COAT=191 (see the top of each shape file); repeatable')
ap.add_argument('--render', action='store_true', help='also save OUT.png (three views)')
ap.add_argument('--instructions', action='store_true', help='also write step-by-step instructions (needs LeoCAD)')
ap.add_argument('--data', default=os.environ.get('REMAKE_DATA', os.path.join(HERE, 'data')),
                help='Rebrickable CSV folder (get_data.py fills ./data)')
ap.add_argument('--lib', default=os.environ.get('LDRAW_LIB', os.path.join(HERE, 'ldraw')),
                help='LDraw parts library (get_data.py fills ./ldraw)')
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2, help='seeds to run at once')
a = ap.parse_args()

for need, what in ((os.path.join(a.data, 'inventory_parts.csv.gz'), 'Rebrickable data'), (os.path.join(a.lib, 'LDConfig.ldr'), 'LDraw library')):
    if not os.path.exists(need):
        sys.exit(f'{what} not found at {os.path.dirname(need)}: run  python get_data.py  first')

seeds = []
for part in a.seeds.split(','):
    lo, _, hi = part.partition('-')
    seeds += list(range(int(lo), int(hi or lo) + 1))


def ldr_counts(path):
    c = collections.Counter()
    for line in open(path, encoding='utf-8', errors='replace'):
        t = line.split()
        if len(t) >= 15 and t[0] == '1':
            c[(t[14].lower().removesuffix('.dat'), t[1])] += 1
    return c


add = [t for t in a.add.split(',') if t]
for f in a.after:   # set aside what the earlier models use: negative extra parts
    add += [f'{p}:{c}:-{n}' for (p, c), n in ldr_counts(f).items()]

env = dict(os.environ, CURVEFIRST='1', MAXPRO='2', COLMAP=a.colmap, QY='3' if a.bricks_only else '1', ADD=','.join(add))
for kv in a.var:
    k, _, v = kv.partition('=')
    env[k] = v

out = os.path.abspath(a.out)
base = os.path.splitext(out)[0]
runs = os.path.join(os.path.dirname(out), '_runs')
os.makedirs(runs, exist_ok=True)
name = os.path.basename(base)


def run(seed):
    ldr = os.path.join(runs, f'{name}_{seed}.ldr'); log = ldr[:-4] + '.log'
    with open(log, 'w') as fh:
        subprocess.run([sys.executable, os.path.join(GEN, 'generate.py'), a.data, a.lib, a.set, a.shape, ldr,
                        str(a.scale), str(seed), str(a.tries)], env=env, stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding='utf-8', errors='replace').read()
    m = re.search(r'^SUMMARY (.*)$', txt, re.M)
    if not m:
        return seed, None, txt.strip().splitlines()[-1] if txt.strip() else 'no output'
    t = m.group(1).split()
    s = {t[i]: int(t[i + 1]) for i in range(0, len(t) - 1, 2) if t[i + 1].lstrip('-').isdigit()}
    return seed, s, ldr


print(f'building {name} from set {a.set}: scale {a.scale}, seeds {seeds}' + (f', after {len(a.after)} model(s)' if a.after else ''))
results = []
with cf.ThreadPoolExecutor(a.jobs) as ex:
    for seed, s, info in ex.map(run, seeds):
        if s is None:
            print(f'  seed {seed}: failed ({info})')
            continue
        print(f"  seed {seed}: {s['pieces']} pieces, {s['dropped']} loose (removed), {s['missing']} cells unfilled, "
              f"{s['wrongcolour']} off-colour, {s['edits']} cells changed")
        results.append((seed, s, info))
if not results:
    sys.exit('every seed failed; see the logs in ' + runs)

# cleanest first: nothing removed, nothing missing, right colours, then fewest shape edits
seed, s, best = min(results, key=lambda r: (r[1]['dropped'], r[1]['missing'], r[1]['wrongcolour'], r[1]['edits'], r[0]))
shutil.copy(best, out)
print(f'best: seed {seed} -> {out} ({s["pieces"]} pieces, {s["steps"]} steps)')

if a.render:
    from PIL import Image
    views = []
    for tag, yaw, pitch in (('a', -30, 30), ('b', 140, 35), ('c', 0, 75)):
        png = os.path.join(runs, f'_{name}_{tag}.png')
        subprocess.run([sys.executable, os.path.join(GEN, 'render.py'), GEN, a.lib, out, png, str(yaw), str(pitch), '900'],
                       stdout=subprocess.DEVNULL, check=True)
        views.append(Image.open(png))
    sheet = Image.new('RGB', (sum(v.width for v in views), max(v.height for v in views)), (245, 244, 240))
    x = 0
    for v in views:
        sheet.paste(v, (x, 0)); x += v.width
    sheet.save(base + '.png')
    print('render:', base + '.png')

if a.instructions:
    subprocess.run([sys.executable, os.path.join(GEN, 'instructions.py'), out, base + '-instructions',
                    '--lib', a.lib, '--data', a.data], check=True)
