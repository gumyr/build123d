from build123d import *

thickness = 2
height = 40
width = 65
length = 100
diam = 4
tol = 0.05


#
# Base and top
#


class Base(Part):
    hinge_x1, hinge_x2 = 0.63, 0.87

    hinges_holes = {
        "right_front": Location((-hinge_x1 * width, -hinge_x1 * length), (0, 0, 195)),
        "right_middle": Location((-hinge_x2 * width, 0), (0, 0, 180)),
        "right_back": Location((-hinge_x1 * width, hinge_x1 * length), (0, 0, 165)),
        "left_front": Location((hinge_x1 * width, -hinge_x1 * length), (0, 0, -15)),
        "left_middle": Location((hinge_x2 * width, 0), (0, 0, 0)),
        "left_back": Location((hinge_x1 * width, hinge_x1 * length), (0, 0, 15)),
    }

    stand_holes = {
        "front_stand": Location((0, -0.8 * length), (0, 0, 180)),
        "back_stand": Location((0, 0.75 * length), (0, 0, 0)),
    }

    def __init__(self, label):
        base = extrude(Ellipse(width, length), thickness)
        base -= Pos(Y=-length + 5) * Box(2 * width, 20, 3 * thickness)

        for pos in self.hinges_holes.values():
            base -= pos * Cylinder(
                diam / 2 + tol,
                thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        for pos in self.stand_holes.values():
            base -= pos * Box(width / 2 + 2 * tol, thickness + 2 * tol, 5 * thickness)

        super().__init__(base.wrapped, label=label)

        # Add joints

        for name, edge in self.hinges_holes.items():
            RigidJoint(f"j_{name}", self, edge)

        for name, pos in self.stand_holes.items():
            RigidJoint(f"j_{name}", self, pos * Rot(0, 0, 90))

        center = self.faces().sort_by().last.center_location
        RigidJoint("j_top", self, center * Pos(Z=height + thickness + 2 * tol))
        RigidJoint("j_bottom", self, center)


#
# Stands
#


class Stand(Part):
    def __init__(self, label):
        self.h = 5

        stand = Box(width / 2 + 10, height + 2 * tol, thickness)
        faces = stand.faces().sort_by(Axis.Y)

        t2 = thickness / 2
        w = height / 2 + tol - self.h / 2
        for i in [-1, 1]:
            rect = Pos(0, i * w, t2) * Rectangle(thickness, self.h)
            block = extrude(rect, self.h)

            m = block.edges().group_by()[-1]
            block = chamfer(
                m.sort_by(Axis.Y).first if i == 1 else m.sort_by(Axis.Y).last,
                length=self.h - 2 * tol,
            )

            stand += block

        for plane in [Plane(faces.first), Plane(faces.last)]:
            stand += plane * Box(
                thickness,
                width / 2,
                thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        super().__init__(stand.wrapped, label=label)

        RigidJoint(
            "j_bottom",
            self,
            self.faces().sort_by(Axis.Y).last.center_location * Rot(0, 180, 0),
        )


#
# Legs
#


class UpperLeg(Part):
    def __init__(self, label):
        self.l1 = 50
        self.l2 = 80

        leg_hole = Location((self.l2 - 10, 0), (0, 0, 0))

        line = Polyline(
            (0, 0), (0, height / 2), (self.l1, height / 2 - 5), (self.l2, 0)
        )
        line += mirror(line, about=Plane.XZ)
        face = make_face(line)
        upper_leg = extrude(face, thickness, dir=(0, 0, 1))
        upper_leg = fillet(upper_leg.edges().group_by(Axis.X)[-1], radius=4)

        last = upper_leg.edges()
        upper_leg -= leg_hole * Hole(diam / 2 + tol, depth=thickness)
        self.knee_hole = upper_leg.edges().filter_by(GeomType.CIRCLE) - last

        upper_leg += (
            Pos(0, 0, thickness / 2)
            * Rot(90, 0, 0)
            * Cylinder(diam / 2, 2 * (height / 2 + thickness + tol))
        )

        super().__init__(upper_leg.wrapped, label=label)

        RevoluteJoint(
            "j_hinge",
            self,
            axis=-upper_leg.faces().sort_by(Axis.Y).last.center_location.z_axis,
            angular_range=(0, 180),
        )
        RigidJoint(
            "j_knee_front",
            self,
            leg_hole * Rot(180, 0, 0),
        )
        RigidJoint("j_knee_back", self, leg_hole * Pos(0, 0, thickness))


class LowerLeg(Part):
    def __init__(self, label):
        self.w = 15
        self.l1 = 20
        self.l2 = 120

        leg_hole = Location((self.l1 - 10, 0), (0, 0, 0))

        line = Polyline((0, 0), (self.l1, self.w), (self.l2, 0))
        line += mirror(line, about=Plane.XZ)
        face = make_face(line)
        lower_leg = extrude(face, thickness, dir=(0, 0, 1))
        lower_leg = fillet(lower_leg.edges().filter_by(Axis.Z), radius=4)

        lower_leg -= leg_hole * Hole(diam / 2 + tol, depth=thickness)

        super().__init__(lower_leg.wrapped, label=label)

        RevoluteJoint(
            "j_front",
            self,
            axis=(leg_hole * Pos(0, 0, thickness) * Rot(0, 180, 0)).z_axis,
            angular_range=(-180, 180),
        )
        RevoluteJoint(
            "j_back",
            self,
            axis=(leg_hole * Pos(0, 0, 0)).z_axis,
            angular_range=(-180, 180),
        )
