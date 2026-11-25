GRID = (32, 24, 54)   # room to build in: 32 studs long, 24 studs wide, 54 plates (18 bricks) tall
TITLE = 'My animal'

# =====================================================================================================
#  A four-legged animal you design by changing numbers and colour names. No geometry needed.
#
#  Sizes:  length and width are in STUDS (the round bumps on top of a brick: a 2x4 brick is 2 x 4 studs).
#          heights are in BRICKS (one normal brick tall).
#  Build it with --scale 1, e.g.:
#      python preview_shape.py shapes/my_animal.py                (quick look, a few seconds)
#      python make_model.py 11045-1 shapes/my_animal.py out/my_animal.ldr --scale 1 --bricks-only --render
# =====================================================================================================

# ---------- body ----------
BODY_LENGTH = 10      # studs, nose-to-tail direction
BODY_WIDTH = 6        # studs, side to side
BODY_HEIGHT = 3       # bricks
ROUNDNESS = 3         # 2 = very round, 3 = rounded box, 6 or more = almost a plain box

# ---------- legs ----------
LEG_HEIGHT = 2        # bricks (0 = no legs, the body sits on the table)
LEG_THICKNESS = 2     # studs (2 is a good minimum; 1-stud legs snap off)

# ---------- head ----------
HEAD_LENGTH = 5       # studs
HEAD_WIDTH = 4        # studs
HEAD_HEIGHT = 3       # bricks
HEAD_RAISE = 2        # how many bricks the top of the head sits above the top of the body (0 = level)
SNOUT = 1             # how many studs the snout sticks out in front of the face (0 = no snout)
EARS = 1              # 1 = ears on top of the head, 0 = none
TAIL = 1              # how many studs the tail sticks out at the back, on top of the rump (0 = no tail)

# ---------- colours (names from the COLOURS list below) ----------
BODY_COLOUR = 'nougat'
BELLY_COLOUR = 'nougat'    # bottom brick of the body
HEAD_COLOUR = 'nougat'
SNOUT_COLOUR = 'white'
EYE_COLOUR = 'black'
EAR_COLOUR = 'nougat'
LEG_COLOUR = 'nougat'
FEET_COLOUR = 'black'      # bottom brick of each leg
TAIL_COLOUR = 'nougat'

# =====================================================================================================
#  You don't need to change anything below this line.
# =====================================================================================================
COLOURS = {   # name -> Rebrickable colour id
    'black': 0, 'blue': 1, 'green': 2, 'red': 4, 'dark pink': 5, 'pink': 5, 'bright green': 10, 'yellow': 14,
    'white': 15, 'tan': 19, 'orange': 25, 'magenta': 26, 'lime': 27, 'dark tan': 28, 'bright pink': 29,
    'light pink': 29, 'lavender': 30, 'reddish brown': 70, 'brown': 70, 'light grey': 71, 'light gray': 71,
    'dark grey': 72, 'dark gray': 72, 'medium blue': 73, 'nougat': 84, 'medium nougat': 84, 'dark purple': 85,
    'bright light orange': 191, 'golden': 191, 'bright light yellow': 226, 'dark brown': 308, 'dark red': 320,
    'dark azure': 321, 'medium azure': 322,
}

# settings can also come from the command line:  --var BODY_COLOUR=white --var BODY_LENGTH=12
for _k, _v in list(locals().items()):
    if _k.isupper() and _k in os.environ:
        locals()[_k] = type(_v)(os.environ[_k]) if not isinstance(_v, str) else os.environ[_k]
_g = locals()


def colour(name):
    n = str(name).strip().lower()
    if n.isdigit():
        return int(n)
    if n not in COLOURS:
        raise SystemExit(f'unknown colour "{name}". Use one of: ' + ', '.join(sorted(COLOURS)))
    return COLOURS[n]


S = studs(1)            # one stud, in shape units
B = 24 / SC             # one brick, in shape units
band = lambda n: (Y > n * B) & (Y < (n + 1) * B)   # the n-th brick layer from the table
L, W, H = _g['BODY_LENGTH'], _g['BODY_WIDTH'], _g['BODY_HEIGHT']
LH, LT = _g['LEG_HEIGHT'], _g['LEG_THICKNESS']
HL, HW, HH = _g['HEAD_LENGTH'], _g['HEAD_WIDTH'], _g['HEAD_HEIGHT']

def rounded(cx, bottom, top, half_len, half_wid, p):
    """a block with straight sides, rounded corners seen from above, and its top brick layer one stud smaller
    all round. Straight sides matter: a brick that bulges out past the bricks above and below it has nothing
    to click onto and falls off."""
    plan = lambda hl, hw: (np.abs((X - cx) / hl) ** p + np.abs(Z / hw) ** p) <= 1
    m = plan(half_len, half_wid) & (Y > bottom) & (Y < top)
    top_layer = (Y > top - B) & (Y < top)
    if half_len > 1.5 * S and half_wid > 1.5 * S:
        m &= ~(top_layer & ~plan(half_len - S, half_wid - S))
    return m


# body: sits on the legs, centred on x = 0; the head is toward -x
body_bottom = LH * B
body_top = body_bottom + H * B
body = rounded(0, body_bottom, body_top, L / 2 * S, W / 2 * S, _g['ROUNDNESS'])

# legs: four square posts under the corners, reaching one brick up into the body so they clip on
legs = np.zeros_like(body)
if LH > 0:
    for x0 in (snap(-L / 2 * S + S), snap(L / 2 * S - S - LT * S)):
        for z0 in (snap(-W / 2 * S + S / 2), snap(W / 2 * S - S / 2 - LT * S)):
            legs |= box((x0, 0, z0), (x0 + LT * S, body_bottom + B, z0 + LT * S))

# head: overlaps the front of the body by two studs, so its bricks clip onto the body's
head_top = body_top + _g['HEAD_RAISE'] * B
head_bottom = head_top - HH * B
head_x = -(L / 2 + HL / 2 - 2) * S
head = rounded(head_x, head_bottom, head_top, HL / 2 * S, HW / 2 * S, _g['ROUNDNESS'] + 1)

face_x = X[:, 0, 0][np.nonzero(head.any((1, 2)))[0][0]] if head.any() else head_x
first_head_band = int(round(head_bottom / B))
snout = np.zeros_like(body)
if _g['SNOUT'] > 0:   # a block across the lower face, sticking out in front
    sw = max(HW - 2, 2)
    snout = box((snap(face_x - _g['SNOUT'] * S), head_bottom, snap(-sw / 2 * S)),
                (snap(face_x + S), head_bottom + min(2, HH - 1) * B, snap(sw / 2 * S))) & (Y > head_bottom)

ears = np.zeros_like(body)
if _g['EARS']:        # one brick on top of the head at each side, only where the head has bricks to clip onto
    top_band = int(round(head_top / B)) - 1
    on_head = (head & band(top_band)).any(1)[:, None, :]
    ears = band(top_band + 1) & on_head & (np.abs(Z) >= (HW / 2 - 1) * S) & (X > head_x - S)

tail = np.zeros_like(body)
if _g['TAIL'] > 0:    # one brick on top of the back, clipped onto the body and sticking out behind it
    tb = int(round(body_top / B))
    on_body = (body & band(tb - 1)).any(1)[:, None, :]
    inner = band(tb) & on_body & (Z > 0) & (Z < S)
    if inner.any():
        back_x = X[:, 0, 0][np.nonzero(inner.any((1, 2)))[0][-1]]
        tail = band(tb) & (Z > 0) & (Z < S) & (X > back_x - 1.5 * S) & (X < back_x + (_g['TAIL'] + 0.5) * S)

solid = body | legs | head | snout | ears | tail
col = np.full(solid.shape, colour(_g['BODY_COLOUR']))
col[body & band(int(round(body_bottom / B)))] = colour(_g['BELLY_COLOUR'])
col[head] = colour(_g['HEAD_COLOUR'])
col[legs] = colour(_g['LEG_COLOUR'])
col[legs & band(0)] = colour(_g['FEET_COLOUR'])
col[tail & ~body] = colour(_g['TAIL_COLOUR'])
col[ears] = colour(_g['EAR_COLOUR'])
col[snout] = colour(_g['SNOUT_COLOUR'])
eye_band = int(round(head_top / B)) - 2 if HH >= 3 else int(round(head_top / B)) - 1
col[head & ~snout & band(eye_band) & (X < face_x + 1.5 * S) & (np.abs(Z) > 0.5 * S)] = colour(_g['EYE_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
