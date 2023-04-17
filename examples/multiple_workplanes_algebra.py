from build123d import *

obj = Box(5, 5, 1)
planes = [Plane(f) for f in obj.faces().filter_by(Axis.Z)]
obj -= planes * Sphere(1.8)

if "show_object" in locals():
    show_object(obj)
