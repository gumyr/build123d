from alg123d import *

obj = Box(5, 5, 1)
for plane in [Plane(f) for f in obj.faces().filter_by(Axis.Z)]:
    obj -= plane * Sphere(1.8)

if "show_object" in locals():
    show_object(obj)
