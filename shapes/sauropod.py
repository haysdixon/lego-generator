GRID = (16, 40, 56)
TITLE = 'Long-neck dinosaur'
# Plush-style long-neck (sauropod) dinosaur. Front = -Z, Y up. Chubby body, thick neck and tail so
# every part stays at least 3-4 studs wide. SKIN/BELLY/EYE envs pick colours (Rebrickable ids).
SKIN = int(os.environ.get('SKIN', '27')); BELLY = int(os.environ.get('BELLY', str(SKIN))); EYE = int(os.environ.get('EYE', '0'))
KEYC = tuple(dict.fromkeys((SKIN, BELLY, EYE)))
body = ell((0, 120, 20), (68, 72, 115)) & (Y > 0)
solid = body.copy()
# neck: a chain of balls from the shoulders up and forward to the head
for t in np.linspace(0, 1, 14):
    cz = -60 - 110 * t; cy = 150 + 190 * t ** 0.8; r = 42 - 8 * t
    solid |= ell((0, cy, cz), (r, r, r))
B = 24 / SC; eb = int(350 // B)
# boxy head three bricks tall so the eye band has head bricks above and below it
head = sell((0, (eb + 0.5) * B, -185), (44, 1.45 * B, 54), 3)
# tail: tapering chain back and down to the ground
for t in np.linspace(0, 1, 14):
    cz = 110 + 150 * t; cy = 110 - 85 * t; r = 40 - 16 * t
    solid |= ell((0, cy, cz), (r, r, r)) & (Y > 0)
legs = np.zeros_like(body)
for lx in (-studs(2), studs(2)):
    for lz in (-50, 95):
        cx_, cz_ = snap(lx), snap(lz)
        legs |= box((cx_ - studs(1), 0, cz_ - studs(1)), (cx_ + studs(1), 80, cz_ + studs(1)))
solid |= head | legs
col = np.full(solid.shape, SKIN)
col[body & (Y < 75)] = BELLY
hz = Z[0, 0, :][head.any((0, 1))].min()
col[head & (Y > eb * B) & (Y < (eb + 1) * B) & (Z < hz + studs(2)) & (np.abs(X) > studs(0.5))] = EYE   # eyes: 1 brick tall on the sides
