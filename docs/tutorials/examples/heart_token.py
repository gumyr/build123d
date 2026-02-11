# [Code]
from build123d import *
from ocp_vscode import show

# Create the edges of one half the heart surface
l1 = JernArc((0, 0), (1, 1.4), 40, -17)
l2 = JernArc(l1 @ 1, l1 % 1, 4.5, 175)
l3 = IntersectingLine(l2 @ 1, l2 % 1, other=Edge.make_line((0, 0), (0, 20)))
l4 = ThreePointArc(l3 @ 1, (0, 0, 1.5) + (l3 @ 1 + l1 @ 0) / 2, l1 @ 0)
heart_half = Wire([l1, l2, l3, l4])
# [SurfaceEdges]

# Create a point elevated off the center
surface_pnt = l2.arc_center + (0, 0, 1.5)
# [SurfacePoint]

# Create the surface from the edges and point
top_right_surface = Pos(Z=0.5) * -Face.make_surface(heart_half, [surface_pnt])
# [Surface]

# Use the mirror method to create the other top and bottom surfaces
top_left_surface = top_right_surface.mirror(Plane.YZ)
bottom_right_surface = top_right_surface.mirror(Plane.XY)
bottom_left_surface = -top_left_surface.mirror(Plane.XY)
# [Surfaces]

# Create the left and right sides
left_wire = Wire([l3, l2, l1])
left_side = Pos(Z=-0.5) * Shell.extrude(left_wire, (0, 0, 1))
right_side = left_side.mirror(Plane.YZ)
# [Sides]

# Put all of the faces together into a Shell/Solid
heart = Solid(
    Shell(
        [
            top_right_surface,
            top_left_surface,
            bottom_right_surface,
            bottom_left_surface,
            left_side,
            right_side,
        ]
    )
)
# [Solid]

# Build a frame around the heart
with BuildPart() as heart_token:
    with BuildSketch() as outline:
        with BuildLine():
            add(l1)
            add(l2)
            add(l3)
            Line(l3 @ 1, l1 @ 0)
        make_face()
        mirror(about=Plane.YZ)
        center = outline.sketch
        offset(amount=2, kind=Kind.INTERSECTION)
        add(center, mode=Mode.SUBTRACT)
    extrude(amount=2, both=True)
    add(heart)

heart_token.part.color = "Red"

show(heart_token)
# [End]
# export_gltf(heart_token.part, "heart_token.glb", binary=True)
