GRID = (18, 26, 36)
TITLE = 'Potbelly pig'
# Features are sized to whole bricks (B) so brick-only builds keep the snout, ears and eyes.
# Env colours: BODY (default 5 dark pink, 11045's pink), SNOUT, EYE, EAR.
E = lambda k, d: int(os.environ.get(k, d))
BODY, SNOUT, EYE = E('BODY', '5'), E('SNOUT', '5'), E('EYE', '0'); EAR = E('EAR', str(BODY))
KEYC = tuple(dict.fromkeys((BODY, SNOUT, EYE, EAR)))
B = 24 / SC
band = lambda n: (Y > n * B) & (Y < (n + 1) * B)
body = sell((0, 115, 10), (80, 74, 120), 2.6) & (Y > 0)
belly = ell((0, 85, 15), (72, 55, 100)) & (Y > 0)
head = sell((0, 140, -125), (60, 58, 52), 2.5)
legs = np.zeros_like(body)
for lx in (-studs(2), studs(2)):
    for lz in (-70, 90):
        cx_, cz_ = snap(lx), snap(lz)
        legs |= box((cx_ - studs(1), 0, cz_ - studs(1)), (cx_ + studs(1), 60, cz_ + studs(1)))
hz = Z[0, 0, :][head.any((0, 1))].min()                             # front of the head
hy = int(140 // B)
snout = (band(hy - 1) | band(hy)) & (Z >= hz - studs(1)) & (Z < hz) & (np.abs(X) <= studs(1.5))   # 3x1 studs, 2 bricks
top = int(Y[0, :, 0][head.any((0, 2))].max() // B)
# ears sit only on cells where the head's top band exists, so they always click on
headtop = (head & band(top)).any(1)[:, None, :]
ears = band(top + 1) & headtop & (np.abs(X) >= studs(1)) & (np.abs(X) <= studs(3)) & (Z > -125 - studs(1.5)) & (Z < -125 + studs(0.5))
tz = Z[0, 0, :][body.any((0, 1))].max()
tail = band(int(150 // B)) & (np.abs(X) <= studs(0.5)) & (Z > tz) & (Z <= tz + studs(1))
solid = body | belly | head | legs | snout | ears | tail
col = np.full(solid.shape, BODY)
col[snout] = SNOUT; col[ears] = EAR
col[head & band(hy + 1) & (Z < hz + studs(2)) & (np.abs(X) >= studs(1)) & (np.abs(X) <= studs(2.5))] = EYE
