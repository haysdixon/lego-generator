GRID = (24, 14, 36)
TITLE = 'Holstein cow'
# Holstein cow, traced from a hand-drawn doodle by Hays Dixon. Units: LDU before scaling; length along X (head at -X),
# width along Z, Y up. Doodle px -> LDU: x = (px - 735) * 0.5, y = (780 - px_y) * 0.5. Small features are
# snapped to the stud grid so legs are exactly 2x2 studs and the tongue is exactly 1 stud.
# Colour ids are Rebrickable/LDraw: 15 white, 0 black, 19 tan, 29 bright pink, 4 red. MUZZLE env overrides pink.
WHITE, BLACK, TAN, PINK, RED = 15, 0, 19, int(os.environ.get('MUZZLE', '29')), 4
KEYC = (WHITE, BLACK, TAN, PINK, RED)
XOFF = 40   # shift the cow toward +X so it is centred on the grid

body = sell((XOFF, 223, 0), (190, 107, 100), 3)
head = sell((XOFF - 245, 250, 0), (55, 70, 48), 3)
legs = np.zeros_like(body)
for lx in (XOFF - 130, XOFF + 120):
    for lz in (-studs(2), studs(2)):           # legs on the outer columns, 2-stud gap between them
        cx_, cz_ = snap(lx), snap(lz)          # centre on a stud boundary -> exactly 2 studs each way
        legs |= box((cx_ - studs(1), 0, cz_ - studs(1)), (cx_ + studs(1), 130, cz_ + studs(1)))
ears = box((snap(XOFF - 236), 300, -studs(3)), (snap(XOFF - 236) + studs(2), 326, studs(3)))   # one 2x6 strip across the head top: its ends are the ears, the head below anchors it
# horns: stepped points on the ear-strip ends, a 1x2 then a 1x1 standing up (Y bands chosen for scale 0.7, QY=3)
ear_x0 = snap(XOFF - 236)
horn1 = box((ear_x0, 345, -studs(3)), (ear_x0 + studs(2), 375, studs(3))) & (np.abs(Z) > studs(2))
horn2 = box((ear_x0, 380, -studs(3)), (ear_x0 + studs(1), 410, studs(3))) & (np.abs(Z) > studs(2))
horns = horn1 | horn2
face_x = X[:, 0, 0][np.nonzero(head.any((1, 2)))[0][0]]       # centre of the head's front-most column
# muzzle: a 2-deep, 4-wide snout across the bottom of the face, sticking out 1 stud in front
# (a sideways 2x4 brick), instead of a recessed pink slot
snout = box((face_x - studs(1) - 1, 172, -studs(2)), (face_x + 1, 202, studs(2)))
# small tongue: one 1x1 hanging under the protruding front row, just off centre
tongue = box((face_x - studs(1) - 1, 146, 1), (face_x - studs(1) + 1, 172, studs(1) - 1))

solid = body | head | snout | legs | ears | horns | tongue
col = np.full(solid.shape, WHITE)
# black patches (from the doodle's side view), painted through the body so both sides and the top get them
spots = (ell((XOFF - 88, 231, 0), (52, 30, 999)) | ell((XOFF + 75, 300, 0), (110, 75, 999)) |
         ell((XOFF - 52, 140, 0), (125, 30, 999)))
col[spots & body & ~legs] = BLACK
col[legs & (Y < 22)] = TAN                                   # hooves
col[snout] = PINK                                            # muzzle
col[ears | horns] = TAN
col[tongue] = RED
col[head & (np.abs(Z) > 34) & (Y > 262) & (Y < 296) & (X > XOFF - 282) & (X < XOFF - 250)] = BLACK  # eyes (a full brick tall)
