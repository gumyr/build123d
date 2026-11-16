"""
Doubly-curved bracelet with an embossed label

name: bracelet.py
by:   Gumyr
date: January 7, 2026

desc:
      This model is a good "stress test" for OCCT because most of the final boundary
      surfaces are *freeform* (not analytic planes/cylinders/spheres). The geometry
      is assembled from:
        - a swept center section (using a curved solid end-face as the sweep profile)
        - two freeform "tip caps" built as Gordon surfaces (network of curves)
        - an optional embossed text label projected onto a curved solid
        - alignment holes for splitting/printing/assembly

      Key techniques demonstrated:
        - using location_at/position_at/tangent (%) to extract local frames & tangents
        - projecting curves onto a non-planar surface to create "true" 3D guide curves
        - Gordon surfaces to build high-quality doubly-curved skins
        - projecting faces (text) onto a complex solid and thickening them

"""

# [Code]
from build123d import *
from ocp_vscode import show

# Define input parameters
# - radii: ellipse radii (X, Y) controlling the bracelet centerline shape
# - width: bracelet width (along Z for the center sweep)
# - thickness: bracelet thickness (radial thickness of the cross section)
# - opening_angle: the missing angle that creates the wrist opening
# - label_str: optional text to emboss on the outside surface
# - Define input parameters
# radii, width, thickness, opening_angle, label_str = (45, 30), 25, 5, 80, "build123d"
radii, width, thickness, opening_angle, label_str = (45, 30), 25, 5, 80, ""

# Step 1: Create an elliptical arc defining the *centerline* of the bracelet.
# The arc is truncated to leave an opening (the "gap" where the bracelet goes on).
# Angles are in degrees; 270° points downward, which keeps the opening centered at the bottom.
center_arc = EllipticalCenterArc(
    (0, 0), *radii, 270 + opening_angle / 2, arc_size=360 - opening_angle
)

# Step 2: Create HALF of the end cross-section, positioned at the end of the arc.
# We build only half so we can later mirror it to enforce symmetry and reduce
# curve-network complexity when building the freeform tip.
#
# location_at(1) returns a local coordinate frame at the arc end (tangent-aware).
# x_dir is chosen so the section’s local "X" is well-defined and stable.
end_center_arc = center_arc.location_at(1, x_dir=(0, 0, 1))
half_x_section = EllipticalCenterArc(
    (0, 0), width / 2, thickness / 2, 90, arc_size=180
).locate(end_center_arc)

# Step 3: Create a doubly-curved "tip edge" curve.
# The tip edge must live in 3D and conform to the outside of the bracelet.
# To do that, we:
#   1) create a surface by extruding the center_arc into a sheet (a ribbon surface)
#   2) build a planar arc in a local frame at the end of that surface
#   3) project the planar arc onto the curved surface to get a true 3D curve
#
# The resulting tip_arc is a 3D edge that naturally matches the bracelet curvature.
center_surface = -Face.extrude(center_arc, (0, 0, 2 * width)).moved(
    Location((0, 0, -width), (0, 0, 180))
)
tip_center_loc = -center_surface.location_at(center_arc @ 1, x_dir=(1, 0, 0))
normal_at_tip_center = tip_center_loc.z_axis.direction

# A planar arc that would represent the outer boundary of the tip *if* the surface
# were flat. We immediately project it to make it truly conformal in 3D.
planar_tip_arc = CenterArc((0, 0), width / 2, 270, 180).locate(tip_center_loc).edge()
tip_arc = planar_tip_arc.project_to_shape(center_surface, -normal_at_tip_center)[0]

# Step 4: Build the tip as a Gordon surface (a surface fit through a curve network).
# Gordon surfaces are ideal when:
#   - you don’t have an obvious analytic surface
#   - curvature changes in two directions (doubly-curved "cap")
#   - you can define a consistent set of profile curves + guide curves
#
# Here:
#   - profiles define "across the tip" shape (section -> bulged spline -> mirrored section)
#   - guides define "along the tip" rails (start point -> projected 3D arc -> end point)
#
# Tangents are used to encourage smoothness where the tip joins the swept center section.
profile = Spline(
    half_x_section @ 0,
    tip_arc @ 0.5,
    half_x_section @ 1,
    tangents=(center_arc % 1, -(center_arc % 1)),
)
tip_surface = Face.make_gordon_surface(
    profiles=[half_x_section, profile, half_x_section.mirror(Plane.XY)],
    guides=[half_x_section @ 0, tip_arc, half_x_section @ 1],
)

# Step 5: Close the tip surface into a watertight Solid.
# tip_surface is the outer "skin"; we create a side face from its boundary wire
# and make a shell, then a solid.
tip_side = Face(tip_surface.wire())
tip = Solid(Shell([tip_side, tip_surface]))

# Step 6: Sweep the *flat end face* of the tip around the center arc.
# This is the trick that makes the center section compatible with the freeform tip:
# the sweep profile is the same face that bounds the tip, so the join is naturally aligned.
center_section = sweep(tip_side, center_arc).solid()

# Step 7: Assemble the bracelet from the center and two mirrored tips.
# Mirror across YZ to create the opposite end cap.
bracelet = Solid() + [tip, center_section, tip.mirror(Plane.YZ)]

# Step 8: Add an embossed label.
# This is often the hardest operation for OCCT in this model:
# projecting text onto a doubly-curved surface can create many small faces/edges,
# and thickening them adds even more boolean complexity.
if label_str:
    label = Text(label_str, font_size=width * 0.8, align=Align.CENTER)

    # Project the text onto the bracelet using a path-based placement along center_arc.
    # The parameter offsets the label so it sits centered along arc-length.
    p_labels = bracelet.project_faces(
        label, center_arc, 0.5 - 0.5 * (label.bounding_box().size.X) / center_arc.length
    )
    # Turn the projected faces into solids via thickening (embossing).
    embossed_label = [Solid.thicken(f, 0.5) for f in p_labels.faces()]
    bracelet += embossed_label

# Step 9: Add alignment holes to aid assembly after 3D printing in two halves.
# These are placed at evenly spaced locations along the arc (including both ends).
# A small clearance (+0.15) is included for typical FDM tolerances.
alignment_holes = [
    Pos(p) * Cylinder(1.75 / 2 + 0.15, 8)
    for p in [center_arc.position_at(i / 4) for i in range(5)]
]
bracelet -= alignment_holes

show(bracelet)
# [End]
