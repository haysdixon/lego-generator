GRID = (20, 20, 36)   # room to build in: 20 x 20 studs, 36 plates (12 bricks) tall
TITLE = 'My mug'

# =====================================================================================================
#  A mug with a handle, and coffee inside if you like. Change the numbers and colour names.
#
#  Sizes:  across and handle are in STUDS (the round bumps on top of a brick).
#          heights are in BRICKS (one normal brick tall).
#  The handle is on the right when you look at the mug from the front (-Z).
#      python preview_shape.py shapes/my_mug.py --bricks-only
#      python make_model.py 11045-1 shapes/my_mug.py out/my_mug.ldr --scale 1 --bricks-only --render
# =====================================================================================================

ACROSS = 8            # studs, outside width of the mug (6 or more)
HEIGHT = 5            # bricks, including the bottom
WALL = 2              # studs, wall thickness (2 holds together best)
ROUNDNESS = 3         # 2 = round, 3 = rounded square, 6 or more = square
HANDLE = 1            # 1 = handle, 0 = none
HANDLE_OUT = 2        # studs the handle sticks out from the side (2 or 3)
COFFEE = 1            # 1 = filled with a drink, 0 = empty
COFFEE_DEPTH = 1      # bricks between the drink and the rim (1 or more)

MUG_COLOUR = 'white'
STRIPE_COLOUR = 'red'      # one brick-high band around the middle ('none' = no stripe)
HANDLE_COLOUR = 'white'
COFFEE_COLOUR = 'black'    # 'nougat' looks like a latte

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

# settings can also come from the command line:  --var MUG_COLOUR=lime --var HEIGHT=6
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
A, H, WL, P = _g['ACROSS'], _g['HEIGHT'], _g['WALL'], _g['ROUNDNESS']
plan = lambda r: (np.abs(X / r) ** P + np.abs(Z / r) ** P) <= 1   # rounded square r raw units from the centre

outside = plan(A / 2 * S) & (Y > 0) & (Y < H * B)
inside = plan((A / 2 - WL) * S) & (Y > B)          # the hole; the bottom brick stays solid
cup = outside & ~inside

drink = np.zeros_like(cup)
if _g['COFFEE'] and H - 1 - _g['COFFEE_DEPTH'] >= 1:
    drink = inside & (Y < (H - _g['COFFEE_DEPTH']) * B)   # fills the hole up to the drink's surface

# handle: a closed loop on the +X side. Its top and bottom bars reach 2 studs into the wall (so their bricks
# clip onto the wall bricks above and below), and an upright post joins them at the outer end.
handle = np.zeros_like(cup)
if _g['HANDLE'] and H >= 4:
    edge = X[:, 0, 0][np.nonzero(outside.any((1, 2)))[0][-1]] + S / 2   # outer face of the wall
    hz = np.abs(Z) < S                                                    # 2 studs wide
    out = _g['HANDLE_OUT']
    top_band, bot_band = H - 2, 1
    bar = hz & (X > edge - 2 * S) & (X < edge + out * S)
    post = hz & (X > edge + (out - 1) * S) & (X < edge + out * S)
    handle = (bar & (band(top_band) | band(bot_band))) | (post & (Y > bot_band * B) & (Y < (top_band + 1) * B))
    handle &= ~inside

solid = cup | drink | handle
col = np.full(solid.shape, colour(_g['MUG_COLOUR']))
if str(_g['STRIPE_COLOUR']).lower() != 'none' and H >= 4:
    col[cup & band(H // 2)] = colour(_g['STRIPE_COLOUR'])
col[handle & ~cup] = colour(_g['HANDLE_COLOUR'])
col[drink] = colour(_g['COFFEE_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
