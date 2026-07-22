"""
Sheet Metal Operations

name: operations_sheet.py
by:   Gabriel Jesus
date: July 21st 2026

desc:
    This python module contains the sheet metal operations.

license:

    Copyright 2026 Gabriel Jesus

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

from __future__ import annotations

from math import asin, atan, cos, degrees, radians, sin, sqrt, tan

from build123d.build_common import flatten_sequence, validate_inputs
from build123d.build_enums import BendPosition, GeomType, HemType, Mode, ReliefType
from build123d.build_sheet import BuildSheet
from build123d.geometry import Axis, Vector
from build123d.topology import (
    Compound,
    Edge,
    Face,
    Part,
    Shape,
    SkipClean,
    Solid,
    Wire,
    topo_explore_connected_faces,
)

THICKNESS_TOLERANCE = 1e-4


def _bend_frame(
    edge: Edge, target: Shape, thickness: float
) -> tuple[Vector, Vector, Vector, Vector, Vector]:
    """Derive the bend coordinate frame from a selected edge.

    The edge must lie at the junction of a sheet face (top/bottom surface)
    and a thickness face (material side wall).

    Returns:
        (p0, p1, thk_dir, f_dir, axis_dir) where p0/p1 are the edge end
        points ordered along axis_dir, thk_dir points from the edge into
        the material, f_dir is the outward direction the wall extends and
        axis_dir the bend axis direction (rotation by +angle folds away
        from the sheet face).
    """
    if edge.geom_type != GeomType.LINE:
        raise ValueError("flange/hem edges must be linear")
    adjacent = [Face(f) for f in topo_explore_connected_faces(edge, parent=target)]
    if len(adjacent) != 2:
        raise ValueError(
            f"Selected edge must have exactly 2 adjacent faces, found {len(adjacent)}"
        )

    def is_thickness_face(face: Face) -> bool:
        return (
            abs(min(e.length for e in face.edges()) - thickness)
            < THICKNESS_TOLERANCE * thickness
        )

    thickness_faces = [f for f in adjacent if is_thickness_face(f)]
    if len(thickness_faces) != 1:
        raise ValueError(
            "Selected edge must be at the junction of a sheet face and a "
            "thickness face (e.g. the edge of the top or bottom surface)"
        )
    thickness_face = thickness_faces[0]
    sheet_face = adjacent[0] if adjacent[1] is thickness_face else adjacent[1]

    f_dir = thickness_face.normal_at()
    normal = sheet_face.normal_at()
    thk_dir = -normal
    axis_dir = normal.cross(f_dir)

    p0, p1 = edge.position_at(0), edge.position_at(1)
    if (p1 - p0).dot(axis_dir) < 0:
        p0, p1 = p1, p0
    return p0, p1, thk_dir, f_dir, axis_dir


def _relief_cuts(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    orig0: Vector,
    orig1: Vector,
    axis_dir: Vector,
    f_dir: Vector,
    thk_dir: Vector,
    thickness: float,
    gap1: float,
    gap2: float,
    relief: ReliefType,
    relief_size: tuple[float, float],
    offset: float,
) -> list[Solid]:
    """Bend relief notches cut into the base sheet at each gapped end.

    Each notch is flush against the wall's side, spanning the last
    relief-width of the gap, cut through the sheet thickness (FreeCAD
    smMakeReliefFace placement). For inside bend positions an extra
    rectangular band of depth ``offset`` clears alongside the shifted
    wall (FreeCAD parity).
    """
    width, depth = relief_size
    cuts: list[Solid] = []
    for end, direction, gap in ((orig0, axis_dir, gap1), (orig1, -axis_dir, gap2)):
        if gap <= 0:
            continue
        inner = end + direction * gap  # flush with the wall's side
        outer = inner - direction * width  # toward the sheet corner
        root0, root1 = outer, inner
        if offset < 0:  # wall root shifted into the material
            root0 = outer + f_dir * offset
            root1 = inner + f_dir * offset
            band = Face(
                Wire.make_polygon([outer, inner, root1, root0], close=True)
            )
            cuts.append(Solid.extrude(band, thk_dir * thickness))
        if relief == ReliefType.RECTANGLE:
            notch = Face(
                Wire.make_polygon(
                    [root0, root1, root1 - f_dir * depth, root0 - f_dir * depth],
                    close=True,
                )
            )
        else:  # ReliefType.ROUND
            cap_radius = width / 2
            mid = (root0 + root1) * 0.5
            mouth = Edge.make_line(root0, root1)
            if depth <= cap_radius + 1e-9:
                cap = Edge.make_three_point_arc(
                    root1, mid - f_dir * depth, root0
                )
                notch = Face(Wire([mouth, cap]))
            else:
                shoulder0 = root0 - f_dir * (depth - cap_radius)
                shoulder1 = root1 - f_dir * (depth - cap_radius)
                notch = Face(
                    Wire(
                        [
                            mouth,
                            Edge.make_line(root1, shoulder1),
                            Edge.make_three_point_arc(
                                shoulder1, mid - f_dir * depth, shoulder0
                            ),
                            Edge.make_line(shoulder0, root0),
                        ]
                    )
                )
        cuts.append(Solid.extrude(notch, thk_dir * thickness))
    return cuts


def _make_bend(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    target: Shape,
    edge: Edge,
    thickness: float,
    radius: float,
    angle: float,
    leg_length: float,
    gap1: float = 0,
    gap2: float = 0,
    offset: float = 0,
    extend1: float = 0,
    extend2: float = 0,
    miter_angle1: float = 0,
    miter_angle2: float = 0,
    relief: ReliefType | None = None,
    relief_size: tuple[float, float] | None = None,
) -> tuple[list[Solid], list[Solid]]:
    """Build the solids of one bend: (additions, cuts).

    Translated from FreeCAD SheetMetal smBend: the bend is a thickness
    rectangle revolved about the bend axis; the wall is an extruded
    rectangle rotated to the bend end angle. offset < 0 shifts the whole
    bend into the material (BendPosition.MATERIAL_INSIDE /
    THICKNESS_OUTSIDE) and produces a cut slab.
    """
    p0, p1, thk_dir, f_dir, axis_dir = _bend_frame(edge, target, thickness)
    if gap1 + gap2 >= (p1 - p0).length:
        raise ValueError("gap1 + gap2 leave no bend width on the edge")
    orig0, orig1 = p0, p1
    p0 = p0 + axis_dir * gap1
    p1 = p1 - axis_dir * gap2

    cuts: list[Solid] = []
    if relief is not None:
        cuts.extend(
            _relief_cuts(
                orig0, orig1, axis_dir, f_dir, thk_dir, thickness,
                gap1, gap2, relief, relief_size, offset,
            )
        )
    if offset < 0:
        # shift the working edge into the material and cut the vacated slab
        slab_face = Face(
            Wire.make_polygon(
                [p0, p1, p1 + thk_dir * thickness, p0 + thk_dir * thickness],
                close=True,
            )
        )
        cuts.append(Solid.extrude(slab_face, f_dir * offset))
        p0 = p0 + f_dir * offset
        p1 = p1 + f_dir * offset

    additions: list[Solid] = []
    axis = Axis(p0 + thk_dir * (radius + thickness), axis_dir)

    sector_face = Face(
        Wire.make_polygon(
            [p0, p1, p1 + thk_dir * thickness, p0 + thk_dir * thickness], close=True
        )
    )
    additions.append(Solid.revolve(sector_face, angle, axis))

    if leg_length > 0:
        # extends widen the flat wall beyond the gap-trimmed ends; the bend
        # sector deliberately keeps the gapped width (FreeCAD smBend parity)
        q0 = p0 - axis_dir * extend1
        q1 = p1 + axis_dir * extend2
        # miter angles shift the far corners along the edge: positive cuts
        # inward, negative widens (FreeCAD smMakeFace angle semantics)
        far0 = q0 + f_dir * leg_length + axis_dir * (
            leg_length * tan(radians(miter_angle1))
        )
        far1 = q1 + f_dir * leg_length - axis_dir * (
            leg_length * tan(radians(miter_angle2))
        )
        if (far1 - far0).dot(axis_dir) <= 1e-9:
            raise ValueError("miter angles leave no wall at the tip")
        wall_face = Face(Wire.make_polygon([q0, q1, far1, far0], close=True))
        wall = Solid.extrude(wall_face, thk_dir * thickness)
        additions.append(wall.rotate(axis, angle))

    return additions, cuts


def _apply_bends(
    context: BuildSheet | None,
    target: Shape,
    additions: list[Solid],
    cuts: list[Solid],
    clean: bool,
    mode: Mode,
) -> Part:
    """Fuse bend solids with the target sheet, preserving bend faces."""
    if mode != Mode.ADD:
        raise ValueError("sheet metal operations only support Mode.ADD (POC)")
    with SkipClean():
        new_sheet = target
        if cuts:
            new_sheet = new_sheet.cut(*cuts)
        new_sheet = new_sheet.fuse(*additions)
    if clean:
        new_sheet = new_sheet.clean()
    if context is not None:
        context._add_to_context(new_sheet, mode=Mode.REPLACE)
    # Wrap Solid results in a Compound before creating Part
    if isinstance(new_sheet, Solid):
        new_sheet = Compound([new_sheet])
    return Part(new_sheet)


def flange(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    edges: Edge | list[Edge] | None = None,
    length: float = 0,
    angle: float = 90,
    radius: float | None = None,
    gap1: float = 0,
    gap2: float = 0,
    extend1: float = 0,
    extend2: float = 0,
    miter_angle1: float = 0,
    miter_angle2: float = 0,
    relief: ReliefType | None = None,
    relief_size: tuple[float, float] | None = None,
    bend_position: BendPosition = BendPosition.MATERIAL_OUTSIDE,
    clean: bool = False,
    mode: Mode = Mode.ADD,
    thickness: float | None = None,
) -> Part:
    """Sheet Metal Operation: flange

    Fold a wall (flange) up from each selected sheet edge with a
    cylindrical bend. The bend fold direction is away from the sheet face
    the edge was selected from. Bend faces are intentionally kept separate
    (not unified) — do not clean() the result.

    Args:
        edges (Edge|list[Edge]): straight edge(s) at the junction of a sheet
            face and a thickness face.
        length (float): flat wall length beyond the bend (leg).
        angle (float, optional): bend angle in degrees, 0 < angle <= 270.
            Defaults to 90.
        radius (float, optional): inner bend radius. Defaults to the
            BuildSheet context bend_radius.
        gap1/gap2 (float, optional): trim from each end of the edge.
        extend1/extend2 (float, optional): widen the flat wall beyond each
            end of the edge. Only the wall widens — the bend keeps the
            gapped width, so a wide leg can overhang the bend's sides.
        miter_angle1/miter_angle2 (float, optional): angled end-cut in
            degrees at each side of the wall's free end — positive cuts
            inward, negative widens the wall outward. The bend itself is
            never mitered.
        relief (ReliefType, optional): cut a bend relief notch into the
            base sheet at each gapped end of the wall. Defaults to None.
        relief_size (tuple[float, float], optional): (width, depth) of the
            notch. Defaults to 0.7 x thickness for both.
        bend_position (BendPosition, optional): where the material sits
            relative to the selected edge. Defaults to MATERIAL_OUTSIDE.
        clean (bool, optional): unify faces — destroys bend topology, only
            for parts that will never be unfolded. Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
            Only Mode.ADD is supported (POC limitation).
        thickness (float, optional): sheet thickness — required in algebra
            mode, taken from the context otherwise.

    Raises:
        ValueError: bad edge selection, or invalid gap/radius/angle
            parameters, including a degenerate extend/miter combination
            that leaves no wall at the tip, or a relief/relief_size
            combination (missing gap, non-positive size, or width
            exceeding the gap).
    """
    context: BuildSheet | None = BuildSheet._get_context("flange")
    edge_list = flatten_sequence(edges)
    validate_inputs(context, "flange", edge_list)

    if not edge_list:
        raise ValueError("flange requires at least one edge")
    if length <= 0:
        raise ValueError("length must be positive")
    if not 0 < angle <= 270:
        raise ValueError("angle must be in (0, 270] degrees")

    if thickness is None:
        if context is None:
            raise ValueError("thickness must be provided in algebra mode")
        thickness = context.thickness
    if radius is None:
        radius = context.bend_radius if context is not None else thickness
    if radius < 0:
        raise ValueError("radius can't be negative")
    if gap1 < 0 or gap2 < 0:
        raise ValueError("gaps can't be negative")
    if extend1 < 0 or extend2 < 0:
        raise ValueError("extends can't be negative")
    if abs(miter_angle1) >= 90 or abs(miter_angle2) >= 90:
        raise ValueError("miter angles must be within (-90, 90) degrees")
    if relief_size is not None and relief is None:
        raise ValueError("relief_size requires relief")
    if relief is not None:
        if gap1 <= 0 and gap2 <= 0:
            raise ValueError("relief requires gap1 or gap2 > 0")
        if relief_size is None:
            relief_size = (0.7 * thickness, 0.7 * thickness)
        if relief_size[0] <= 0 or relief_size[1] <= 0:
            raise ValueError("relief_size values must be positive")
        for gap in (gap1, gap2):
            if 0 < gap < relief_size[0]:
                raise ValueError("relief width must not exceed the gap")

    if context is not None and context.sheet is not None:
        target = context.sheet
    else:
        target = edge_list[0].topo_parent  # pylint: disable=no-member
        if target is None:
            raise ValueError("edges must belong to a sheet solid")

    if bend_position == BendPosition.MATERIAL_INSIDE:
        offset = -(thickness + radius)
    elif bend_position == BendPosition.THICKNESS_OUTSIDE:
        offset = -radius
    else:
        offset = 0.0

    additions: list[Solid] = []
    cuts: list[Solid] = []
    for edge in edge_list:
        adds, cut_solids = _make_bend(
            target, edge, thickness, radius, angle, length, gap1, gap2, offset,
            extend1, extend2, miter_angle1, miter_angle2,
            relief, relief_size,
        )
        additions.extend(adds)
        cuts.extend(cut_solids)

    return _apply_bends(context, target, additions, cuts, clean, mode)


def _bisection(func, lower: float, upper: float, eps: float = 1.0e-9) -> float:
    """Root of func in [lower, upper] — from FreeCAD SheetMetalHem.py"""
    f_lower, f_upper = func(lower), func(upper)
    if f_lower * f_upper > 0:
        raise ValueError("Teardrop hem has unexpected incorrect geometry")
    mid = 0.5 * (lower + upper)
    prev_mid = mid + 2 * eps
    while abs(mid - prev_mid) >= eps:
        prev_mid = mid
        f_mid = func(mid)
        if f_lower * f_mid < 0:
            upper = mid
        else:
            lower, f_lower = mid, f_mid
        mid = 0.5 * (lower + upper)
    return mid


def _hem_parameters(  # pylint: disable=too-many-return-statements
    hem_type: HemType,
    thickness: float,
    width: float | None,
    opening: float,
    radius: float | None,
    roll_angle: float | None,
) -> tuple[float, float, float]:
    """Return (leg_length, bend_angle, bend_radius) for a hem.

    Pure-math translation of FreeCAD SheetMetalHem.py generateOpenHem /
    generateRolledHem / generateTeardropHem (width always includes the bend).
    """
    if hem_type in (HemType.FLAT, HemType.OPEN):
        if opening < 0:
            raise ValueError("opening must be positive")
        if width is None:
            raise ValueError(f"width is required for {hem_type}")
        bend_radius = 0.5 * opening
        if width <= bend_radius + thickness:
            raise ValueError(
                "width must be greater than the bend width "
                "(bend radius + thickness)"
            )
        return width - (bend_radius + thickness), 180.0, bend_radius

    if hem_type == HemType.ROLLED:
        if radius is None or radius <= 0:
            raise ValueError("a positive radius is required for a rolled hem")
        max_roll_angle = 270.0 + degrees(asin(radius / (radius + thickness)))
        if roll_angle is None:
            return 0.0, max_roll_angle, radius
        if roll_angle <= 0:
            raise ValueError("roll_angle must be strictly positive")
        if roll_angle > max_roll_angle:
            raise ValueError(
                f"roll_angle must not exceed physical maximum ({max_roll_angle}°)"
            )
        return 0.0, roll_angle, radius

    if hem_type == HemType.TEARDROP:
        if radius is None or radius <= 0:
            raise ValueError("a positive radius is required for a teardrop hem")
        if opening < 0:
            raise ValueError("opening must be positive")
        if width is None:
            raise ValueError("width is required for a teardrop hem")
        bend_width = radius + thickness
        if width < 2 * bend_width:
            raise ValueError(
                "width must be greater or equal than twice the bend width "
                "(bend radius + thickness)"
            )
        if width == 2 * bend_width:  # degenerate teardrop
            if opening >= radius:
                raise ValueError("opening must be smaller than bend radius")
            return radius - opening, 270.0, radius
        def equation(leg: float) -> float:
            return leg - width + bend_width + thickness * sin(2 * atan(radius / leg))
        leg = _bisection(equation, width - bend_width - thickness, width - bend_width)
        if opening == 0.0:
            theta = atan(radius / leg)
            return leg, 180.0 + 2 * degrees(theta), radius
        if opening == 2 * radius:
            return _hem_parameters(HemType.OPEN, thickness, width - bend_width, opening, None, None)
        theta = atan(
            (leg - sqrt(leg**2 - 2.0 * radius * opening + opening**2)) / opening
        )
        leg_length = opening * (cos(2 * theta) - 1) / sin(2 * theta) + leg
        return leg_length, 180.0 + 2 * degrees(theta), radius

    raise ValueError(f"Unknown hem type {hem_type}")


def hem(
    edges: Edge | list[Edge] | None = None,
    hem_type: HemType = HemType.FLAT,
    width: float | None = None,
    opening: float = 0,
    radius: float | None = None,
    roll_angle: float | None = None,
    clean: bool = False,
    mode: Mode = Mode.ADD,
    thickness: float | None = None,
) -> Part:
    """Sheet Metal Operation: hem

    Fold the sheet edge back onto itself. A hem is a bend with an angle of
    180° or more; the hem type determines the fold parameters:

    - HemType.FLAT: fold flat onto the sheet (radius 0).
    - HemType.OPEN: 180° fold leaving a gap of ``opening``.
    - HemType.TEARDROP: teardrop-profile fold of ``radius``.
    - HemType.ROLLED: open curl of ``radius`` and ``roll_angle`` (defaults
      to the physical maximum), no flat leg.

    Args:
        edges (Edge|list[Edge]): straight sheet edge(s) to hem.
        hem_type (HemType, optional): style of hem. Defaults to HemType.FLAT.
        width (float, optional): total hem width including the bend —
            required for FLAT/OPEN/TEARDROP.
        opening (float, optional): gap of an OPEN/TEARDROP hem. Defaults to 0.
        radius (float, optional): bend radius for TEARDROP/ROLLED. Defaults
            to the BuildSheet context bend_radius.
        roll_angle (float, optional): ROLLED sweep angle in degrees.
        clean (bool, optional): unify faces — destroys bend topology.
            Defaults to False.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
            Only Mode.ADD is supported (POC limitation).
        thickness (float, optional): sheet thickness — required in algebra
            mode, taken from the context otherwise.

    Raises:
        ValueError: bad edge selection or hem parameters.
    """
    context: BuildSheet | None = BuildSheet._get_context("hem")
    edge_list = flatten_sequence(edges)
    validate_inputs(context, "hem", edge_list)

    if not edge_list:
        raise ValueError("hem requires at least one edge")
    if thickness is None:
        if context is None:
            raise ValueError("thickness must be provided in algebra mode")
        thickness = context.thickness
    if radius is None:
        radius = context.bend_radius if context is not None else None

    leg_length, bend_angle, bend_radius = _hem_parameters(
        hem_type, thickness, width, opening, radius, roll_angle
    )

    if context is not None and context.sheet is not None:
        target = context.sheet
    else:
        target = edge_list[0].topo_parent  # pylint: disable=no-member
        if target is None:
            raise ValueError("edges must belong to a sheet solid")

    additions: list[Solid] = []
    for edge in edge_list:
        adds, _ = _make_bend(
            target, edge, thickness, bend_radius, bend_angle, leg_length
        )
        additions.extend(adds)

    return _apply_bends(context, target, additions, [], clean, mode)
