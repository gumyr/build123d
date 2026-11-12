"""
A hinged box tutorial

name: hinged_box.py
by:   Gumyr
date: November 11th 2026

desc:
    Every code example in the "A hinged box" tutorial lives here, between
    pairs of ``# [name]`` markers that the page includes with
    ``literalinclude``, and this script also renders the SVG images the page
    embeds. The box and the lid are written twice, once in builder mode and
    once in algebra mode, and the two are checked against each other so that
    the tabs on the page cannot drift apart. Run it from its own directory;
    the images are written to ``assets/hinged_box``.

license:

    Copyright 2026 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

from pathlib import Path

from build123d.topology import Shape

# [setup]
import copy

from build123d import *

leaf_width, leaf_length, leaf_thickness = 50, 120, 2
pin_diameter = 5

box_length, box_depth, box_height = 200, 150, 80
wall_thickness, lid_thickness = 12, 12
pilot_radius, pilot_depth = 3, 10
# [setup]

OUTPUT = Path("assets/hinged_box")
OUTPUT.mkdir(parents=True, exist_ok=True)


def render(
    parts: list[Shape],
    name: str,
    joints: list[Joint] | None = None,
    viewpoint=(-120, -160, 120),
) -> None:
    """Write parts as an SVG line drawing, with the symbols of ``joints`` in red."""
    scene = Compound(
        children=[
            PLAIN_SCREW.located(part.location) if part in SCREWS else copy.copy(part)
            for part in parts
        ]
    )
    look_at = scene.bounding_box().center()
    camera = Vector(viewpoint) + look_at
    visible, hidden = scene.drawing_view(camera, look_at=look_at)
    marks = []
    for joint in joints or []:
        symbol_visible, symbol_hidden = joint.symbol.drawing_view(
            camera, look_at=look_at
        )
        marks += symbol_visible + symbol_hidden
    size = Compound(children=visible + hidden + marks).bounding_box().size
    exporter = ExportSVG(scale=100 / max(size.X, size.Y), margin=4)
    exporter.add_layer("Hidden", line_color=0xB0B0B0, line_type=LineType.ISO_DOT)
    exporter.add_layer("Visible", line_weight=0.4)
    exporter.add_layer("Joints", line_color=0xD03030, line_weight=0.5)
    exporter.add_shape(hidden, layer="Hidden")
    exporter.add_shape(visible, layer="Visible")
    if marks:
        exporter.add_shape(marks, layer="Joints")
    exporter.write(OUTPUT / f"hinged_{name}.svg")


# The thread of the imported screw takes about ten seconds a screw to draw
# with hidden lines removed. In the pictures of the whole box, where the
# threads are out of sight, a plain screw of the same size stands in for it.
SCREWS: list[Shape] = []
PLAIN_SCREW = revolve(
    Plane.XZ * Polygon((0, 0), (5.1, 0), (3, -2.1), (3, -12), (0, -12), align=None)
) - Box(12, 1.2, 2.4)


def same(first: Shape, second: Shape) -> bool:
    """Do the builder and algebra versions of a part make the same shape?"""
    return (
        abs(first.volume - second.volume) < 1e-6
        and (first.bounding_box().size - second.bounding_box().size).length < 1e-6
        and len(first.faces()) == len(second.faces())
    )


def overlap(first: Shape, second: Shape) -> float:
    """The volume two parts have in common."""
    common = first.intersect(second)
    return 0.0 if common is None else sum(s.volume for s in common.solids())


# ---------------------------------------------------------------------------
# Step 2: a hinge leaf
# ---------------------------------------------------------------------------
# [leaf]
class HingeLeaf(BasePartObject):
    """One leaf of a butt hinge, rolled from sheet metal"""

    def __init__(
        self,
        width: float,
        length: float,
        thickness: float,
        pin_diameter: float,
        outer: bool = True,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        screw_inset, screw_spacing = 0.6 * width, length / 3
        notch_count, notch_length = (2, length / 4) if outer else (3, length / 6)

        with BuildPart() as leaf:
            with BuildSheet(
                thickness=thickness, sheet_surface=SheetSurface.OUTSIDE
            ) as sheet:
                with BuildSketch() as blank:
                    Rectangle(width, length, align=(Align.MIN, Align.CENTER))
                    with GridLocations(0, 5 * length / 12, 1, notch_count):
                        Rectangle(5 * thickness, notch_length, mode=Mode.SUBTRACT)
                hem(
                    sheet.rims().group_by(Axis.X)[0],
                    HemType.ROLLED,
                    radius=pin_diameter / 2,
                )
            thicken()

            with Locations((screw_inset, 0, thickness)):
                with GridLocations(0, screw_spacing, 1, 3):
                    CounterSinkHole(radius=3, counter_sink_radius=5)

        super().__init__(part=leaf.part, rotation=rotation, align=align, mode=mode)
        self.barrel_radius = pin_diameter / 2 + thickness
        self.screw_inset, self.screw_spacing = screw_inset, screw_spacing
        self.label = "outer leaf" if outer else "inner leaf"


box_leaf = HingeLeaf(leaf_width, leaf_length, leaf_thickness, pin_diameter)
lid_leaf = HingeLeaf(leaf_width, leaf_length, leaf_thickness, pin_diameter, outer=False)
# [leaf]

assert not box_leaf.joints and not lid_leaf.joints
bare_leaves = box_leaf, lid_leaf
render(
    [box_leaf, Pos(-12, 0, 0) * Rot(Z=180) * lid_leaf],
    "leaves",
    viewpoint=(-60, -140, 130),
)


# ---------------------------------------------------------------------------
# Step 3: joints on the leaf
# ---------------------------------------------------------------------------
# [leaf_joints]
class HingeLeaf(BasePartObject):
    """One leaf of a butt hinge, rolled from sheet metal"""

    def __init__(
        self,
        width: float,
        length: float,
        thickness: float,
        pin_diameter: float,
        outer: bool = True,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        screw_inset, screw_spacing = 0.6 * width, length / 3
        notch_count, notch_length = (2, length / 4) if outer else (3, length / 6)

        with BuildPart() as leaf:
            with BuildSheet(
                thickness=thickness, sheet_surface=SheetSurface.OUTSIDE
            ) as sheet:
                with BuildSketch() as blank:
                    Rectangle(width, length, align=(Align.MIN, Align.CENTER))
                    with GridLocations(0, 5 * length / 12, 1, notch_count):
                        Rectangle(5 * thickness, notch_length, mode=Mode.SUBTRACT)
                hem(
                    sheet.rims().group_by(Axis.X)[0],
                    HemType.ROLLED,
                    radius=pin_diameter / 2,
                )
                bends = sheet.bends().sort_by(Axis.Y)
                bend_axis = bends[0 if outer else -1].axis_of_rotation
            thicken()

            with Locations((screw_inset, 0, thickness)):
                with GridLocations(0, screw_spacing, 1, 3):
                    CounterSinkHole(radius=3, counter_sink_radius=5)
                    CylindricalJoint("hole", linear_range=(0, 20))

            RigidJoint("mount", joint_location=Location((screw_inset, 0, 0)))

            if outer:
                RevoluteJoint(
                    "hinge", axis=bend_axis.reverse(), angular_range=(90, 360)
                )
            else:
                RigidJoint("hinge", joint_location=bend_axis.location)

        super().__init__(part=leaf.part, rotation=rotation, align=align, mode=mode)
        self.barrel_radius = pin_diameter / 2 + thickness
        self.screw_inset, self.screw_spacing = screw_inset, screw_spacing
        self.label = "outer leaf" if outer else "inner leaf"


box_leaf = HingeLeaf(leaf_width, leaf_length, leaf_thickness, pin_diameter)
lid_leaf = HingeLeaf(leaf_width, leaf_length, leaf_thickness, pin_diameter, outer=False)

print(list(box_leaf.joints))
# [leaf_joints]

assert all(same(old, new) for old, new in zip(bare_leaves, (box_leaf, lid_leaf)))
assert list(box_leaf.joints) == ["hole0", "hole1", "hole2", "mount", "hinge"]
assert list(lid_leaf.joints) == list(box_leaf.joints)
assert isinstance(box_leaf.joints["hinge"], RevoluteJoint)
assert isinstance(lid_leaf.joints["hinge"], RigidJoint)
render(
    [box_leaf],
    "leaf_joints",
    joints=list(box_leaf.joints.values()),
    viewpoint=(-60, -140, 130),
)

# ---------------------------------------------------------------------------
# Step 4: the box
# ---------------------------------------------------------------------------
# [box_builder]
with BuildPart() as box_builder:
    with BuildSketch() as footprint:
        Rectangle(box_depth, box_length)
    extrude(amount=box_height)
    offset(amount=-wall_thickness, openings=box_builder.faces().sort_by(Axis.Z)[-1])

    back = box_builder.faces().sort_by(Axis.X)[0]
    rim = back.edges().sort_by(Axis.Z)[-1]
    pin_height = lid_thickness + box_leaf.barrel_radius
    hinge_plane = Plane(
        origin=(rim @ 0.5) + (0, 0, pin_height - box_leaf.screw_inset),
        x_dir=(0, 0, -1),
        z_dir=(-1, 0, 0),
    )
    with Locations(hinge_plane):
        RigidJoint("hinge")
        with GridLocations(0, box_leaf.screw_spacing, 1, 3):
            Hole(pilot_radius, pilot_depth)
box = box_builder.part
# [box_builder]
builder_box = box

# [box_algebra]
box = extrude(Rectangle(box_depth, box_length), amount=box_height)
box = offset(box, amount=-wall_thickness, openings=box.faces().sort_by(Axis.Z)[-1])

back = box.faces().sort_by(Axis.X)[0]
rim = back.edges().sort_by(Axis.Z)[-1]
pin_height = lid_thickness + box_leaf.barrel_radius
hinge_plane = Plane(
    origin=(rim @ 0.5) + (0, 0, pin_height - box_leaf.screw_inset),
    x_dir=(0, 0, -1),
    z_dir=(-1, 0, 0),
)
box -= (
    hinge_plane
    * GridLocations(0, box_leaf.screw_spacing, 1, 3)
    * Hole(pilot_radius, pilot_depth)
)
box += hinge_plane * RigidJoint("hinge")
# [box_algebra]

assert same(builder_box, box)
assert builder_box.joints["hinge"].location == box.joints["hinge"].location
render([box], "box", joints=[box.joints["hinge"]])

# ---------------------------------------------------------------------------
# Step 5: the lid
# ---------------------------------------------------------------------------
# [lid_builder]
with BuildPart() as lid_builder:
    with BuildSketch() as footprint:
        Rectangle(box_depth, box_length)
    extrude(amount=lid_thickness)

    top = lid_builder.faces().sort_by(Axis.Z)[-1]
    back_edge = top.edges().sort_by(Axis.X)[0]
    hinge_plane = Plane(
        origin=(back_edge @ 0.5)
        + (lid_leaf.screw_inset - lid_leaf.barrel_radius, 0, 0),
        x_dir=(1, 0, 0),
        z_dir=(0, 0, 1),
    )
    with Locations(hinge_plane):
        RigidJoint("hinge")
        with GridLocations(0, lid_leaf.screw_spacing, 1, 3):
            Hole(pilot_radius, pilot_depth)
lid = lid_builder.part
# [lid_builder]
builder_lid = lid

# [lid_algebra]
lid = extrude(Rectangle(box_depth, box_length), amount=lid_thickness)

top = lid.faces().sort_by(Axis.Z)[-1]
back_edge = top.edges().sort_by(Axis.X)[0]
hinge_plane = Plane(
    origin=(back_edge @ 0.5) + (lid_leaf.screw_inset - lid_leaf.barrel_radius, 0, 0),
    x_dir=(1, 0, 0),
    z_dir=(0, 0, 1),
)
lid -= (
    hinge_plane
    * GridLocations(0, lid_leaf.screw_spacing, 1, 3)
    * Hole(pilot_radius, pilot_depth)
)
lid += hinge_plane * RigidJoint("hinge")
# [lid_algebra]

assert same(builder_lid, lid)
assert builder_lid.joints["hinge"].location == lid.joints["hinge"].location
render([lid], "lid", joints=[lid.joints["hinge"]])

# ---------------------------------------------------------------------------
# Step 6: a screw
# ---------------------------------------------------------------------------
# [screw]
screw = import_step("M6-1x12-countersunk-screw.step")
RigidJoint("head", screw, Location((0, 0, 0)))
# [screw]

if not (OUTPUT / "hinged_screw.svg").exists():  # thirty seconds, for the thread
    render([screw], "screw", joints=[screw.joints["head"]], viewpoint=(-60, -140, 80))

# ---------------------------------------------------------------------------
# Step 7: connect the joints
# ---------------------------------------------------------------------------
# [connect_box]
box.joints["hinge"].attach(box_leaf.joints["mount"])
# [connect_box]
render([box, box_leaf], "connect_box")

# [connect_leaves]
box_leaf.joints["hinge"].attach(lid_leaf.joints["hinge"], angle=90)
# [connect_leaves]
render([box, box_leaf, lid_leaf], "connect_leaves")

# [connect_lid]
lid_leaf.joints["mount"].attach(lid.joints["hinge"])
# [connect_lid]
render([box, box_leaf, lid_leaf, lid], "connect_lid")

# The lid has landed exactly on the box.
lid_box = lid.bounding_box()
assert abs(lid_box.min.Z - box_height) < 1e-6
assert (lid_box.center() - Vector(0, 0, box_height + lid_thickness / 2)).length < 1e-6

# ---------------------------------------------------------------------------
# Step 8: an assembly
# ---------------------------------------------------------------------------
# [assembly]
box.label, lid.label = "box", "lid"
hinged_box = Compound(label="hinged box", children=[box, box_leaf, lid_leaf, lid])

clash, clashing_parts, clash_volume = hinged_box.do_children_intersect()
print(f"Do any of the parts overlap? {clash}")
# [assembly]
assert clash is False

# ---------------------------------------------------------------------------
# Step 9: the screws
# ---------------------------------------------------------------------------
# [screws]
for leaf in (box_leaf, lid_leaf):
    for hole in ("hole0", "hole1", "hole2"):
        new_screw = copy.copy(screw)
        new_screw.label = f"{leaf.label} screw"
        leaf.joints[hole].attach(new_screw.joints["head"], position=0, angle=0)
        new_screw.parent = hinged_box

print(hinged_box.show_topology())
# [screws]
SCREWS += hinged_box.children[4:]
assert len(SCREWS) == 6
render(list(hinged_box.children), "finished")

# ---------------------------------------------------------------------------
# Step 10: open the lid
# ---------------------------------------------------------------------------
# [open]
box_leaf.joints["hinge"].attach(lid_leaf.joints["hinge"], angle=200)
lid_leaf.joints["mount"].attach(lid.joints["hinge"])
lid_screws = hinged_box.children[-3:]
for hole, lid_screw in zip(("hole0", "hole1", "hole2"), lid_screws):
    lid_leaf.joints[hole].attach(lid_screw.joints["head"], position=0, angle=0)
# [open]
render(list(hinged_box.children), "open")
clash, _, _ = Compound(
    children=[copy.copy(c) for c in hinged_box.children[:4]]
).do_children_intersect()
assert clash is False

# [limit]
try:
    box_leaf.joints["hinge"].attach(lid_leaf.joints["hinge"], angle=45)
except ValueError as error:
    print(error)
# [limit]
