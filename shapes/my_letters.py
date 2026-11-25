GRID = (64, 10, 30)   # room to build in: 64 x 10 studs, 30 plates (10 bricks) tall. Longer words: add 5 to the
                      # first number for each extra letter (it fits about 11 letters now).
TITLE = 'My letters'

# =====================================================================================================
#  A word in big block letters standing on a base, reading from the front (-Z). Change the word and colours.
#
#  Letters are 4 studs wide (M and W are 5) and 7 bricks tall. A-Z, 0-9 and spaces work.
#      python preview_shape.py shapes/my_letters.py --bricks-only
#      python make_model.py 11045-1 shapes/my_letters.py out/my_letters.ldr --scale 1 --bricks-only --render
#      python make_model.py 11045-1 shapes/my_letters.py out/hi.ldr --scale 1 --bricks-only --var TEXT=HI
# =====================================================================================================

TEXT = 'HELLO'
THICKNESS = 2         # studs, front to back (2 or more)
GAP = 1               # studs between letters
BASE = 2              # bricks: the letters stand on a base that holds them together (2 recommended, 0 = none)
BASE_DEPTH = 4        # studs, front to back

# a list of colours the letters take in turn. Thin letter strokes use 1x2 and 1x1 bricks, and 11045 has only 20 and
# 14 of those per colour, so give each colour about 2 letters at most: 'red, lime' is fine for 4 letters, not for 6.
LETTER_COLOURS = 'red, golden, lime, dark azure, dark pink'
BASE_COLOUR = 'white'

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

# settings can also come from the command line:  --var TEXT=LOVE --var LETTER_COLOURS=red
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

# Block font, 7 bricks tall, mostly 4 studs wide. Every pixel is 1 stud wide and 1 brick tall. The rules that
# make it hold together: every stroke sits on a stroke in the row below it (the generator builds bottom-up),
# crossbars are at most 4 studs long, so one brick can bridge both uprights, and no 3-stud stroke has a loose end
# (11045 has no 3-long bricks).
FONT = {
    'A': '#### #..# #..# #### #..# #..# #..#', 'B': '##.. #.## #..# #### #..# #..# ####',
    'C': '#### #... #... #... #... #... ####', 'D': '##.. #.## #..# #..# #..# #..# ####',
    'E': '#### #... #... ##.. #... #... ####', 'F': '#### #... #... ##.. #... #... #...',
    'G': '#### #... #... #.## #..# #..# ####', 'H': '#..# #..# #..# #### #..# #..# #..#',
    'I': '#### .##. .##. .##. .##. .##. ####', 'J': '..## ...# ...# ...# #..# #..# ####',
    'K': '#..# #.## ###. ##.. ###. #.## #..#', 'L': '#... #... #... #... #... #... ####',
    'M': '#...# ##.## ##### #...# #...# #...# #...#', 'N': '#..# ##.# #### #.## #..# #..# #..#',
    'O': '#### #..# #..# #..# #..# #..# ####', 'P': '#### #..# #..# #### #... #... #...',
    'Q': '#### #..# #..# #..# #.## #### ...#', 'R': '#### #..# #..# #### #.#. #.## #..#',
    'S': '#### #... #... #### ...# ...# ####', 'T': '#### .##. .##. .##. .##. .##. .##.',
    'U': '#..# #..# #..# #..# #..# #..# ####', 'V': '#..# #..# #..# #..# #### .##. .##.',
    'W': '#...# #...# #...# #...# ##### ##.## #...#', 'X': '#..# #### .##. .##. .##. #### #..#',
    'Y': '#..# #..# #### .##. .##. .##. .##.', 'Z': '#### ...# ..## .##. ##.. #... ####',
    '0': '#### #..# #.## ##.# #..# #..# ####', '1': '.##. .##. .##. .##. .##. .##. ####',
    '2': '#### ...# ...# #### #... #... ####', '3': '#### ...# ...# ..## ...# ...# ####',
    '4': '#..# #..# #..# #### ...# ...# ...#', '5': '#### #... #... #### ...# ...# ####',
    '6': '#### #... #... #### #..# #..# ####', '7': '#### ...# ...# ..## ..#. ..#. ..#.',
    '8': '#### #..# #..# #### #..# #..# ####', '9': '#### #..# #..# #### ...# ...# ####',
    ' ': '... ... ... ... ... ... ...',
}
text = str(_g['TEXT']).upper()
bad = sorted(set(text) - set(FONT))
if bad:
    raise SystemExit('these characters are not in the font: ' + ' '.join(bad) + '  (use A-Z, 0-9 and spaces)')
names = [n.strip() for n in str(_g['LETTER_COLOURS']).split(',') if n.strip()]
T, gap = _g['THICKNESS'], _g['GAP']
widths = [len(FONT[ch].split()[0]) for ch in text]
width = sum(widths) + (len(text) - 1) * gap          # studs
if width + 2 + 4 > GRID[0]:
    raise SystemExit(f'"{text}" is {width} studs long: raise the first number of GRID to at least {width + 6}')

base_h = _g['BASE']
x_left = snap(-width / 2 * S)
solid = np.zeros(X.shape, bool)
col = np.zeros(X.shape, int)
depth = np.abs(Z) < T / 2 * S
x = x_left                                            # the word reads left to right from the front (-Z): +X
n = 0
for ch, w in zip(text, widths):
    c = colour(names[n % len(names)])
    n += ch != ' '
    for r, row in enumerate(FONT[ch].split()):
        yb = (base_h + 6 - r) * B                     # row 0 is the top
        for k, px in enumerate(row):
            if px == '#':
                cell = depth & (X > x + k * S) & (X < x + (k + 1) * S) & (Y > yb) & (Y < yb + B)
                solid |= cell
                col[cell] = c
    x += (w + gap) * S
if base_h:
    base = (np.abs(X) < snap((width / 2 + 1) * S)) & (np.abs(Z) < _g['BASE_DEPTH'] / 2 * S) & (Y > 0) & (Y < base_h * B)
    solid |= base
    col[base] = colour(_g['BASE_COLOUR'])
KEYC = tuple(dict.fromkeys(int(c) for c in np.unique(col[solid])))
