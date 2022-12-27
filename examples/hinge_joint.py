"""

name: hinge_joint.py
by:   Gumyr
date: December 27h 2022

desc:

    This example a box with a lid attached with a hinge.

license:

    Copyright 2022 Gumyr

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
from build123d import *


class Hinge(Compound):
    """Hinge

    Half a simple hinge with several joints. The joints are:
    - "plate": RigidJoint where hinge screws to object
    - "hinge_axis": RigidJoint (inner) or RevoluteJoint (outer)
    - "hole0", "hole1", "hole2": CylindricalJoints for attachment screws

    Args:
        width (float): width of one leaf
        length (float): hinge length
        barrel_diameter (float): size of hinge pin barrel
        thickness (float): hinge plate thickness
        pin_diameter (float): hinge pin diameter
        inner (bool, optional): inner or outer half of hinge . Defaults to True.
    """

    def __init__(
        self,
        width: float,
        length: float,
        barrel_diameter: float,
        thickness: float,
        pin_diameter: float,
        inner: bool = True,
    ):

        # The profile of the hinge used to create the tabs
        with BuildPart() as hinge_profile:
            with BuildSketch():
                for i, loc in enumerate(
                    GridLocations(0, length / 5, 1, 5, centered=(False, False))
                ):
                    if i % 2 == inner:
                        with Locations(loc):
                            Rectangle(width, length / 5, centered=(False, False))
                Rectangle(
                    width - barrel_diameter,
                    length,
                    centered=(False, False),
                )
            Extrude(amount=-barrel_diameter)

        # The hinge pin
        with BuildPart() as pin:
            Cylinder(
                radius=pin_diameter / 2, height=length, centered=(True, True, False)
            )
            with BuildPart(pin.part.faces().sort_by(Axis.Z)[-1]) as pin_head:
                Cylinder(
                    radius=barrel_diameter / 2,
                    height=pin_diameter,
                    centered=(True, True, False),
                )
                Fillet(
                    *pin_head.edges(Select.LAST).filter_by(GeomType.CIRCLE),
                    radius=pin_diameter / 3,
                )

        # Both the external and internal hinge with joints
        with BuildPart() as hinge:
            with BuildSketch():
                with BuildLine():
                    l1 = Line((0, 0), (width - barrel_diameter / 2, 0))
                    l2 = RadiusArc(
                        l1 @ 1,
                        l1 @ 1 + Vector(0, barrel_diameter),
                        -barrel_diameter / 2,
                    )
                    l3 = RadiusArc(
                        l2 @ 1,
                        (
                            width - barrel_diameter,
                            barrel_diameter / 2,
                        ),
                        -barrel_diameter / 2,
                    )
                    l4 = Line(l3 @ 1, (width - barrel_diameter, thickness))
                    l5 = Line(l4 @ 1, (0, thickness))
                    Line(l5 @ 1, l1 @ 0)
                MakeFace()
                with Locations(
                    (width - barrel_diameter / 2, barrel_diameter / 2)
                ) as pin_center:
                    Circle(pin_diameter / 2 + 0.1 * MM, mode=Mode.SUBTRACT)
            Extrude(amount=length)
            Add(hinge_profile.part, rotation=(90, 0, 0), mode=Mode.INTERSECT)

            # Create holes for fasteners
            with Workplanes(hinge.part.faces().filter_by(Axis.Y)[-1]):
                with GridLocations(0, length / 3, 1, 3):
                    holes = CounterSinkHole(3 * MM, 5 * MM)
            # Add the hinge pin to the external hinge
            if not inner:
                with Locations(pin_center.locations[0]):
                    Add(pin.part)
            #
            # Create the Joints
            #
            # Plate attachment
            RigidJoint(
                "plate",
                hinge.part,
                Location((width - barrel_diameter, 0, length / 2), (90, 0, 0)),
            )
            # Hinge axis (fixed with inner)
            if inner:
                RigidJoint(
                    "hinge_axis",
                    hinge.part,
                    Location((width - barrel_diameter / 2, barrel_diameter / 2, 0)),
                )
            else:
                RevoluteJoint(
                    "hinge_axis",
                    hinge.part,
                    axis=Axis(
                        (width - barrel_diameter / 2, barrel_diameter / 2, 0), (0, 0, 1)
                    ),
                    range=(90, 270),
                )
            # Fastener holes
            hole_locations = [hole.location for hole in holes]
            for hole, hole_location in enumerate(hole_locations):
                CylindricalJoint(
                    "hole" + str(hole),
                    hinge.part,
                    hole_location.to_axis(),
                    linear_range=(0, 2 * CM),
                    rotational_range=(0, 360),
                )

        super().__init__(hinge.part.wrapped, joints=hinge.part.joints)


# Create instances of the two halves of the hinge
hinge_inner = Hinge(
    width=5 * CM,
    length=12 * CM,
    barrel_diameter=1 * CM,
    thickness=2 * MM,
    pin_diameter=4 * MM,
)
hinge_outer = Hinge(
    width=5 * CM,
    length=12 * CM,
    barrel_diameter=1 * CM,
    thickness=2 * MM,
    pin_diameter=4 * MM,
    inner=False,
)

# Create the box with a RigidJoint to mount the hinge
with BuildPart() as box_builder:
    Box(30 * CM, 30 * CM, 10 * CM)
    Offset(amount=-1 * CM, openings=box_builder.faces().sort_by(Axis.Z)[-1])
    # Create a notch for the hinge
    with Locations((-15 * CM, 0, 5 * CM)):
        Box(2 * CM, 12 * CM, 4 * MM, mode=Mode.SUBTRACT)
    with Workplanes(
        box_builder.part.faces().sort_by(Axis.X)[0].located(Location((0, 0, 2 * CM)))
    ):
        with GridLocations(0, 40 * MM, 1, 3):
            Hole(3 * MM, 1 * CM)
    RigidJoint(
        "hinge_attachment",
        box_builder.part,
        Location((-15 * CM, 0, 4 * CM), (180, 90, 0)),
    )
# Demonstrate that objects with Joints can be moved and the joints follow
box = box_builder.part.moved(Location((0, 0, 5 * CM)))

# The lid with a RigidJoint for the hinge
with BuildPart() as lid_builder:
    Box(30 * CM, 30 * CM, 1 * CM)
    with Workplanes(
        lid_builder.part.faces().sort_by(Axis.Z)[-1].located(Location((-13 * CM, 0, 0)))
    ):
        with GridLocations(0, 40 * MM, 1, 3):
            Hole(3 * MM, 1 * CM)
    RigidJoint(
        "hinge_attachment",
        lid_builder.part,
        Location((-15 * CM, 0, 5 * MM), (180, 0, 180)),
    )
lid = lid_builder.part

# A screw to attach the hinge to the box
m6_screw = Compound.import_step("M6-1x12-countersunk-screw.step")
RigidJoint("head", m6_screw, Location((0, 0, 0), (1, 0, 0), 180))

# Connect the parts together
box.joints["hinge_attachment"].connect_to(hinge_outer.joints["plate"])
hinge_outer.joints["hinge_axis"].connect_to(hinge_inner.joints["hinge_axis"], angle=120)
hinge_inner.joints["plate"].connect_to(lid.joints["hinge_attachment"])
hinge_outer.joints["hole2"].connect_to(m6_screw.joints["head"], position=5, angle=30)

if "show_object" in locals():
    show_object(box, name="box", options={"alpha": 0.8})
    # show_object(box.joints["hinge_attachment"].symbol, name="box attachment point")
    show_object(hinge_outer, name="hinge_outer")
    # show_object(hinge_outer.joints["plate"].symbol, name="hinge_outer plate joint")
    # show_object(hinge_outer.joints["hinge_axis"].symbol, name="hinge_outer hinge axis")
    show_object(lid, name="lid")
    # show_object(lid.joints["hinge_attachment"].symbol, name="lid attachment point")
    show_object(hinge_inner, name="hinge_inner")
    # show_object(hinge_inner.joints["plate"].symbol, name="hinge_inner plate joint")
    # show_object(hinge_inner.joints["hinge_axis"].symbol, name="hinge_inner hinge axis")
    # for hole in [0, 1, 2]:
    #     show_object(
    #         hinge_inner.joints["hole" + str(hole)].symbol,
    #         name="hinge_inner hole " + str(hole),
    #     )
    #     show_object(
    #         hinge_outer.joints["hole" + str(hole)].symbol,
    #         name="hinge_outer hole " + str(hole),
    #     )
    show_object(m6_screw, name="m6 screw")
    # show_object(m6_screw.joints["head"].symbol, name="m6 screw symbol")
