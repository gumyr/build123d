from math import pi, sin
from alg123d import *

slice_count = 10

art = AlgCompound()
for i in range(slice_count + 1):
    plane = Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))
    art += plane * Circle(10 * sin(i * pi / slice_count) + 5)

art = loft(art)
top_bottom = art.faces(GeomType.PLANE)
art = shell(art, openings=top_bottom, amount=0.5)

reset_show()
if "show_object" in locals():
    show_object(art, name="art")
