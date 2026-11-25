"""Voxel sculpture -> LDraw, using only a set's own plates, bricks, tiles and curved/sloped bricks.
usage: generate.py RB_DIR LDRAW_LIB SET_NUM SHAPE.py OUT.ldr SCALE SEED TRIES
(Most people want ../make_model.py, which runs this over several seeds and keeps the best.)"""
import csv, gzip, sys, os, re, json, random, collections
import numpy as np

RB, LIB, SETNUM, SHAPE, OUT = sys.argv[1:6]
SC = float(sys.argv[6]); SEED = int(sys.argv[7]); TRIES = int(sys.argv[8])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ldr, partshape
ldr.setlib(LIB)

def rows(f):
    return csv.DictReader(gzip.open(f"{RB}/{f}.csv.gz", 'rt', encoding='utf-8'))

inv_id = max((i for i in rows('inventories') if i['set_num'] == SETNUM), key=lambda i: int(i['version']))['id']
pname = {p['part_num']: p['name'] for p in rows('parts')}
inv = collections.Counter()
for x in rows('inventory_parts'):
    if x['inventory_id'] == inv_id and x['is_spare'] == 'False':
        inv[(x['part_num'], int(x['color_id']))] += int(x['quantity'])
# ADD="3024:0:20,11477:84:30": extra loose parts (e.g. Pick a Brick) on top of the set's own inventory
for _t in filter(None, os.environ.get('ADD', '').split(',')):
    _p, _c, _q = _t.split(':'); inv[(_p, int(_c))] += int(_q)
ORIG = dict(inv)

# ---- usable parts: plain plates/bricks/tiles plus curved/sloped tops
OK = re.compile(r'^(Plate|Brick|Tile)\b')
BAD = re.compile(r'Inverted|Bracket|Hinge|Towball|Pin|Axle|Studs? on|Side|Arch|Tube|Tooth|Panel|Window|Palisade|Log|Clip|Bar|Handle|Hole|Grille|Jumper|Wedge|Print|Cutout|Corner|Round|Cone|Modified|Special|Hollow|Bow', re.I)
GOOD = re.compile(r'^(Tile \d+ x \d+ with Groove|Brick Curved \d+ x \d+( x [\d /]+)? No Studs|Brick Curved 2 x 2 x 2/3|Brick Sloped (45|33|30)\W+ \d+ x \d+( x 2/3)?$|Plate Round 1 x 1 with Solid Stud|Brick Round 1 x 1 Open Stud|Plate Special .*Jumper|Plate .*Rounded with 2 Open Studs|.*with Only 2 Studs|Plate Round 2 x 2)', re.I)

cache_f = os.path.join(HERE, 'partcache.json')
cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
_cache_n0 = len(cache)
PT = {}
for (p, c), n in ORIG.items():
    if p in PT:
        continue
    nm = pname.get(p, '')
    if not OK.match(nm):
        continue
    if BAD.search(nm) and not GOOD.match(nm):
        continue
    if p not in cache:
        try:
            cache[p] = partshape.analyse(p)
        except FileNotFoundError:
            cache[p] = None
    if not cache[p]:
        continue
    seen = set(); lst = []
    for o in cache[p]:
        f = np.array(o['fill']); stud = np.array(o['stud'])
        if 'Jumper' in nm:
            # the jumper stud sits between grid cells: the ray-cast reads it as an extra layer or as
            # whole-cell studs. Treat it as one studless plate layer (a finishing piece on this grid).
            f = f[:, :1, :]; f[:] = 1.0; stud = np.zeros_like(stud)
        key = (f.shape, f.round(2).tobytes(), stud.tobytes())
        if key in seen:
            continue
        seen.add(key)
        eff = f >= 0.5; blk = f > 0.1
        if not eff[:, 0, :].any():
            continue
        ny = eff.shape[1]
        top = np.where(eff.any(1), ny - 1 - np.argmax(eff[:, ::-1, :], axis=1), -1)
        blktop = np.where(blk.any(1), ny - 1 - np.argmax(blk[:, ::-1, :], axis=1), -1)
        curved = bool(((f > 0.1) & (f < 0.9)).any())
        hcol = f.sum(1); ga, gb = np.meshgrid(np.arange(f.shape[0]) + 0.5, np.arange(f.shape[2]) + 0.5, indexing='ij')
        dv = np.array([((ga - ga.mean()) * (hcol.mean() - hcol)).sum(), ((gb - gb.mean()) * (hcol.mean() - hcol)).sum()])
        down = dv / np.linalg.norm(dv) if np.linalg.norm(dv) > 1e-6 else np.zeros(2)
        lst.append(dict(part=p, rot=o['rot'], nx=o['nx'], ny=ny, nz=o['nz'], eff=eff, blk=blk, stud=stud,
                        top=top, blktop=blktop, off=o['off'], curved=curved, down=down, studless=not stud.any(), vol=int(eff.sum())))
    if lst:
        PT[p] = lst
if len(cache) != _cache_n0:   # only save when new parts were analysed; atomic + retry (parallel runs share this file)
    import time
    _tmp = f'{cache_f}.{os.getpid()}.tmp'; json.dump(cache, open(_tmp, 'w'))
    for _ in range(20):
        try:
            os.replace(_tmp, cache_f); break
        except PermissionError:
            time.sleep(0.5)
    else:
        os.remove(_tmp)
print('usable part types', len(PT), [(p, pname[p]) for p in sorted(PT, key=lambda p: -PT[p][0]['vol'])])

# ---- shape
import shapelib
_shp = shapelib.load(SHAPE, SC)
NX, NZ, NY = _shp['NX'], _shp['NZ'], _shp['NY']; X, Y, Z = _shp['X'], _shp['Y'], _shp['Z']
solid, col, KEYC, TITLE = _shp['solid'], _shp['col'], _shp['KEYC'], _shp['TITLE']
EDITS_F = os.environ.get('EDITS')
prev_edits = json.load(open(EDITS_F)) if EDITS_F and os.path.exists(EDITS_F) else []
for e in prev_edits:
    if e[0] == 'trim': solid[e[2], e[1], e[3]] = False
    else: col[e[2], e[1], e[3]] = e[4]

def erode(m, ground=False):
    e = m.copy()
    for ax in range(3):
        for s in (1, -1):
            sh = np.roll(m, s, axis=ax); idx = [slice(None)] * 3; idx[ax] = 0 if s == 1 else -1
            sh[tuple(idx)] = (ground and ax == 1 and s == 1)   # the table under layer 0 hides bottom faces
            e &= sh
    return e
exposed = shell = None
EXTRA = np.zeros(solid.shape, bool)
def refresh():
    global exposed, shell
    exposed = (solid & ~erode(solid, True)) | (EXTRA & solid); shell = solid & ~erode(erode(solid))
refresh()
sx, sy_, sz = np.nonzero(solid.any(1)[:, None, :].repeat(1, 1)) if False else (None, None, None)
_cols = np.argwhere(solid.any(1)); CX, CZ = _cols[:, 0].mean() + 0.5, _cols[:, 1].mean() + 0.5

# ---- placement
occ = np.full((NX, NY, NZ), -1, int)
pieces = []
PARENT = []
rng = random.Random(SEED)
MAXPRO = int(os.environ.get('MAXPRO', '1'))

def stud_at(pc, x, y, z):
    o = pc['o']; a = x - pc['i']; b = z - pc['k']
    return bool(o['stud'][a, b]) and pc['L'] + o['top'][a, b] == y

def support_ids(o, i, L, k, occ_, pcs):
    ids = set()
    if L == 0:
        return ids
    for a in range(o['nx']):
        for b in range(o['nz']):
            if not o['eff'][a, 0, b]:
                continue
            q = occ_[i + a, L - 1, k + b]
            if q >= 0 and stud_at(pcs[q], i + a, L - 1, k + b):
                ids.add(q)
    return ids

def support(o, i, L, k, occ_, pcs):
    if L == 0:
        return 0
    ids = set()
    for a in range(o['nx']):
        for b in range(o['nz']):
            if not o['eff'][a, 0, b]:
                continue
            q = occ_[i + a, L - 1, k + b]
            if q >= 0 and stud_at(pcs[q], i + a, L - 1, k + b):
                ids.add(q)
    return len(ids)

def check(o, i, L, k, occ_, free_needed, EXP):
    nx, ny, nz = o['nx'], o['ny'], o['nz']
    if i < 0 or k < 0 or i + nx > NX or k + nz > NZ or L + ny > NY:
        return None
    so = solid[i:i + nx, L:L + ny, k:k + nz]; oc = occ_[i:i + nx, L:L + ny, k:k + nz]
    eff, blk = o['eff'], o['blk']
    if (blk & (oc >= 0)).any():
        return None
    if (eff & ~so).sum() > (MAXPRO if o['curved'] else 0):
        return None
    if not (eff[:, 0, :] & free_needed[i:i + nx, k:k + nz]).any():
        return None
    if o['curved'] and o['down'].any():
        out = np.array([i + nx / 2 - CX, k + nz / 2 - CZ])
        if np.linalg.norm(out) > 0.75 and o['down'] @ (out / np.linalg.norm(out)) < 0.35:
            return None
    # a column without studs must have open air right above it
    for a in range(nx):
        for b in range(nz):
            if o['blktop'][a, b] < 0 or o['stud'][a, b]:
                continue
            yy = L + o['blktop'][a, b] + 1
            if yy < NY and solid[i + a, yy, k + b]:
                return None
    m = blk & so
    vis = EXP[i:i + nx, L:L + ny, k:k + nz] & m
    need = set(col[i:i + nx, L:L + ny, k:k + nz][vis].tolist())
    if len(need) > 1:
        return None
    lost = int((blk & ~eff & so).sum())
    return (need.pop() if need else None), lost

def attempt(L, inv0):
    inv_ = dict(inv0); occ_ = occ.copy(); pcs = list(pieces); new = []; exp_ = exposed.copy(); extra = np.zeros_like(EXTRA)
    sol = solid[:, L, :]
    if not sol.any():
        return (0, [], inv_, occ_, [], np.zeros_like(EXTRA), list(PARENT))
    xs, zs = np.nonzero(sol); x0, x1, z0, z1 = xs.min(), xs.max(), zs.min(), zs.max()
    vis = exposed[:, L, :].copy(); sh = shell[:, L, :]

    def place(o, c, i, k):
        n = len(pcs); pc = dict(part=o['part'], color=c, o=o, i=i, L=L, k=k)
        pcs.append(pc); new.append(pc)
        sub = occ_[i:i + o['nx'], L:L + o['ny'], k:k + o['nz']]; sub[o['blk']] = n
        inv_[(o['part'], c)] -= 1
        if o['curved']:
            lost = o['blk'] & ~o['eff']
            for a, l, b in zip(*np.nonzero(lost)):
                for da, dl, db in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    x_, y_, z_ = i + a + da, L + l + dl, k + b + db
                    if 0 <= x_ < NX and 0 <= y_ < NY and 0 <= z_ < NZ and solid[x_, y_, z_]:
                        exp_[x_, y_, z_] = True; extra[x_, y_, z_] = True

    def colour_choice(p, need):
        if need is not None:
            return need if inv_.get((p, need), 0) > 0 else None
        cs = [c for (pp, c), n in inv_.items() if pp == p and n > 0]
        if not cs:
            return None
        cs.sort(key=lambda c: (c in KEYC, -inv_[(p, c)]))
        return cs[0]

    def sweep(kind, region, maxlost=0, minsup=0):
        types = [p for p in PT if kind(PT[p][0]) and any(n > 0 for (pp, c), n in inv_.items() if pp == p)]
        types.sort(key=lambda p: -(PT[p][0]['vol'] + rng.random() * 4))
        for p in types:
            orients = list(PT[p]); rng.shuffle(orients)
            for o in orients:
                pos = [(i, k) for i in range(x0 - o['nx'] + 1, x1 + 1) for k in range(z0 - o['nz'] + 1, z1 + 1)]
                rng.shuffle(pos)
                for i, k in pos:
                    free = (occ_[:, L, :] < 0) & region
                    res = check(o, i, L, k, occ_, free, exp_)
                    if not res:
                        continue
                    need, lost = res
                    if lost > maxlost:
                        continue
                    c = colour_choice(p, need)
                    if c is None:
                        continue
                    nsup = len(support_ids(o, i, L, k, occ_, pcs))
                    ncols = int(o['eff'][:, 0, :].sum())
                    if o['studless'] and nsup < (2 if ncols >= 2 else 1):
                        continue
                    if nsup < minsup:
                        continue
                    place(o, c, i, k)

    curve_first = os.environ.get('CURVEFIRST') == '1'
    if curve_first:
        sweep(lambda o: o['curved'], vis, maxlost=2)              # curved caps get first pick of the outside
    if L > 0:
        sweep(lambda o: not o['curved'], sh, minsup=2)            # bridges: pieces that join 2+ pieces below
    if not curve_first:
        sweep(lambda o: o['curved'], vis, maxlost=2)              # curved caps on the outside
    sweep(lambda o: not o['curved'] and o['ny'] > 1, sh)          # full bricks in the wall
    sweep(lambda o: not o['curved'] and o['ny'] == 1, sh & vis)   # plates/tiles on the outside
    sweep(lambda o: not o['curved'] and o['ny'] == 1, vis)        # fix-ups, may reach inward
    sweep(lambda o: not o['curved'] and o['ny'] == 1, sh)         # hidden filler
    vis = exp_[:, L, :]
    freeL = occ_[:, L, :] < 0
    miss_v = [(L, int(i), int(k), int(col[i, L, k])) for i, k in zip(*np.nonzero(freeL & vis))]
    miss_s = int((freeL & sh & ~vis).sum())
    par = list(PARENT) + list(range(len(PARENT), len(pcs)))
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    base = len(PARENT)
    for n_i, pc in enumerate(new):
        me = base + n_i
        for q in support_ids(pc['o'], pc['i'], L, pc['k'], occ_, pcs):
            ra, rb = find(me), find(q)
            if ra != rb: par[ra] = rb
    roots = len({find(a) for a in range(len(pcs))})
    bond = 0; flo = 0
    for pc in new:
        n_ = support(pc['o'], pc['i'], L, pc['k'], occ_, pcs)
        if n_ == 0 and L > 0:
            flo += 1
        bond += min(n_, 3)
    curved = sum(1 for pc in new if pc['o']['curved'])
    score = len(miss_v) * 1000 + miss_s * 20 + flo * 150 - bond * 2 + len(new) - curved * 15 + roots * int(os.environ.get('ROOTW', '120'))
    return score, new, inv_, occ_, miss_v, extra, par

def nbrs(i, k):
    return [(i + a, k + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= i + a < NX and 0 <= k + b < NZ]

edits = []; missing = []
for L in range(NY):
    if not solid[:, L, :].any():
        continue
    for rnd in range(4):
        best = min((attempt(L, inv) for _ in range(TRIES)), key=lambda t: t[0])
        _, new, newinv, newocc, miss, extra, newpar = best
        if not miss or rnd == 3:
            break
        for (_, i, k, c) in miss:
            others = {int(col[a, L, b]) for a, b in nbrs(i, k) if solid[a, L, b] and exposed[a, L, b]} - {c}
            if others:
                col[i, L, k] = sorted(others)[0]; edits.append(('recolour', L, int(i), int(k), int(col[i, L, k])))
            else:
                solid[i, L, k] = False; edits.append(('trim', L, int(i), int(k)))
        refresh()
    inv.clear(); inv.update(newinv); occ[:] = newocc; pieces += new; missing += miss
    EXTRA |= extra; refresh(); PARENT[:] = newpar
    print(f'layer {L}: +{len(new)} ({sum(1 for p in new if p["o"]["curved"])} curved, '
          f'{sum(1 for p in new if p["o"]["ny"] > 1 and not p["o"]["curved"])} bricks) miss {len(miss)}', flush=True)

# ---- connectivity (stud-into-tube contacts only)
adj = collections.defaultdict(set)
for n, pc in enumerate(pieces):
    o = pc['o']
    if pc['L'] == 0:
        continue
    for a in range(o['nx']):
        for b in range(o['nz']):
            if not o['eff'][a, 0, b]:
                continue
            q = occ[pc['i'] + a, pc['L'] - 1, pc['k'] + b]
            if q >= 0 and stud_at(pieces[q], pc['i'] + a, pc['L'] - 1, pc['k'] + b):
                adj[n].add(q); adj[q].add(n)
seen = set(); comps = []
for n in range(len(pieces)):
    if n in seen:
        continue
    st = [n]; comp = []; seen.add(n)
    while st:
        u = st.pop(); comp.append(u)
        for v in adj[u]:
            if v not in seen:
                seen.add(v); st.append(v)
    comps.append(comp)
comps.sort(key=len, reverse=True)
main = set(comps[0])
dropped = [(pieces[n]['part'], pieces[n]['color'], pieces[n]['L']) for n in range(len(pieces)) if n not in main]
weak = sum(1 for n in main if len(adj[n]) <= 1)
keep = [pieces[n] for n in sorted(main)]
if os.environ.get('DUMP'):
    cid = {}
    for ci, comp in enumerate(comps):
        for n in comp: cid[n] = ci
    for L in range(0, 6):
        print('layer', L)
        for kk in range(NZ):
            row = ''
            for ii in range(NX):
                q = occ[ii, L, kk]
                if q < 0: row += ('  ~ ' if solid[ii, L, kk] else '  . ')
                else:
                    pc = pieces[q]; row += f"{cid[q]:2d}{'b' if pc['o']['ny']>1 and not pc['o']['curved'] else ('c' if pc['o']['curved'] else 'p')}{'*' if pc['L']==L else ' '}"
            print(row)

# ---- repaint: hidden filler that the outside can actually see shows up as holes in the wrong colour.
# Find pieces touching outside air; give each the colour its visible cells want, by swapping colours with a
# hidden piece of the same part, or else by using a spare from the set.
for n in range(len(pieces)):
    if n not in main:
        inv[(pieces[n]['part'], pieces[n]['color'])] = inv.get((pieces[n]['part'], pieces[n]['color']), 0) + 1
occK = np.full(occ.shape, -1, int)
for n, pc in enumerate(keep):
    o = pc['o']; sub = occK[pc['i']:pc['i'] + o['nx'], pc['L']:pc['L'] + o['ny'], pc['k']:pc['k'] + o['nz']]; sub[o['blk']] = n
air = occK < 0; out_air = np.zeros_like(air)
seed = np.zeros_like(air); seed[0], seed[-1], seed[:, :, 0], seed[:, :, -1], seed[:, -1] = True, True, True, True, True
out_air = seed & air
while True:   # flood outside air inward
    grow = out_air.copy()
    for ax in range(3):
        for sft in (1, -1):
            sh_ = np.roll(out_air, sft, axis=ax); idx = [slice(None)] * 3; idx[ax] = 0 if sft == 1 else -1; sh_[tuple(idx)] = False
            grow |= sh_ & air
    if (grow == out_air).all():
        break
    out_air = grow
def seen_cells(n):
    pc = keep[n]; o = pc['o']; cells = []
    for a, l, b in zip(*np.nonzero(o['blk'])):
        x_, y_, z_ = pc['i'] + a, pc['L'] + l, pc['k'] + b
        for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            u, v, w = x_ + dx, y_ + dy, z_ + dz
            if v < 0:
                continue                      # table
            if not (0 <= u < NX and 0 <= v < NY and 0 <= w < NZ) or out_air[u, v, w]:
                cells.append((x_, y_, z_)); break
    return cells
want = {}
for n in range(len(keep)):
    cs = seen_cells(n)
    if cs:
        want[n] = collections.Counter(int(col[c]) for c in cs).most_common(1)[0][0]
repaint = [0, 0, 0]   # swapped, from spares, still wrong
for n, tgt in want.items():
    pc = keep[n]
    if pc['color'] == tgt:
        continue
    swap = next((m for m in range(len(keep)) if m not in want and keep[m]['part'] == pc['part'] and keep[m]['color'] == tgt), None)
    if swap is not None:
        keep[swap]['color'], pc['color'] = pc['color'], tgt; repaint[0] += 1
    elif inv.get((pc['part'], tgt), 0) > 0:
        inv[(pc['part'], tgt)] -= 1; inv[(pc['part'], pc['color'])] = inv.get((pc['part'], pc['color']), 0) + 1
        pc['color'] = tgt; repaint[1] += 1
    else:
        repaint[2] += 1; print('  visible wrong colour:', pc['part'], pc['color'], 'wants', tgt, 'layer', pc['L'], 'at', pc['i'], pc['k'])
print('repaint: swapped', repaint[0], 'from spares', repaint[1], 'still wrong colour', repaint[2])

lines = [f'0 {TITLE}', f'0 Name: {os.path.basename(OUT)}', '0 Author: Claude (generated)', '']
# build order: a piece goes in the first step where something it clips onto is already placed. Pieces that hang
# under a later layer (a tongue under a snout, the belly between the legs) wait for the piece above them.
placed = set(); step_of = {}
for Ls in sorted({pieces[n]['L'] for n in main}):
    grew = True
    while grew:
        grew = False
        for n in sorted(main):
            if n in placed or pieces[n]['L'] > Ls:
                continue
            if pieces[n]['L'] == 0 or adj[n] & placed:
                placed.add(n); step_of[n] = Ls; grew = True
late = sum(1 for n in main if step_of[n] != pieces[n]['L'])
print('build order: pieces moved to a later step (hang from above):', late)
byL = collections.defaultdict(list)
for n in sorted(main):
    byL[step_of[n]].append(pieces[n])
for L in sorted(byL):
    for pc in byL[L]:
        o = pc['o']; R = partshape.ROTS[o['rot']]
        tx = (pc['i'] - NX / 2) * 20 - o['off'][0]; tz = (pc['k'] - NZ / 2) * 20 - o['off'][2]; ty = -pc['L'] * 8 - o['off'][1]
        lines.append(f"1 {pc['color']} {tx:g} {ty:g} {tz:g} " + ' '.join(f'{v:g}' for v in R.reshape(-1)) + f" {pc['part']}.dat")
    lines.append('0 STEP')
open(OUT, 'w').write('\n'.join(lines) + '\n')
if EDITS_F:
    json.dump(prev_edits + edits, open(EDITS_F, 'w'))
used = collections.Counter((pc['part'], pc['color']) for pc in keep)
over = [(k, v, ORIG.get(k, 0)) for k, v in used.items() if v > ORIG.get(k, 0)]
print('SUMMARY pieces', len(keep), 'wrongcolour', repaint[2], 'curved', sum(1 for p in keep if p['o']['curved']),
      'bricks', sum(1 for p in keep if p['o']['ny'] > 1 and not p['o']['curved']),
      'missing', len(missing), 'edits', len(edits), 'components', len(comps), 'dropped', len(dropped),
      'weak', weak, 'over', over, 'steps', len(byL))
print('dropped:', dropped)
