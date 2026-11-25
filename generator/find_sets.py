"""Search every LEGO set for ones whose parts can build a shape (or for sets rich in given parts/colours).

usage:
  python generator/find_sets.py shape SHAPE.py [--scales 0.45,0.5,...] [--minyear 2024] [--top 25] [--subst 29=5,19 ...]
      For each set, find the largest scale at which its usable parts cover the shape's visible cells in every
      key colour (with slack) and the whole shell overall. Ranked by piece count (a price proxy) among sets that
      reach the scale you care about.
  python generator/find_sets.py parts --colour 15:300 --colour 0:150 [--part 3573] [--minyear 2024] [--top 25]
      Sets with at least N stud-plate units of usable parts in each colour (and optionally containing a part).

"Usable" = the parts generate.py can place (plain plates, bricks, tiles, curved/sloped bricks, a few specials).
Volume is in stud-plate units: a 2x4 plate = 8, a 2x4 brick = 24. Colour ids are Rebrickable ids.
Data: data/*.csv.gz from Rebrickable downloads (sets, themes, inventories, inventory_parts, parts, colors)."""
import argparse, collections, csv, gzip, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('REMAKE_DATA', os.path.join(os.path.dirname(HERE), 'data'))
rows = lambda f: csv.DictReader(gzip.open(os.path.join(DATA, f + '.csv.gz'), 'rt', encoding='utf-8'))

# same filter as generate.py
OK = re.compile(r'^(Plate|Brick|Tile)\b')
BAD = re.compile(r'Inverted|Bracket|Hinge|Towball|Pin|Axle|Studs? on|Side|Arch|Tube|Tooth|Panel|Window|Palisade|Log|Clip|Bar|Handle|Hole|Grille|Jumper|Wedge|Print|Cutout|Corner|Round|Cone|Modified|Special|Hollow|Bow', re.I)
GOOD = re.compile(r'^(Tile \d+ x \d+ with Groove|Brick Curved \d+ x \d+( x [\d /]+)? No Studs|Brick Curved 2 x 2 x 2/3|Brick Sloped (45|33|30)\W+ \d+ x \d+( x 2/3)?$|Plate Round 1 x 1 with Solid Stud|Brick Round 1 x 1 Open Stud|Plate Special .*Jumper|Plate .*Rounded with 2 Open Studs|.*with Only 2 Studs|Plate Round 2 x 2)', re.I)
DIM = re.compile(r'(\d+) x (\d+)(?: x (\d+)(?: (\d)/3)?| x (\d)/3)?')


def part_volume(name):
    """stud-plate volume of a usable part from its name, or 0 if generate.py can't use it"""
    if not OK.match(name) or (BAD.search(name) and not GOOD.match(name)):
        return 0
    m = DIM.search(name)
    if not m:
        return 0
    a, b = int(m.group(1)), int(m.group(2))
    if m.group(3):                       # "x 2" bricks, "x 1 2/3"
        h = int(m.group(3)) * 3 + (int(m.group(4)) if m.group(4) else 0)
    elif m.group(5):                     # "x 2/3"
        h = int(m.group(5))
    else:
        h = 3 if name.startswith('Brick') else 1
    v = a * b * h
    if 'Curved' in name or 'Sloped' in name:
        v *= 0.6                         # curved/sloped tops fill part of their box
    return v


def load_sets(minyear):
    themes = {t['id']: t for t in rows('themes')}
    def top_theme(tid):
        while themes.get(tid, {}).get('parent_id'):
            tid = themes[tid]['parent_id']
        return themes.get(tid, {}).get('name', '?')
    sets = {}
    for s in rows('sets'):
        if int(s['year']) >= minyear and int(s['num_parts']) > 0:
            tt = top_theme(s['theme_id'])
            if tt in ('Gear', 'Books', 'Collectible Minifigures', 'Key Chains', 'Magnets', 'Service Packs', 'Bulk Bricks', 'Supplemental', 'Promotional'):
                continue
            s['top_theme'] = tt
            sets[s['set_num']] = s
    inv = {}
    for i in rows('inventories'):
        if i['set_num'] in sets and (i['set_num'] not in inv or int(i['version']) > inv[i['set_num']][1]):
            inv[i['set_num']] = (i['id'], int(i['version']))
    by_inv = {v[0]: k for k, v in inv.items()}
    pname = {p['part_num']: p['name'] for p in rows('parts')}
    vol_cache = {}
    contents = collections.defaultdict(lambda: collections.Counter())   # set -> (part, colour) -> qty
    for x in rows('inventory_parts'):
        sn = by_inv.get(x['inventory_id'])
        if sn and x['is_spare'] == 'False':
            contents[sn][(x['part_num'], int(x['color_id']))] += int(x['quantity'])
    for sn, cnt in contents.items():
        vols = collections.Counter()
        for (p, c), q in cnt.items():
            if p not in vol_cache:
                vol_cache[p] = part_volume(pname.get(p, ''))
            vols[c] += vol_cache[p] * q
        sets[sn]['vols'] = vols
        sets[sn]['contents'] = cnt
    return {k: v for k, v in sets.items() if 'vols' in v}


def cname():
    return {int(c['id']): c['name'] for c in rows('colors')}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='mode', required=True)
    a1 = sub.add_parser('shape'); a1.add_argument('shape')
    a1.add_argument('--scales', default='0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8')
    a1.add_argument('--want', type=float, default=0.6, help='list sets that reach at least this scale')
    a1.add_argument('--slack', type=float, default=1.6, help='usable volume needed per visible cell of each colour')
    a1.add_argument('--accent', type=float, default=1.0, help='slack for colours with < 60 visible cells')
    a1.add_argument('--subst', nargs='*', default=[], help='colour substitutes, e.g. 29=5,19 (pink may be dark pink or tan)')
    a2 = sub.add_parser('parts'); a2.add_argument('--colour', action='append', default=[]); a2.add_argument('--part', action='append', default=[])
    for a in (a1, a2):
        a.add_argument('--minyear', type=int, default=2024); a.add_argument('--top', type=int, default=25)
    args = ap.parse_args()
    CN = cname()
    sets = load_sets(args.minyear)
    print(f'{len(sets)} sets from {args.minyear} on with inventories', file=sys.stderr)

    if args.mode == 'parts':
        need = {int(k): float(v) for k, v in (c.split(':') for c in args.colour)}
        out = []
        for sn, s in sets.items():
            if all(s['vols'][c] >= v for c, v in need.items()) and all(any(p == pp for (pp, _) in s['contents']) for p in args.part):
                out.append(s)
        out.sort(key=lambda s: int(s['num_parts']))
        for s in out[:args.top]:
            print(f"{s['set_num']:10} {s['year']} {int(s['num_parts']):5}pcs  {s['top_theme'][:14]:14} {s['name'][:40]:40} " +
                  ' '.join(f"{CN.get(c, c)}={s['vols'][c]:.0f}" for c in need))
        return

    sys.path.insert(0, HERE); import shapelib
    subst = {}
    for t in args.subst:
        k, v = t.split('='); subst[int(k)] = [int(x) for x in v.split(',')]
    scales = [float(x) for x in args.scales.split(',')]
    needs = {sc: shapelib.needs(shapelib.load(args.shape, sc)) for sc in scales}
    for sc in scales:
        print(f'scale {sc}: ' + ', '.join(f"{CN.get(c, c)} vis {n['visible']} shell {n['shell']}" for c, n in needs[sc].items()), file=sys.stderr)

    def fits(s, nd):
        """True if the set covers this need table; returns (ok, notes)"""
        notes = []; used = collections.Counter()
        for c, n in sorted(nd.items(), key=lambda kv: -kv[1]['visible']):
            k = args.slack if n['visible'] >= 60 else args.accent
            req = n['visible'] * k
            options = [c] + subst.get(c, [])
            got = None
            for o in options:
                if s['vols'][o] - used[o] >= req:
                    got = o; break
            if got is None:
                return False, notes
            used[got] += req
            if got != c:
                notes.append(f'{CN.get(c, c)}->{CN.get(got, got)}')
        total_need = sum(n['shell'] for n in nd.values()) * 1.15
        if sum(s['vols'].values()) < total_need:
            return False, notes
        return True, notes

    res = []
    for sn, s in sets.items():
        best = None
        for sc in scales:
            ok, notes = fits(s, needs[sc])
            if ok:
                best = (sc, notes)
        if best and best[0] >= args.want:
            res.append((s, best))
    res.sort(key=lambda r: (int(r[0]['num_parts']), -r[1][0]))
    print(f'{len(res)} sets reach scale >= {args.want}')
    for s, (sc, notes) in res[:args.top]:
        main_cols = ' '.join(f"{CN.get(c, c)[:10]}={s['vols'][c]:.0f}" for c in needs[scales[-1]] if s['vols'][c])
        print(f"{s['set_num']:10} {s['year']} {int(s['num_parts']):5}pcs max-scale {sc:<4} {s['top_theme'][:14]:14} {s['name'][:38]:38} {main_cols} {' '.join(notes)}")


if __name__ == '__main__':
    main()
