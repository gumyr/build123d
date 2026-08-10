from build123d import *
from ocp_vscode import show

obj = Box(5, 5, 1)
planes = [Plane(f) for f in obj.faces().filter_by(Axis.Z)]
obj -= planes * Sphere(1.8)

show(obj)
