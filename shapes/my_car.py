GRID = (28, 16, 30)   # room to build in: 28 x 16 studs, 30 plates (10 bricks) tall
TITLE = 'My car'

# =====================================================================================================
#  A car (or van, or truck) with a cabin, windows, lights and four wheels. The front is at -X.
#  The wheels are black blocks: the bricks in 11045 don't turn. Change the numbers and colour names.
#
#  Sizes:  lengths and widths are in STUDS (the round bumps on top of a brick).
#          heights are in BRICKS (one normal brick tall).
#      python preview_shape.py shapes/my_car.py --bricks-only
#      python make_model.py 11045-1 shapes/my_car.py out/my_car.ldr --scale 1 --bricks-only --render
#  A van: CABIN_LENGTH=9 HOOD_LENGTH=2.  A pickup truck: CABIN_LENGTH=4 HOOD_LENGTH=3.
# =====================================================================================================

LENGTH = 14           # studs, front to back
WIDTH = 6             # studs
BODY_HEIGHT = 2       # bricks, from the top of the wheels' first brick to the bottom of the windows
HOOD_LENGTH = 4       # studs from the front of the car to the windscreen
CABIN_LENGTH = 6      # studs
CABIN_HEIGHT = 2      # bricks (the bottom one is the windows, the rest is the roof)
WHEEL_SIZE = 3        # studs long; wheels are 2 bricks tall and 2 studs wide
LIGHTS = 1            # 1 = headlights at the front and tail lights at the back

BODY_COLOUR = 'dark azure'
ROOF_COLOUR = 'white'
WINDOW_COLOUR = 'black'
WHEEL_COLOUR = 'black'
HEADLIGHT_COLOUR = 'clear yellow'   # see-through yellow; 'white' works too
TAILLIGHT_COLOUR = 'red'

# =====================================================================================================
#  You don't need to change anything below this line.
# =====================================================================================================
COLOURS = {   # name -> Rebrickable colour id
    'black': 0, 'blue': 1, 'green': 2, 'red': 4, 'dark pink': 5, 'pink': 5, 'bright green': 10, 'yellow': 14,
    'white': 15, 'tan': 19, 'orange': 25, 'magenta': 26, 'lime': 27, 'dark tan': 28, 'bright pink': 29,
    'light pink': 29, 'lavender': 30, 'clear blue': 41, 'trans light blue': 41, 'trans pink': 45,
    'clear yellow': 46, 'trans yellow': 46, 'reddish brown': 70, 'brown': 70, 'light grey': 71, 'light gray': 71,
    'dark grey': 72, 'dark gray': 72, 'medium blue': 73, 'nougat': 84, 'medium nougat': 84, 'dark purple': 85,
    'bright light orange': 191, 'golden': 191, 'bright light yellow': 226, 'dark brown': 308, 'dark red': 320,
    'dark azure': 321, 'azure': 321, 'medium azure': 322,
}

# settings can also come from the command line:  --var BODY_COLOUR=red --var CABIN_LENGTH=8
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
L, W, BH, CH = _g['LENGTH'], _g['WIDTH'], _g['BODY_HEIGHT'], _g['CABIN_HEIGHT']
x0, x1 = snap(-L / 2 * S), snap(L / 2 * S)          # front and back
zr = snap(W / 2 * S)
body_top = 1 + BH                                    # bands: 0 = wheels only, 1 .. BH = body

body = (X > x0) & (X < x1) & (np.abs(Z) < zr) & (Y > B) & (Y < body_top * B)

# wheels: 2 x WHEEL_SIZE studs, 2 bricks tall; the top brick is part of the body so the body clips onto them
ws = _g['WHEEL_SIZE']
wheels = np.zeros_like(body)
for wx in (x0 + S, x1 - S - ws * S):
    wx = snap(wx)
    wheels |= (X > wx) & (X < wx + ws * S) & (np.abs(Z) > zr - 2 * S) & (np.abs(Z) < zr) & (Y > 0) & (Y < 2 * B)

# cabin: sits on the body, one stud in from each side
cx0 = snap(x0 + _g['HOOD_LENGTH'] * S)
cx1 = min(snap(cx0 + _g['CABIN_LENGTH'] * S), x1)
cabin = (X > cx0) & (X < cx1) & (np.abs(Z) < zr - S) & (Y > body_top * B) & (Y < (body_top + CH) * B)
glass = cabin & band(body_top)
inner = (X > cx0 + S) & (X < cx1 - S) & (np.abs(Z) < zr - 2 * S)        # cells not on the outside
pillars = (np.abs(Z) > zr - 2 * S) & ((X < cx0 + S) | (X > cx1 - S))   # the cabin's four corners stay body colour
windows = glass & ~inner & ~pillars

lights = np.zeros_like(body)
front_l = back_l = lights
if _g['LIGHTS']:
    # top body brick, one stud in from each side: the corner stays body colour so a body brick can hold the
    # corner below it (a lamp right on the corner leaves a 1x1 column that holds onto nothing)
    lamp = band(body_top - 1) & (np.abs(Z) > zr - 2 * S) & (np.abs(Z) < zr - S)
    front_l = lamp & (X < x0 + S)
    back_l = lamp & (X > x1 - S)

solid = body | wheels | cabin
col = np.full(solid.shape, colour(_g['BODY_COLOUR']))
col[cabin] = colour(_g['ROOF_COLOUR'])
col[cabin & band(body_top) & pillars] = colour(_g['BODY_COLOUR'])
col[windows] = colour(_g['WINDOW_COLOUR'])
col[wheels] = colour(_g['WHEEL_COLOUR'])
col[front_l] = colour(_g['HEADLIGHT_COLOUR'])
col[back_l] = colour(_g['TAILLIGHT_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
