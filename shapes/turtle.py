TITLE = 'Turtle - remade from LEGO 71426 Piranha Plant parts'
BG, DG, RED, YEL, BLACK = 10, 2, 4, 14, 0
KEYC = (BG, DG, RED, YEL, BLACK)
# head 4 studs wide and raised on a neck; legs pushed out past the shell rim
DOMEY = float(os.environ.get("DOMEY", "95"))
shell_ = ell((0, 0, 0), (100, DOMEY, 118)) & (Y > 0)
head = ell((0, 34, -150), (40, 30, 38)) & (Y > 0)
neck = ell((0, 24, -112), (30, 22, 30)) & (Y > 0)
legs = (ell((-96, 7, -78), (30, 14, 28)) | ell((96, 7, -78), (30, 14, 28)) |
        ell((-96, 7, 82), (30, 14, 28)) | ell((96, 7, 82), (30, 14, 28))) & (Y > 0)
solid = shell_ | head | neck | legs
col = np.full(solid.shape, BG)
# yellow eyes on the sides of the head (head and legs share the shell colour so pieces can bond)
col[head & (abs(X) > 22) & (Y > 38) & (Y < 54) & (Z < -150) & (Z > -172)] = YEL
