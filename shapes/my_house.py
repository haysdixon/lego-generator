GRID = (24, 20, 45)   # room to build in: 24 x 20 studs, 45 plates (15 bricks) tall
TITLE = 'My house'

# =====================================================================================================
#  A little house with a stepped roof, a door, windows and a chimney. The door is at the front (-Z).
#  Change the numbers and colour names.
#
#  Sizes:  length and depth are in STUDS (the round bumps on top of a brick).
#          heights are in BRICKS (one normal brick tall).
#      python preview_shape.py shapes/my_house.py --bricks-only
#      python make_model.py 11045-1 shapes/my_house.py out/my_house.ldr --scale 1 --bricks-only --render
# =====================================================================================================

LENGTH = 10           # studs, left to right along the front
DEPTH = 8             # studs, front to back
WALL_HEIGHT = 4       # bricks
EAVES = 1             # studs the roof overhangs the walls (0 or 1)
DOOR = 1              # 1 = a door in the middle of the front
WINDOWS = 1           # 1 = a window each side of the door and one on each end wall
CHIMNEY = 1           # 1 = a chimney on the roof

WALL_COLOUR = 'white'
ROOF_COLOUR = 'red'
DOOR_COLOUR = 'nougat'
WINDOW_COLOUR = 'dark azure'   # 'clear blue' uses see-through bricks, but 11045 has only 6 of them (1x1)
CHIMNEY_COLOUR = 'black'
BASE_COLOUR = 'white'          # bottom brick of the walls

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

# settings can also come from the command line:  --var ROOF_COLOUR="dark azure" --var LENGTH=12
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
L, D, WH, E = _g['LENGTH'], _g['DEPTH'], _g['WALL_HEIGHT'], _g['EAVES']
xr, zr = snap(L / 2 * S), snap(D / 2 * S)           # half length and half depth, on stud lines

walls = (np.abs(X) < xr) & (np.abs(Z) < zr) & (Y > 0) & (Y < WH * B)

# roof: each brick layer is one stud narrower front and back than the one below, until it is 2 studs wide
roof = np.zeros_like(walls)
k = 0
while D + 2 * E - 2 * k >= 2:
    half = zr + (E - k) * S
    roof |= band(WH + k) & (np.abs(X) < xr + E * S) & (np.abs(Z) < half)
    k += 1
roof_top = WH + k   # bands

front = Z < -zr + S                                 # the front row of cells
door = np.zeros_like(walls)
if _g['DOOR'] and WH >= 3:
    door = front & (np.abs(X) < S) & (Y > 0) & (Y < min(3, WH - 1) * B)
windows = np.zeros_like(walls)
if _g['WINDOWS'] and WH >= 3:
    win_band = (Y > B) & (Y < min(3, WH - 1) * B)       # two bricks tall, level with the top of the door
    wx = snap((xr + S) / 2)                             # halfway between the door and the corner
    for sx in (-1, 1):
        windows |= front & win_band & (np.abs(X - sx * wx) < S)                       # front, either side of the door
        windows |= (sx * X > xr - S) & win_band & (np.abs(Z) < S)                     # end walls, in the middle

chimney = np.zeros_like(walls)
if _g['CHIMNEY'] and k >= 3:
    cx, cz = snap(L / 4 * S), snap(zr / 2)          # toward the right and the back, on a step of the roof
    chimney = (np.abs(X - cx) < S) & (np.abs(Z - cz) < S) & (Y > WH * B) & (Y < (roof_top + 1) * B)

solid = walls | roof | chimney
col = np.full(solid.shape, colour(_g['WALL_COLOUR']))
col[walls & band(0)] = colour(_g['BASE_COLOUR'])
col[roof] = colour(_g['ROOF_COLOUR'])
col[chimney] = colour(_g['CHIMNEY_COLOUR'])
col[door] = colour(_g['DOOR_COLOUR'])
col[windows] = colour(_g['WINDOW_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
