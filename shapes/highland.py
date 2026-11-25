GRID = (24, 16, 40)
TITLE = 'Highland cow'
# Highland cow, built on holstein.py so the pair matches: same body, head,
# 2x2 legs, protruding 2x4 snout and head-top strip, same Y bands (tuned for scale 0.7, QY=3).
# Highland changes: horns step outward past the 2x6 strip (1x2 overhanging 1 stud) then up to a dark tip,
# a fringe/forelock covers the eyes, a darker belly band, dark snout and hooves.
# Env colours (Rebrickable ids): COAT, COAT2 (belly band), FRINGE, HORN, TIP, NOSE, HOOF.
E = lambda k, d: int(os.environ.get(k, d))
COAT, COAT2, FRINGE = E('COAT', '191'), E('COAT2', '84'), E('FRINGE', '84')
HORN, TIP, NOSE, HOOF = E('HORN', '15'), E('TIP', '0'), E('NOSE', '0'), E('HOOF', '0')
KEYC = tuple(dict.fromkeys((COAT, COAT2, FRINGE, HORN, TIP, NOSE, HOOF)))
XOFF = 40
body = sell((XOFF, 223, 0), (190, 107, 100), 3)
head = sell((XOFF - 245, 250, 0), (55, 70, 48), 3)
legs = np.zeros_like(body)
for lx in (XOFF - 130, XOFF + 120):
    for lz in (-studs(2), studs(2)):
        cx_, cz_ = snap(lx), snap(lz)
        legs |= box((cx_ - studs(1), 0, cz_ - studs(1)), (cx_ + studs(1), 130, cz_ + studs(1)))
ear_x0 = snap(XOFF - 236)
strip = box((ear_x0, 300, -studs(3)), (ear_x0 + studs(2), 326, studs(3)))          # one 2x6 brick across the head top (as the Holstein)
horn1 = box((ear_x0, 345, -studs(4)), (ear_x0 + studs(1), 375, studs(4))) & (np.abs(Z) > studs(2))   # 1x2 on the strip end, sticking out 1 stud
horn2 = box((ear_x0, 380, -studs(4)), (ear_x0 + studs(1), 410, studs(4))) & (np.abs(Z) > studs(3))   # 1x1 tip on the outer stud
face_x = X[:, 0, 0][np.nonzero(head.any((1, 2)))[0][0]]
snout = box((face_x - studs(1) - 1, 172, -studs(2)), (face_x + 1, 202, studs(2)))
forelock = box((face_x - studs(1) - 1, 262, -studs(1.5)), (face_x + 1, 296, studs(1.5)))   # bangs over the eyes
solid = body | head | snout | legs | strip | horn1 | horn2 | forelock
col = np.full(solid.shape, COAT)
ix = np.floor(X * SC / 20).astype(int); iz = np.floor(Z * SC / 20).astype(int)
col[body & ~legs & (Y < 160)] = COAT2                         # long darker hair hanging along the belly (big blocks: thin streaks broke the build)
col[head & (Y > 262) & (X < face_x + studs(2))] = FRINGE             # fringe across the brow
col[forelock] = FRINGE
col[strip | horn1] = HORN
col[horn2] = TIP
col[snout] = NOSE
col[legs & (Y < 22)] = HOOF
