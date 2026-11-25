"""Build step-by-step instructions (HTML + images) for a generated .ldr, using LeoCAD to render.
usage: python generator/instructions.py MODEL.ldr OUTDIR [--lib LDRAW_DIR] [--data RB_DIR] [--angles LAT LON] [--size W H]

Writes OUTDIR/instructions.html, OUTDIR/steps/stepNN.png (new parts highlighted, earlier ones faded),
OUTDIR/parts/<part>_<color>.png (one picture per part/colour) and OUTDIR/parts_list.csv.
Steps come from the model's `0 STEP` lines (generate.py writes one per layer)."""
import argparse, collections, csv, gzip, html, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# LeoCAD (free, https://www.leocad.org) does the step renders. Set LEOCAD to its path if it isn't found.
LEOCAD = (os.environ.get('LEOCAD') or shutil.which('leocad') or shutil.which('LeoCAD')
          or next((p for p in (r'C:\Program Files\LeoCAD\LeoCAD.exe', '/Applications/LeoCAD.app/Contents/MacOS/LeoCAD')
                   if os.path.exists(p)), None))
ap = argparse.ArgumentParser()
ap.add_argument('model'); ap.add_argument('out')
ap.add_argument('--lib', default=os.environ.get('LDRAW_LIB', os.path.join(ROOT, 'ldraw')))
ap.add_argument('--data', default=os.environ.get('REMAKE_DATA', os.path.join(ROOT, 'data')))
ap.add_argument('--angles', nargs=2, default=['30', '-30'], help='camera latitude longitude (degrees)')
ap.add_argument('--size', nargs=2, type=int, default=[900, 650])
ap.add_argument('--title', default=None)
a = ap.parse_args()
if not LEOCAD:
    sys.exit('LeoCAD not found: install it from https://www.leocad.org or set LEOCAD=/path/to/leocad')
model = os.path.abspath(a.model); out = os.path.abspath(a.out)
os.makedirs(os.path.join(out, 'steps'), exist_ok=True); os.makedirs(os.path.join(out, 'parts'), exist_ok=True)

# ---- read the model: title and the parts added in each step
title = a.title; steps = [[]]
for line in open(model, encoding='utf-8', errors='replace'):
    t = line.split()
    if not t:
        continue
    if t[0] == '0' and title is None and len(t) > 1 and t[1] not in ('Name:', 'Author:', 'STEP'):
        title = line[2:].strip()
    elif t[0] == '0' and len(t) > 1 and t[1] == 'STEP':
        steps.append([])
    elif t[0] == '1':
        steps[-1].append((t[14].lower().removesuffix('.dat'), int(t[1])))
steps = [s for s in steps if s]
title = title or os.path.basename(model)
if not steps:
    sys.exit('no parts found in ' + model)

# ---- names (Rebrickable ids match LDraw codes for the plain colours generate.py uses)
pname = {p['part_num']: p['name'] for p in csv.DictReader(gzip.open(os.path.join(a.data, 'parts.csv.gz'), 'rt', encoding='utf-8'))}
cinfo = {int(c['id']): (c['name'], c['rgb']) for c in csv.DictReader(gzip.open(os.path.join(a.data, 'colors.csv.gz'), 'rt', encoding='utf-8'))}
cname = lambda c: cinfo.get(c, (f'colour {c}', '888888'))[0]

def leocad(args):
    # timeout: if LeoCAD crashes it shows a modal dialog and never exits on its own
    try:
        r = subprocess.run([LEOCAD, '-l', a.lib] + args, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/IM', 'LeoCAD.exe'], capture_output=True)
        print('WARNING: LeoCAD hung or crashed on', args[0], file=sys.stderr)
        return -1
    if r.returncode:
        print('WARNING: LeoCAD exit', r.returncode, 'on', args[0], r.stderr[-300:], file=sys.stderr)
    return r.returncode

# ---- step pictures (one LeoCAD call renders them all as stepNN.png)
W, H = a.size
leocad([model, '-i', os.path.join(out, 'steps', 'step.png'), '-w', str(W), '-h', str(H), '-f', '1', '-t', str(len(steps)),
        '--fade-steps', '--highlight', '--camera-angles', a.angles[0], a.angles[1]])
leocad([model, '-i', os.path.join(out, 'steps', 'final.png'), '-w', str(W), '-h', str(H),
        '--camera-angles', a.angles[0], a.angles[1]])
nd = len(str(len(steps))) if len(steps) > 9 else 2
step_img = lambda n: f'steps/step{n:0{nd}d}.png'
missing = [n for n in range(1, len(steps) + 1) if not os.path.exists(os.path.join(out, step_img(n)))]
if missing:   # LeoCAD's number padding differs from the guess: look for what it wrote
    found = sorted(f for f in os.listdir(os.path.join(out, 'steps')) if f.startswith('step') and f != 'step.png')
    if len(found) == len(steps):
        step_img = lambda n: 'steps/' + found[n - 1]
    else:
        print('WARNING: step images missing for steps', missing[:10], file=sys.stderr)

# ---- one picture per part/colour, for the callouts
uniq = sorted({pc for s in steps for pc in s})
for p, c in uniq:
    f = os.path.join(out, 'parts', f'{p}_{c}.png')
    if os.path.exists(f):
        continue
    tmp = os.path.join(out, 'parts', f'_{p}_{c}.ldr')
    open(tmp, 'w').write(f'0 {p}\n1 {c} 0 0 0 1 0 0 0 1 0 0 0 1 {p}.dat\n')
    leocad([tmp, '-i', f, '-w', '160', '-h', '120', '--camera-angles', '30', '-30'])
    os.remove(tmp)

# ---- parts list CSV
total = collections.Counter(pc for s in steps for pc in s)
with open(os.path.join(out, 'parts_list.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['part', 'color', 'qty', 'description'])
    for (p, c), n in sorted(total.items(), key=lambda kv: (-kv[1], kv[0])):
        w.writerow([p, cname(c), n, pname.get(p, '')])

# ---- page
def callouts(cnt):
    cells = []
    for (p, c), n in sorted(cnt.items(), key=lambda kv: (cname(kv[0][1]), kv[0][0])):
        cells.append(f'<figure class="part"><img src="parts/{p}_{c}.png" alt="">'
                     f'<figcaption><b>{n}×</b> {html.escape(pname.get(p, p))}<br><span>{html.escape(cname(c))} · {p}</span></figcaption></figure>')
    return '<div class="parts">' + ''.join(cells) + '</div>'

body = [f'<h1>{html.escape(title)}</h1>',
        f'<p class="meta">{sum(total.values())} pieces · {len(steps)} steps</p>',
        '<img class="hero" src="steps/final.png" alt="finished model">',
        '<h2>Parts you need</h2>', callouts(total)]
for n, s in enumerate(steps, 1):
    body += [f'<section class="step"><h2>Step {n}</h2>', callouts(collections.Counter(s)),
             f'<img class="stepimg" src="{step_img(n)}" alt="step {n}"></section>']
page = f'''<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>
body{{font:15px/1.4 system-ui,sans-serif;max-width:980px;margin:2em auto;padding:0 1em;color:#222;background:#fafaf7}}
h1{{margin-bottom:.2em}} .meta{{color:#666;margin-top:0}} .hero,.stepimg{{display:block;max-width:100%;margin:1em auto}}
.parts{{display:flex;flex-wrap:wrap;gap:8px}} .part{{margin:0;width:150px;background:#fff;border:1px solid #ddd;border-radius:6px;padding:6px;font-size:12px}}
.part img{{width:100%;height:auto}} .part span{{color:#777}} .step{{border-top:2px solid #ddd;margin-top:2em;page-break-inside:avoid}}
@media print{{body{{background:#fff}} .step{{page-break-before:always}}}}
</style></head><body>{''.join(body)}</body></html>'''
open(os.path.join(out, 'instructions.html'), 'w', encoding='utf-8').write(page)
print(f"wrote {os.path.join(out, 'instructions.html')}: {len(steps)} steps, {sum(total.values())} pieces, {len(uniq)} part/colour types")
