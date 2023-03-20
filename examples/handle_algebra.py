from alg123d import *

segment_count = 6

# Create a path for the sweep along the handle - added to pending_edges
handle_center_line = Spline(
    ((-10, 0, 0), (0, 0, 5), (10, 0, 0)),
    tangents=((0, 0, 1), (0, 0, -1)),
    tangent_scalars=(1.5, 1.5),
)
# Record the center line for display and workplane creation
handle_path = handle_center_line.edges()[0]


# Create the cross sections - added to pending_faces

with LazyAlgCompound() as sections:
    for i in range(segment_count + 1):
        plane = Plane(
            origin=handle_path @ (i / segment_count),
            z_dir=handle_path % (i / segment_count),
        )
        if i % segment_count == 0:
            section = plane * Circle(1)
        else:
            section = plane * Rectangle(1.25, 3)
            section = fillet(section, section.vertices(), radius=0.2)
        sections += section

# Create the handle by sweeping along the path
handle = sweep(sections.faces(), path=handle_path, multisection=True)

if "show_object" in locals():
    show_object(handle_path.wrapped, name="handle_path")
    for i, section in enumerate(sections):
        show_object(section.wrapped, name="section" + str(i))
    show_object(handle, name="handle", options=dict(alpha=0.6))
