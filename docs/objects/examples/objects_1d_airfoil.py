from build123d import *
from tools.svg import write_svg

# from ocp_vscode import show_all, set_defaults, Camera

# set_defaults(reset_camera=Camera.KEEP)

with BuildLine() as airfoil:
    l1 = Airfoil("2213")

layers = {"visible": {"shapes": l1}}
write_svg("example_airfoil", layers)

# show_all()
