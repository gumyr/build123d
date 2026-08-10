import pytest
from collections import Counter
from dataclasses import dataclass
from build123d import *
from build123d.topology.shape_core import Shape

INTERSECT_DEBUG = False
if INTERSECT_DEBUG:
    from ocp_vscode import show


@dataclass
class Case:
    object: Shape | Vector | Location | Axis | Plane
    target: Shape | Vector | Location | Axis | Plane
    expected: list | Vector | Location | Axis | Plane
    name: str
    xfail: None | str = None
    include_touched: bool = False


@pytest.mark.skip
def run_test(obj, target, expected, include_touched=False):
    # Only Shape objects support include_touched parameter
    kwargs = {}
    if include_touched and isinstance(obj, Shape):
        kwargs["include_touched"] = include_touched
    if isinstance(target, list):
        result = obj.intersect(*target, **kwargs)
    else:
        result = obj.intersect(target, **kwargs)
    if INTERSECT_DEBUG:
        show([obj, target, result])
    if expected is None:
        assert result == expected, f"Expected None, but got {result}"
    else:
        e_type = ShapeList if isinstance(expected, list) else expected
        assert isinstance(result, e_type), f"Expected {e_type}, but got {result}"
        if e_type == ShapeList:
            assert len(result) == len(
                expected
            ), f"Expected {len(expected)} objects, but got {len(result)}"

            actual_counts = Counter(type(obj) for obj in result)
            expected_counts = Counter(expected)
            assert all(
                actual_counts[t] >= count for t, count in expected_counts.items()
            ), f"Expected {expected}, but got {[type(r) for r in result]}"


@pytest.mark.skip
def make_params(matrix):
    params = []
    for case in matrix:
        obj_type = type(case.object).__name__
        tar_type = type(case.target).__name__
        i = len(params)
        if case.xfail and not INTERSECT_DEBUG:
            marks = [pytest.mark.xfail(reason=case.xfail)]
        else:
            marks = []
        # Add include_touched info to test id if specified
        touched_suffix = ", touched" if case.include_touched else ""
        uid = f"{i} {obj_type}, {tar_type}, {case.name}{touched_suffix}"
        params.append(
            pytest.param(
                case.object,
                case.target,
                case.expected,
                case.include_touched,
                marks=marks,
                id=uid,
            )
        )
        # Swap obj and target to test symmetry, but NOT for include_touched tests
        # (swapping may change behavior with boundary contacts)
        if (
            tar_type != obj_type
            and not isinstance(case.target, list)
            and not case.include_touched
        ):
            uid = f"{i + 1} {tar_type}, {obj_type}, {case.name}{touched_suffix}"
            params.append(
                pytest.param(
                    case.target,
                    case.object,
                    case.expected,
                    case.include_touched,
                    marks=marks,
                    id=uid,
                )
            )

    return params


# Geometric test objects
ax1 = Axis.X
ax2 = Axis.Y
ax3 = Axis((0, 0, 5), (1, 0, 0))
pl1 = Plane.YZ
pl2 = Plane.XY
pl3 = Plane.XY.offset(5)
pl4 = Plane((0, 5, 0))
pl5 = Plane.YZ.offset(1)
vl1 = Vector(2, 0, 0)
vl2 = Vector(2, 0, 5)
lc1 = Location((2, 0, 0))
lc2 = Location((2, 0, 5))
lc3 = Location((0, 0, 0), (0, 90, 90))
lc4 = Location((2, 0, 0), (0, 90, 90))

# Geometric test matrix
geometry_matrix = [
    Case(ax1, ax3, None, "parallel/skew", None),
    Case(ax1, ax1, Axis, "collinear", None),
    Case(ax1, ax2, Vector, "intersecting", None),
    Case(ax1, pl3, None, "parallel", None),
    Case(ax1, pl2, Axis, "coplanar", None),
    Case(ax1, pl1, Vector, "intersecting", None),
    Case(ax1, vl2, None, "non-coincident", None),
    Case(ax1, vl1, Vector, "coincident", None),
    Case(ax1, lc2, None, "non-coincident", None),
    Case(ax1, lc4, Location, "intersecting, co-z", None),
    Case(ax1, lc1, Vector, "intersecting", None),
    Case(pl2, pl3, None, "parallel", None),
    Case(pl2, pl4, Plane, "coplanar", None),
    Case(pl1, pl2, Axis, "intersecting", None),
    Case(pl3, ax1, None, "parallel", None),
    Case(pl2, ax1, Axis, "coplanar", None),
    Case(pl1, ax1, Vector, "intersecting", None),
    Case(pl1, vl2, None, "non-coincident", None),
    Case(pl2, vl1, Vector, "coincident", None),
    Case(pl1, lc2, None, "non-coincident", None),
    Case(pl1, lc3, Location, "intersecting, co-z", None),
    Case(pl2, lc4, Vector, "coincident", None),
    Case(vl1, vl2, None, "non-coincident", None),
    Case(vl1, vl1, Vector, "coincident", None),
    Case(vl1, lc2, None, "non-coincident", None),
    Case(vl1, lc1, Vector, "coincident", None),
    Case(lc1, lc2, None, "non-coincident", None),
    Case(lc1, lc4, Vector, "coincident", None),
    Case(lc1, lc1, Location, "coincident, co-z", None),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(geometry_matrix)
)
def test_geometry(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# Shape test matrices
vt1 = Vertex(2, 0, 0)
vt2 = Vertex(2, 0, 5)

shape_0d_matrix = [
    Case(vt1, vt2, None, "non-coincident", None),
    Case(vt1, vt1, [Vertex], "coincident", None),
    Case(vt1, vl2, None, "non-coincident", None),
    Case(vt1, vl1, [Vertex], "coincident", None),
    Case(vt1, lc2, None, "non-coincident", None),
    Case(vt1, lc1, [Vertex], "coincident", None),
    Case(vt2, ax1, None, "non-coincident", None),
    Case(vt1, ax1, [Vertex], "coincident", None),
    Case(vt2, pl1, None, "non-coincident", None),
    Case(vt1, pl2, [Vertex], "coincident", None),
    Case(vt1, [vt2, lc1], None, "multi to_intersect, non-coincident", None),
    Case(vt1, [vt1, lc1], [Vertex], "multi to_intersect, coincident", None),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(shape_0d_matrix)
)
def test_shape_0d(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# 1d Shapes
ed1 = Line((0, 0), (5, 0)).edge()
ed2 = Line((0, -1), (5, 1)).edge()
ed3 = Line((0, 0, 5), (5, 0, 5)).edge()
ed4 = CenterArc((3, 1), 2, 0, 360).edge()
ed5 = CenterArc((3, 1), 5, 0, 360).edge()

ed6 = Edge.make_line((0, -1), (2, 1))
ed7 = Edge.make_line((0, 1), (2, -1))
ed8 = Edge.make_line((0, 0), (2, 0))

wi1 = Wire() + [Line((0, 0), (1, 0)), RadiusArc((1, 0), (3, 1.5), 2)]
wi2 = wi1 + Line((3, 1.5), (3, -1))
wi3 = Wire() + [
    Line((0, 0), (1, 0)),
    RadiusArc((1, 0), (3, 0), 2),
    Line((3, 0), (5, 0)),
]
wi4 = Wire() + [Line((0, 1), (2, -1)), Line((2, -1), (3, -1))]
wi5 = wi4 + Line((3, -1), (4, 1))
wi6 = Wire() + [Line((0, 1, 1), (2, -1, 1)), Line((2, -1, 1), (4, 1, 1))]

shape_1d_matrix = [
    Case(ed1, vl2, None, "non-coincident", None),
    Case(ed1, vl1, [Vertex], "coincident", None),
    Case(ed1, lc2, None, "non-coincident", None),
    Case(ed1, lc1, [Vertex], "coincident", None),
    Case(ed3, ax1, None, "parallel/skew", None),
    Case(ed2, ax1, [Vertex], "intersecting", None),
    Case(ed1, ax1, [Edge], "collinear", None),
    Case(ed4, ax1, [Vertex, Vertex], "multi intersect", None),
    Case(ed1, pl3, None, "parallel/skew", None),
    Case(ed1, pl1, [Vertex], "intersecting", None),
    Case(ed1, pl2, [Edge], "collinear", None),
    Case(ed5, pl1, [Vertex, Vertex], "multi intersect", None),
    Case(ed1, vt2, None, "non-coincident", None),
    Case(ed1, vt1, [Vertex], "coincident", None),
    Case(ed3, ed1, None, "parallel/skew", None),
    Case(ed2, ed1, [Vertex], "intersecting", None),
    Case(ed1, ed1, [Edge], "collinear", None),
    Case(ed4, ed1, [Vertex, Vertex], "multi intersect", None),
    Case(ed6, [ed7, ed8], [Vertex], "multi to_intersect, intersect", None),
    Case(ed6, [ed7, pl5], [Vertex], "multi to_intersect, intersect", None),
    Case(ed6, [ed7, Vector(1, 0)], [Vertex], "multi to_intersect, intersect", None),
    Case(wi6, ax1, None, "parallel/skew", None),
    Case(wi4, ax1, [Vertex], "intersecting", None),
    Case(wi1, ax1, [Edge], "collinear", None),
    Case(wi5, ax1, [Vertex, Vertex], "multi intersect", None),
    Case(wi2, ax1, [Vertex, Edge], "intersect + collinear", None),
    Case(wi3, ax1, [Edge, Edge], "2 collinear", None),
    Case(wi6, ed1, None, "parallel/skew", None),
    Case(wi4, ed1, [Vertex], "intersecting", None),
    Case(wi1, ed1, [Edge], "collinear", None),
    Case(wi5, ed1, [Vertex, Vertex], "multi intersect", None),
    Case(wi2, ed1, [Vertex, Edge], "intersect + collinear", None),
    Case(wi3, ed1, [Edge, Edge], "2 collinear", None),
    Case(
        wi5, [ed1, Vector(1, 0)], [Vertex], "multi to_intersect, multi intersect", None
    ),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(shape_1d_matrix)
)
def test_shape_1d(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# 2d Shapes
fc1 = Rectangle(5, 5).face()
fc2 = Pos(Z=5) * Rectangle(5, 5).face()
fc3 = Rot(Y=90) * Rectangle(5, 5).face()
fc4 = Rot(Z=45) * Rectangle(5, 5).face()
fc5 = Pos(2.5, 2.5, 2.5) * Rot(0, 90) * Rectangle(5, 5).face()
fc6 = Pos(2.5, 2.5) * Rot(0, 90, 45, Extrinsic.XYZ) * Rectangle(5, 5).face()
fc7 = (Rot(90) * Cylinder(2, 4)).faces().filter_by(GeomType.CYLINDER)[0]
fc8 = make_face(
    Polyline(
        (-1.5, 1, 1),
        (-1.5, -1, 1),
        (3.5, -1, -1),
        (3.5, 1, -1),
        (-1.5, 1, 1),
    )
)
fc9 = Pos(-2) * mirror(fc8, Plane.XY)

fc11 = Rectangle(4, 4).face()
fc22 = sweep(Rot(90) * CenterArc((0, 0), 2, 0, 180), Line((0, 2), (0, -2)))
sh1 = Shell([Pos(-4) * fc11, fc22])
sh2 = Pos(Z=1) * sh1
sh3 = Shell([Pos(-4) * fc11, fc22, Pos(2, 0, -2) * Rot(0, 90) * fc11])
sh4 = Shell([Pos(-4) * fc11, fc22, Pos(4) * fc11])
sh5 = Pos(Z=1) * Shell(
    [Pos(-2, 0, -2) * Rot(0, -90) * fc11, fc22, Pos(2, 0, -2) * Rot(0, 90) * fc11]
)
sh6 = Box(2, 2, 2).shell()

# Shell tangent touch test objects (half spheres)
_half_sphere_solid = Sphere(1) & Pos(0, 0, 0.5) * Box(3, 3, 2)
sh7 = Shell(_half_sphere_solid.faces())
sh8 = Pos(2, 0, 0) * sh7  # tangent at (1, 0, 0)
fc10 = Pos(1, 0, 0) * (
    Rot(0, 90, 0) * Rectangle(2, 2).face()
)  # tangent to sphere at x=1

shape_2d_matrix = [
    Case(fc1, vl2, None, "non-coincident", None),
    Case(fc1, vl1, [Vertex], "coincident", None),
    Case(fc1, lc2, None, "non-coincident", None),
    Case(fc1, lc1, [Vertex], "coincident", None),
    Case(fc2, ax1, None, "parallel/skew", None),
    Case(fc3, ax1, [Vertex], "intersecting", None),
    Case(fc1, ax1, [Edge], "collinear", None),
    Case(fc1, pl3, None, "parallel/skew", None),
    Case(fc1, pl1, [Edge], "intersecting", None),
    Case(fc1, pl2, [Face], "collinear", None),
    Case(fc7, pl1, [Edge, Edge], "multi intersect", None),
    Case(fc1, vt2, None, "non-coincident", None),
    Case(fc1, vt1, [Vertex], "coincident", None),
    Case(fc1, ed3, None, "parallel/skew", None),
    Case(Pos(1) * fc3, ed1, [Vertex], "intersecting", None),
    Case(fc1, ed1, [Edge], "collinear", None),
    Case(Pos(1.1) * fc3, ed4, [Vertex, Vertex], "multi intersect", None),
    Case(fc1, wi6, None, "parallel/skew", None),
    Case(Pos(1) * fc3, wi4, [Vertex], "intersecting", None),
    Case(fc1, wi1, [Edge, Edge], "2 collinear", None),
    Case(Rot(90) * fc4, wi5, [Vertex, Vertex], "multi intersect", None),
    Case(Rot(90) * fc4, wi2, [Vertex, Edge], "intersect + collinear", None),
    Case(fc1, fc2, None, "parallel/skew", None),
    Case(fc1, fc3, [Edge], "intersecting", None),
    Case(fc1, fc4, [Face], "coplanar", None),
    Case(fc1, fc5, [Edge], "intersecting edge", None),
    # Face + Face crossing vertex: now requires include_touched
    Case(fc1, fc6, None, "crossing vertex", None),
    Case(fc1, fc6, [Vertex], "crossing vertex", None, True),
    Case(fc1, fc7, [Edge, Edge], "multi-intersecting", None),
    Case(fc7, Pos(Y=2) * fc7, [Face], "cyl intersecting", None),
    Case(sh2, fc1, None, "parallel/skew", None),
    Case(Pos(Z=1) * sh3, fc1, [Edge], "intersecting", None),
    Case(sh1, fc1, [Face, Edge], "coplanar + intersecting", None),
    Case(sh4, fc1, [Face, Face], "2 coplanar", None),
    Case(sh5, fc1, [Edge, Edge], "2 intersecting", None),
    Case(sh6, Pos(0, 0, 1) * fc1, [Face], "2 intersecting boundary", None),
    Case(sh6, Pos(2, 1, 1) * sh6, [Face], "2 intersecting boundary", None),
    # Shell + Face tangent touch
    Case(sh7, fc10, None, "tangent touch", None),
    Case(sh7, fc10, [Vertex], "tangent touch", None, True),
    # Shell + Shell tangent touch
    Case(sh7, sh8, None, "tangent touch", None),
    Case(sh7, sh8, [Vertex], "tangent touch", None, True),
    Case(fc1, [fc4, Pos(2, 2) * fc1], [Face], "multi to_intersect, intersecting", None),
    Case(
        fc1,
        [ed1, Pos(2.5, 2.5) * fc1],
        [Edge],
        "multi to_intersect, intersecting",
        None,
    ),
    Case(fc7, [wi5, fc1], [Vertex], "multi to_intersect, intersecting", None),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(shape_2d_matrix)
)
def test_shape_2d(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# 3d Shapes
sl1 = Box(2, 2, 2).solid()
sl2 = Pos(Z=5) * Box(2, 2, 2).solid()
sl3 = Cylinder(2, 1).solid() - Cylinder(1.5, 1).solid()
sl4 = Box(3, 1, 1)
# T-shaped solid (box + thin plate) for testing coplanar face touches
sl5 = Pos(0.5, 0, 1) * Box(1, 1, 1) + Pos(0.5, 0, 1) * Box(2, 0.1, 1)
sl6 = Pos(2, 0, 1.5) * Box(2, 2, 1)
# Overlapping boxes where coplanar face is part of intersection (not touch)
sl7 = Pos(0, 0.1, 0) * Box(2, 2, 2)
sl8 = Pos(1, 0, -1) * Box(4, 2, 1)
# Extended T-shaped solid for testing coplanar edge touches
sl9 = Box(2, 2, 2) + sl5

wi7 = Wire(
    [
        l1 := sl3.faces().sort_by(Axis.Z)[-1].edges()[0].trim(0.3, 0.4),
        l2 := l1.trim(2, 3),
        RadiusArc(l1 @ 1, l2 @ 0, 1, short_sagitta=False),
    ]
)

shape_3d_matrix = [
    Case(sl2, vl1, None, "non-coincident", None),
    Case(Pos(2) * sl1, vl1, [Vertex], "contained", None),
    Case(Pos(1, 1, -1) * sl1, vl1, [Vertex], "coincident", None),
    Case(sl2, lc1, None, "non-coincident", None),
    Case(Pos(2) * sl1, lc1, [Vertex], "contained", None),
    Case(Pos(1, 1, -1) * sl1, lc1, [Vertex], "coincident", None),
    Case(sl2, ax1, None, "non-coincident", None),
    Case(sl1, ax1, [Edge], "intersecting", None),
    Case(Pos(1, 1, 1) * sl1, ax2, [Edge], "coincident", None),
    Case(sl1, pl3, None, "non-coincident", None),
    Case(sl1, pl2, [Face], "intersecting", None),
    Case(sl1, pl2.offset(1), [Face], "intersecting boondary", None),
    Case(sl2, vt1, None, "non-coincident", None),
    Case(Pos(2) * sl1, vt1, [Vertex], "contained", None),
    Case(Pos(1, 1, -1) * sl1, vt1, [Vertex], "coincident", None),
    Case(sl1, ed3, None, "non-coincident", None),
    Case(sl1, ed1, [Edge], "intersecting", None),
    Case(sl1, Pos(0, 1, 1) * ed1, [Edge], "edge collinear", None),  # xfail removed
    # Solid + Edge corner coincident: now requires include_touched
    Case(sl1, Pos(1, 1, 1) * ed1, None, "corner coincident", None),
    Case(sl1, Pos(1, 1, 1) * ed1, [Vertex], "corner coincident", None, True),
    Case(Pos(2.1, 1) * sl1, ed4, [Edge, Edge], "multi-intersect", None),
    Case(Pos(2.1, 1, -1) * sl1, ed4, [Edge, Edge], "multi-intersect, boundary", None),
    Case(Pos(2, 0.5, -1) * sl1, wi6, None, "non-coincident", None),
    Case(Pos(2, 0.5, 1) * sl1, wi6, [Edge, Edge], "multi-intersecting", None),
    Case(Pos(2, 0.5, 2) * sl1, wi6, [Edge, Edge], "multi-intersecting, boundary", None),
    Case(sl3, wi7, [Edge, Edge], "multi-coincident, is_equal check", None),
    Case(sl2, fc1, None, "non-coincident", None),
    Case(sl1, fc1, [Face], "intersecting", None),
    Case(Pos(0, 0, -1) * sl1, fc1, [Face], "intersecting, boundary", None),
    Case(Pos(0, 0, 1) * sl1, fc1, [Face], "intersecting, boundary", None),
    # Solid + Face edge collinear: now requires include_touched
    Case(Pos(3.5, 0, 1) * sl1, fc1, None, "edge collinear", None),
    Case(Pos(3.5, 0, 1) * sl1, fc1, [Edge], "edge collinear", None, True),
    # Solid + Face corner coincident: now requires include_touched
    Case(Pos(3.5, 3.5) * sl1, fc1, None, "corner coincident", None),
    Case(Pos(3.5, 3.5) * sl1, fc1, [Vertex], "corner coincident", None, True),
    Case(Pos(0.9) * sl1, fc7, [Face, Face], "multi-intersecting", None),
    Case(Pos(0.9, 1) * sl1, fc7, [Face, Face], "multi-intersecting", None),
    Case(Pos(0.9, 1.5) * sl1, fc7, [Face, Face], "multi-intersecting", None),
    Case(sl2, sh1, None, "non-coincident", None),
    Case(Pos(-2) * sl1, sh1, [Face, Face], "multi-intersecting", None),
    Case(Pos(-2) * sl1, sh1, [Face, Face], "multi-intersecting", None),
    Case(Pos(-2, 3) * sl1, sh1, None, "multi-intersecting", None),
    Case(Pos(-2, 3) * sl1, sh1, [Edge, Edge], "multi-intersecting", None, True),
    Case(sl1, sl2, None, "non-coincident", None),
    Case(sl1, Pos(1, 1, 1) * sl1, [Solid], "intersecting", None),
    # Solid + Solid edge collinear: now requires include_touched
    Case(sl1, Pos(2, 2, 1) * sl1, None, "edge collinear", None),
    Case(sl1, Pos(2, 2, 1) * sl1, [Edge], "edge collinear", None, True),
    # Solid + Solid face collinear: now requires include_touched
    Case(sl1, Pos(2, 1.5, 1) * sl1, None, "edge collinear", None),
    Case(sl1, Pos(2, 1.5, 1) * sl1, [Face], "edge collinear", None, True),
    # Solid + Solid corner coincident: now requires include_touched
    Case(sl1, Pos(2, 2, 2) * sl1, None, "corner coincident", None),
    Case(sl1, Pos(2, 2, 2) * sl1, [Vertex], "corner coincident", None, True),
    Case(sl1, Pos(0.45) * sl3, [Solid, Solid], "multi-intersect", None),
    # New test: Solid + Solid face coincident (touch)
    Case(sl1, Pos(2, 0, 0) * sl1, None, "face coincident", None),
    Case(sl1, Pos(2, 0, 0) * sl1, [Face], "face coincident", None, True),
    Case(
        Pos(1.5, 1.5) * sl1,
        [sl3, Pos(0.5, 0.5) * sl1],
        [Solid],
        "multi to_intersect, intersecting",
        None,
    ),
    Case(
        Pos(0, 1.5) * sl1,
        [sl3, Pos(0.5, 0.5) * sl1],
        [Solid, Solid],
        "multi to_intersect, intersecting",
        None,
    ),
    Case(
        Pos(0.5, 1.5) * sl1,
        [sl3, Pos(0.5, 0.5) * sl1],
        [Solid, Solid],
        "multi to_intersect, intersecting",
        None,
    ),
    Case(
        Pos(0.5, 1.5) * sl1,
        [sl3, Pos(0.5, 0.5) * sl1],
        [Solid, Solid],
        "multi to_intersect, intersecting",
        None,
        True,
    ),
    Case(
        Pos(1.5, 1.5) * sl1,
        [sl3, Pos(Z=0.5) * fc1],
        [Face],
        "multi to_intersect, intersecting",
        None,
    ),
    # T-shaped solid with coplanar face touches (edges should be filtered)
    Case(sl5, sl6, [Solid], "coplanar face touch", None),
    Case(sl5, sl6, [Solid, Face, Face], "coplanar face touch", None, True),
    # Overlapping boxes: coplanar face is part of intersection, not touch
    Case(sl7, sl8, [Solid], "coplanar face filtered", None),
    Case(sl7, sl8, [Solid], "coplanar face filtered", None, True),
    # Extended T-shaped solid with coplanar edge touches
    Case(sl9, sl6, [Solid], "coplanar edge touch", None),
    Case(sl9, sl6, [Solid, Face, Face, Edge, Edge], "coplanar edge touch", None, True),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(shape_3d_matrix)
)
def test_shape_3d(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# Compound Shapes
cp1 = Compound(GridLocations(5, 0, 2, 1) * Vertex())
cp2 = Compound(GridLocations(5, 0, 2, 1) * Line((0, -1), (0, 1)))
cp3 = Compound(GridLocations(5, 0, 2, 1) * Rectangle(2, 2))
cp4 = Compound(GridLocations(5, 0, 2, 1) * Box(2, 2, 2))
cp5 = Compound([fc8, fc9])
cp6 = Compound(GridLocations(4, 0, 2, 1) * Rectangle(2, 2))

cv1 = Curve() + [ed1, ed2, ed3]
sk1 = Sketch() + [fc1, fc2, fc3]
pt1 = Part() + [sl1, sl2, sl3]


shape_compound_matrix = [
    Case(cp1, vl1, None, "non-coincident", None),
    Case(Pos(-0.5) * cp1, vl1, [Vertex], "intersecting", None),
    Case(cp2, lc1, None, "non-coincident", None),
    Case(Pos(-0.5) * cp2, lc1, [Vertex], "intersecting", None),
    Case(Pos(Z=1) * cp3, ax1, None, "non-coincident", None),
    Case(cp3, ax1, [Edge, Edge], "intersecting", None),
    Case(Pos(Z=3) * cp4, pl2, None, "non-coincident", None),
    Case(cp4, pl2, [Face, Face], "intersecting", None),
    Case(Pos(Z=1) * cp4, pl2, [Face, Face], "non-coincident, boundary", None),
    Case(Pos(Z=-1) * cp4, pl2, [Face, Face], "non-coincident, boundary", None),
    Case(cp1, vt1, None, "non-coincident", None),
    Case(Pos(-0.5) * cp1, vt1, [Vertex], "intersecting", None),
    Case(Pos(Z=1) * cp2, ed1, None, "non-coincident", None),
    Case(cp2, ed1, [Vertex], "intersecting", None),
    Case(Pos(Z=1) * cp3, fc1, None, "non-coincident", None),
    Case(cp3, fc1, [Face, Face], "intersecting", None),
    Case(Pos(1) * cp3, fc1, [Face, Edge], "intersectingPos(0.5), ", None),
    Case(Pos(Z=5) * cp4, sl1, None, "non-coincident", None),
    Case(Pos(2) * cp4, sl1, [Solid], "intersecting", None),
    Case(cp4, sl4, None, "intersecting", None),
    Case(cp4, sl4, [Face, Face], "intersecting", None, True),
    Case(cp4, Pos(0, 1, 1) * sl4, [Face, Face], "intersecting", None, True),
    Case(cp4, Pos(0, 1, 1.5) * sl4, [Edge, Edge], "intersecting", None, True),
    Case(cp4, Pos(0, 1.5, 1.5) * sl4, [Vertex, Vertex], "intersecting", None, True),
    Case(cp1, Pos(Z=1) * cp1, None, "non-coincident", None),
    Case(cp1, cp2, [Vertex, Vertex], "intersecting", None),
    Case(cp2, cp3, [Edge, Edge], "intersecting", None),
    Case(Pos(0, 2, 0) * cp2, cp3, [Vertex, Vertex], "intersecting", None),
    Case(cp3, cp4, [Face, Face], "intersecting", None),
    Case(cp5, cp4, [Face, Face], "intersecting", None),
    Case(cp5, cp4, [Face, Face, Edge, Edge], "intersecting", None, True),
    Case(
        cp1,
        Compound(children=cp1.get_type(Vertex)),
        [Vertex, Vertex],
        "mixed child type",
        None,
    ),
    Case(
        cp4,
        Compound(children=cp3.get_type(Face)),
        [Face, Face],
        "mixed child type",
        None,
    ),
    Case(cp2, [cp3, cp4], [Edge, Edge], "multi to_intersect, intersecting", None),
    Case(cv1, cp3, [Edge, Edge, Edge, Edge], "intersecting", None),  # xfail removed
    Case(sk1, cp3, [Face, Face], "intersecting", None),
    Case(pt1, cp3, [Face, Face], "intersecting", None),
    Case(pt1, cp6, [Face, Face], "intersecting", None),
    Case(pt1, cp6, [Face, Face, Edge, Edge], "intersecting", None, True),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(shape_compound_matrix)
)
def test_shape_compound(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# FreeCAD issue example
c1 = CenterArc((0, 0), 10, 0, 360).edge()
c2 = CenterArc((19, 0), 10, 0, 360).edge()
skew = Line((-12, 0), (30, 10)).edge()
vert = Line((10, 0), (10, 20)).edge()
horz = Line((0, 10), (30, 10)).edge()
e1 = EllipticalCenterArc((5, 0), 5, 10, 0, arc_size=360).edge()

freecad_matrix = [
    Case(c1, skew, [Vertex, Vertex], "circle, skew, intersect", None),
    Case(c2, skew, [Vertex, Vertex], "circle, skew, intersect", None),
    Case(
        c1, e1, [Vertex, Vertex, Vertex], "circle, ellipse, intersect + tangent", None
    ),
    Case(c2, e1, [Vertex, Vertex], "circle, ellipse, intersect", None),
    Case(skew, e1, [Vertex, Vertex], "skew, ellipse, intersect", None),
    Case(skew, horz, [Vertex], "skew, horizontal, coincident", None),
    Case(skew, vert, [Vertex], "skew, vertical, intersect", None),
    Case(horz, vert, [Vertex], "horizontal, vertical, intersect", None),
    Case(vert, e1, [Vertex], "vertical, ellipse, tangent", None),
    Case(horz, e1, [Vertex], "horizontal, ellipse, tangent", None),
    Case(c1, c2, [Vertex, Vertex], "circle, skew, intersect", None),
    Case(c1, horz, [Vertex], "circle, horiz, tangent", None),
    Case(c2, horz, [Vertex], "circle, horiz, tangent", None),
    Case(c1, vert, [Vertex], "circle, vert, tangent", None),
    Case(c2, vert, [Vertex], "circle, vert, intersect", None),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(freecad_matrix)
)
def test_freecad(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# Issue tests
t = Sketch() + GridLocations(5, 0, 2, 1) * Circle(2)
s = Circle(10).face()
l = Line(-20, 20).edge()
a = Rectangle(10, 10).face()
b = (Plane.XZ * a).face()
e1 = Edge.make_line((-1, 0), (1, 0))
w1 = Wire.make_circle(0.5)
f1 = Face(Wire.make_circle(0.5))

issues_matrix = [
    Case(t, t, [Face, Face], "issue #1015", None),
    Case(l, s, [Edge], "issue #945", None),
    Case(a, b, [Edge], "issue #918", None),
    Case(e1, w1, [Vertex, Vertex], "issue #697", None),
    Case(e1, f1, [Edge], "issue #697", None),
]


@pytest.mark.parametrize(
    "obj, target, expected, include_touched", make_params(issues_matrix)
)
def test_issues(obj, target, expected, include_touched):
    run_test(obj, target, expected, include_touched)


# Exceptions
exception_matrix = [
    Case(vt1, Color(), None, "Unsupported type", None),
    Case(ed1, Color(), None, "Unsupported type", None),
    Case(fc1, Color(), None, "Unsupported type", None),
    Case(sl1, Color(), None, "Unsupported type", None),
    Case(cp1, Color(), None, "Unsupported type", None),
]


@pytest.mark.skip
def make_exception_params(matrix):
    params = []
    for case in matrix:
        obj_type = type(case.object).__name__
        tar_type = type(case.target).__name__
        i = len(params)
        uid = f"{i} {obj_type}, {tar_type}, {case.name}"
        params.append(pytest.param(case.object, case.target, case.expected, id=uid))

    return params


@pytest.mark.parametrize(
    "obj, target, expected", make_exception_params(exception_matrix)
)
def test_exceptions(obj, target, expected):
    with pytest.raises(Exception):
        obj.intersect(target)


# Direct touch() method tests
class TestTouchMethod:
    """Tests for direct touch() method calls to cover specific code paths."""

    def test_solid_vertex_touch_on_face(self):
        """Solid.touch(Vertex) where vertex is on a face of the solid."""
        solid = Box(2, 2, 2)  # Box from -1 to 1 in all axes
        # Vertex on the top face (z=1)
        vertex = Vertex(0, 0, 1)
        result = solid.touch(vertex)
        assert len(result) == 1
        assert isinstance(result[0], Vertex)

    def test_solid_vertex_touch_on_edge(self):
        """Solid.touch(Vertex) where vertex is on an edge of the solid."""
        solid = Box(2, 2, 2)
        # Vertex on an edge (corner of top face)
        vertex = Vertex(1, 0, 1)
        result = solid.touch(vertex)
        assert len(result) == 1
        assert isinstance(result[0], Vertex)

    def test_solid_vertex_touch_on_corner(self):
        """Solid.touch(Vertex) where vertex is on a corner of the solid."""
        solid = Box(2, 2, 2)
        # Vertex on a corner
        vertex = Vertex(1, 1, 1)
        result = solid.touch(vertex)
        assert len(result) == 1
        assert isinstance(result[0], Vertex)

    def test_solid_vertex_touch_not_touching(self):
        """Solid.touch(Vertex) where vertex is not on the solid boundary."""
        solid = Box(2, 2, 2)
        vertex = Vertex(5, 5, 5)  # Far away
        result = solid.touch(vertex)
        assert len(result) == 0

    def test_solid_vertex_touch_inside(self):
        """Solid.touch(Vertex) where vertex is inside the solid (not touch)."""
        solid = Box(2, 2, 2)
        vertex = Vertex(0, 0, 0)  # Center of box
        result = solid.touch(vertex)
        # Inside is not a touch - touch is boundary contact only
        assert len(result) == 0

    def test_shell_tangent_touch(self):
        """Shell.touch(Face) for tangent contact (sphere touching plane)."""
        # Create a hemisphere shell
        sphere = Sphere(1).faces()[0]
        shell = Shell([sphere])

        # Create a plane tangent to the sphere at bottom (z=-1)
        tangent_face = Face(Plane.XY.offset(-1))

        result = shell.touch(tangent_face)
        # Should find tangent vertex contact at (0, 0, -1)
        assert len(result) >= 1
        # Result should be vertex (tangent point)
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1

    def test_solid_solid_touch_faces_equal(self):
        """Solid.touch(Solid) exercises faces_equal for duplicate face detection."""
        b1 = Box(1, 1, 1, align=Align.MIN)
        b2 = (
            Box(2, 2, 0.5, align=Align.MIN)
            - Box(1, 1.2, 1, align=Align.MIN)
            + Pos(1, 0, 0) * Box(1, 1, 1, align=Align.MIN)
            + Box(1, 2, 0.5, align=Align.MIN)
        )
        result = b1.touch(b2)
        # Should find face contact
        assert len(result) >= 1
        faces = [r for r in result if isinstance(r, Face)]
        assert len(faces) >= 1


# ShapeList.expand() tests
class TestShapeListExpand:
    """Tests for ShapeList.expand() method."""

    def test_expand_with_vector(self):
        """ShapeList containing Vector objects."""
        from build123d import Vector, ShapeList

        v1 = Vector(1, 2, 3)
        v2 = Vector(4, 5, 6)
        shapes = ShapeList([v1, v2])
        expanded = shapes.expand()
        assert len(expanded) == 2
        assert v1 in expanded
        assert v2 in expanded

    def test_expand_nested_compound(self):
        """ShapeList with nested compounds."""
        # Create inner compound
        inner = Compound([Box(1, 1, 1), Pos(3, 0, 0) * Box(1, 1, 1)])
        # Create outer compound containing inner compound
        outer = Compound([inner, Pos(0, 3, 0) * Box(1, 1, 1)])

        shapes = ShapeList([outer])
        expanded = shapes.expand()

        # Should have 3 solids after expanding nested compounds
        solids = [s for s in expanded if isinstance(s, Solid)]
        assert len(solids) == 3

    def test_expand_shell_to_faces(self):
        """ShapeList with Shell expands to faces."""
        shells = Box(1, 1, 1).shells()  # Get shell from solid
        if shells:
            shell = shells[0]
            shapes = ShapeList([shell])
            expanded = shapes.expand()
            faces = [s for s in expanded if isinstance(s, Face)]
            assert len(faces) == 6  # Box has 6 faces

    def test_expand_wire_to_edges(self):
        """ShapeList with Wire expands to edges."""
        wire = Rectangle(2, 2).wire()
        shapes = ShapeList([wire])
        expanded = shapes.expand()
        edges = [s for s in expanded if isinstance(s, Edge)]
        assert len(edges) == 4  # Rectangle has 4 edges

    def test_expand_mixed(self):
        """ShapeList with mixed types."""
        from build123d import Vector

        v = Vector(1, 2, 3)
        wire = Rectangle(2, 2).wire()
        solid = Box(1, 1, 1)
        compound = Compound([Pos(5, 0, 0) * Box(1, 1, 1)])

        shapes = ShapeList([v, wire, solid, compound])
        expanded = shapes.expand()

        # Vector stays as vector
        assert v in expanded
        # Wire expands to 4 edges
        edges = [s for s in expanded if isinstance(s, Edge)]
        assert len(edges) == 4
        # Solid stays as solid
        solids = [s for s in expanded if isinstance(s, Solid)]
        assert len(solids) == 2  # Original + from compound


class TestShellTangentTouchCoverage:
    """Tests for Shell tangent touch to cover two_d.py lines 467-491.

    These tests specifically target the Shell-specific code paths in Face.touch()
    where we need to find which face in a Shell contains the contact point.
    """

    def test_shell_self_tangent_touch_multiple_faces(self):
        """Shell.touch(Face) where Shell has multiple faces.

        Finding face containing contact point in self Shell.
        """
        # Create a shell with multiple faces (half-sphere has curved + flat faces)
        half_sphere = Sphere(1) & Pos(0, 0, 0.5) * Box(3, 3, 2)
        shell = Shell(half_sphere.faces())

        # Create a plane tangent to the curved part at x=1
        tangent_face = Pos(1, 0, 0) * (Rot(0, 90, 0) * Rectangle(2, 2).face())

        result = shell.touch(tangent_face)
        # Should find tangent vertex at (1, 0, 0)
        assert len(result) >= 1
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1

    def test_face_shell_other_tangent_touch_multiple_faces(self):
        """Face.touch(Shell) where Shell (other) has multiple faces.

        Finding face containing contact point in other Shell.
        """
        # Create a face
        face = Pos(1, 0, 0) * (Rot(0, 90, 0) * Rectangle(2, 2).face())

        # Create a shell with multiple faces (half-sphere)
        half_sphere = Sphere(1) & Pos(0, 0, 0.5) * Box(3, 3, 2)
        shell = Shell(half_sphere.faces())

        result = face.touch(shell)
        # Should find tangent vertex at (1, 0, 0)
        assert len(result) >= 1
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1

    def test_shell_shell_tangent_touch_multiple_faces(self):
        """Shell.touch(Shell) where both Shells have multiple faces."""
        # Create two half-spheres touching at their curved surfaces
        half_sphere1 = Sphere(1) & Pos(0, 0, 0.5) * Box(3, 3, 2)
        shell1 = Shell(half_sphere1.faces())

        half_sphere2 = Pos(2, 0, 0) * (Sphere(1) & Pos(0, 0, 0.5) * Box(3, 3, 2))
        shell2 = Shell(half_sphere2.faces())

        result = shell1.touch(shell2)
        # Should find tangent vertex at (1, 0, 0)
        assert len(result) >= 1
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1

    def test_interior_tangent_contact_shell_face(self):
        """Shell.touch(Face) with interior tangent contact (not on any edges).

        Full interior tangent detection code path including Shell face
        lookup and normal direction validation.

        Contact point must be:
        - NOT on any edge of the shell (self)
        - NOT on any edge of the face (other)
        """
        import math

        # Create a sphere shell
        sphere = Sphere(2)
        shell = Shell(sphere.faces())

        # Contact at (1, 1, sqrt(2)) - away from the y=0 seam plane of the sphere
        # This point is in the interior of the spherical surface
        x, y, z = 1.0, 1.0, math.sqrt(2)

        # Normal direction at this point on the sphere
        normal = Vector(x, y, z).normalized()

        # Create a small face tangent to sphere at this point
        # The face must be small enough that its edges don't reach the contact point
        tangent_plane = Plane(origin=(x, y, z), z_dir=(normal.X, normal.Y, normal.Z))
        small_face = tangent_plane * Rectangle(0.1, 0.1).face()

        result = shell.touch(small_face)
        # Should find interior tangent vertex near (1, 1, sqrt(2))
        assert len(result) >= 1
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1

    def test_interior_tangent_contact_face_shell(self):
        """Face.touch(Shell) with interior tangent contact.

        Same as above but with arguments swapped to test the 'other is Shell' path.
        """
        import math

        # Create a sphere shell
        sphere = Sphere(2)
        shell = Shell(sphere.faces())

        # Contact at (1, 1, sqrt(2))
        x, y, z = 1.0, 1.0, math.sqrt(2)
        normal = Vector(x, y, z).normalized()

        # Create a small face tangent to sphere
        tangent_plane = Plane(origin=(x, y, z), z_dir=(normal.X, normal.Y, normal.Z))
        small_face = tangent_plane * Rectangle(0.1, 0.1).face()

        # Call face.touch(shell) - 'other' is the Shell
        result = small_face.touch(shell)
        assert len(result) >= 1
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1


class TestSolidEdgeTangentTouch:
    """Tests for Solid.touch(Edge) tangent cases to cover three_d.py lines 891-906.

    These tests cover the BRepExtrema tangent detection for edges tangent to
    solid surfaces (not penetrating).
    """

    def test_edge_tangent_to_cylinder(self):
        """Edge tangent to cylinder surface returns touch vertex.

        Tangent contact detection via BRepExtrema.
        """
        # Create a cylinder along Z axis
        cylinder = Cylinder(1, 2)

        # Create an edge that is tangent to the cylinder at x=1
        # Edge runs along Y at x=1, z=1 (tangent to cylinder surface)
        tangent_edge = Edge.make_line((1, -2, 1), (1, 2, 1))

        result = cylinder.touch(tangent_edge)
        # Should find tangent vertices where edge touches cylinder
        # The edge at x=1 is tangent to the cylinder at radius=1
        vertices = [r for r in result if isinstance(r, Vertex)]
        # Should have at least one tangent contact point
        assert len(vertices) >= 1

    def test_edge_tangent_to_sphere(self):
        """Edge tangent to sphere surface returns touch vertex.

        Another test with spherical geometry.
        """
        # Create a sphere centered at origin
        sphere = Sphere(1)

        # Create an edge that is tangent to the sphere at x=1
        # Edge runs along Z at x=1, y=0
        tangent_edge = Edge.make_line((1, 0, -2), (1, 0, 2))

        result = sphere.touch(tangent_edge)
        # Should find tangent vertex at (1, 0, 0)
        vertices = [r for r in result if isinstance(r, Vertex)]
        assert len(vertices) >= 1


class TestConvertToShapes:
    """Tests for helpers.convert_to_shapes() to cover helpers.py."""

    def test_vector_intersection(self):
        """Shape.intersect(Vector) converts Vector to Vertex."""
        box = Box(2, 2, 2)
        # Vector inside the box
        result = box.intersect(Vector(0, 0, 0))
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], Vertex)

    def test_location_intersection(self):
        """Shape.intersect(Location) converts Location to Vertex."""
        box = Box(2, 2, 2)
        # Location inside the box
        result = box.intersect(Location((0, 0, 0)))
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], Vertex)

    def test_location_intersection_with_rotation(self):
        """Shape.intersect(Location with rotation) still uses position only."""
        box = Box(2, 2, 2)
        # Location with rotation - position is still at origin
        loc = Location((0, 0, 0), (45, 45, 45))
        result = box.intersect(loc)
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], Vertex)


class TestEmptyCompoundIntersect:
    """Tests for Compound._intersect() edge cases to cover composite.py line 741."""

    def test_empty_compound_intersect(self):
        """Empty Compound.intersect() returns None.

        Early return when compound has no elements.
        """
        from OCP.TopoDS import TopoDS_Compound
        from OCP.BRep import BRep_Builder

        # Create an actual empty OCCT compound (has wrapped but no children)
        builder = BRep_Builder()
        empty_occt = TopoDS_Compound()
        builder.MakeCompound(empty_occt)
        empty = Compound(empty_occt)

        box = Box(2, 2, 2)
        result = empty.intersect(box)
        assert result is None

    def test_empty_compound_intersect_with_face(self):
        """Empty Compound.intersect(Face) returns None."""
        from OCP.TopoDS import TopoDS_Compound
        from OCP.BRep import BRep_Builder

        # Create an actual empty OCCT compound
        builder = BRep_Builder()
        empty_occt = TopoDS_Compound()
        builder.MakeCompound(empty_occt)
        empty = Compound(empty_occt)

        face = Rectangle(2, 2).face()
        result = empty.intersect(face)
        assert result is None
