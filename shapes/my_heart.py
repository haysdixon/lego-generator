GRID = (24, 12, 36)   # room to build in: 24 x 12 studs, 36 plates (12 bricks) tall
TITLE = 'My heart'

# =====================================================================================================
#  A heart standing up on a little stand, facing the front (-Z). Change the numbers and colour names.
#
#  Sizes:  width and thickness are in STUDS (the round bumps on top of a brick).
#          heights are in BRICKS (one normal brick tall).
#      python preview_shape.py shapes/my_heart.py --bricks-only
#      python make_model.py 11045-1 shapes/my_heart.py out/my_heart.ldr --scale 1 --bricks-only --render
# =====================================================================================================

WIDTH = 12            # studs, left to right
HEIGHT = 9            # bricks, bottom tip to top of the bumps
THICKNESS = 2         # studs, front to back (2 or more)
STAND = 1             # 1 = stands on a flat base, 0 = the tip sits on the table
STAND_LENGTH = 6      # studs
STAND_DEPTH = 4       # studs (wider than THICKNESS so it doesn't tip over)
OUTLINE = 0           # 1 = a border in OUTLINE_COLOUR along the top and the stepped edges

HEART_COLOUR = 'red'
OUTLINE_COLOUR = 'dark pink'
STAND_COLOUR = 'white'

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

# settings can also come from the command line:  --var HEART_COLOUR="dark pink" --var WIDTH=14
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
W, H, T = _g['WIDTH'], _g['HEIGHT'], _g['THICKNESS']
bottom = B if _g['STAND'] else 0

# the classic heart curve (x^2 + y^2 - 1)^3 <= x^2 y^3, stretched to WIDTH x HEIGHT
u = X / (W / 2 * S) * 1.14
v = -1.0 + (Y - bottom) / (H * B) * 2.25
heart = ((u ** 2 + v ** 2 - 1) ** 3 <= u ** 2 * v ** 3) & (Y > bottom) & (Y < bottom + H * B)
tip = 2 if not _g['STAND'] else max(2, _g['STAND_LENGTH'] - 2)   # the tip is wide enough to hold the stand's bricks together
heart |= band(int(round(bottom / B))) & (np.abs(X) < tip / 2 * S)
heart &= np.abs(Z) < T / 2 * S

stand = np.zeros_like(heart)
if _g['STAND']:
    stand = band(0) & (np.abs(X) < _g['STAND_LENGTH'] / 2 * S) & (np.abs(Z) < _g['STAND_DEPTH'] / 2 * S)

solid = heart | stand
col = np.full(solid.shape, colour(_g['HEART_COLOUR']))
if _g['OUTLINE']:
    # the border along the top and the stepped edges: cells with no heart above or below them. (Not the straight
    # sides: a 1-stud strip of another colour there has nothing above or below to click onto, and falls off.)
    inner = heart & np.roll(heart, 1, axis=1) & np.roll(heart, -1, axis=1)
    col[heart & ~inner & (Y > bottom + B)] = colour(_g['OUTLINE_COLOUR'])
col[stand] = colour(_g['STAND_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
