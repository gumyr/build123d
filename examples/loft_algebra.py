from math import pi, sin
from build123d import *
from build123d.part_operations import *
import alg123d as ad

slice_count = 10

art = Sketch()
for i in range(slice_count + 1):
    plane = Plane(origin=(0, 0, i * 3), z_dir=(0, 0, 1))
    art += plane * Circle(10 * sin(i * pi / slice_count) + 5)

art = loft(art)
top_bottom = art.faces(GeomType.PLANE)
art = ad.shell(art, openings=top_bottom, amount=0.5)

if "show_object" in locals():
    show_object(art, name="art")
