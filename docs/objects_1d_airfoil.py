from build123d import *

# from ocp_vscode import show_all, set_defaults, Camera

# set_defaults(reset_camera=Camera.KEEP)

with BuildLine() as airfoil:
    l1 = Airfoil("2213")
s = 100 / max(*airfoil.line.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(l1)
svg.write("assets/example_airfoil.svg")
# show_all()
