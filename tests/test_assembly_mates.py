"""Tests for persistent Onshape-style assembly mates."""

import copy
from math import isclose

import numpy as np
import pytest

import build123d.assembly as assembly_module
from build123d import (
    Align,
    Assembly,
    Axis,
    BallMate,
    Box,
    Cylinder,
    CylindricalMate,
    Edge,
    Face,
    FastenedMate,
    GearRelation,
    GeomType,
    GroupMate,
    LinearRelation,
    Location,
    Mate,
    MateConnector,
    MateDOF,
    MateLimit,
    MateOffset,
    MateRelation,
    MateSolveError,
    ParallelMate,
    PinSlotMate,
    PlanarMate,
    Polyline,
    Pos,
    RackAndPinionRelation,
    RevoluteMate,
    ScrewRelation,
    SliderMate,
    Sphere,
    TangentMate,
    Vertex,
    WidthMate,
)


def assert_vector(vector, expected, tolerance=1e-5):
    """Assert a build123d vector against a tuple."""

    assert np.allclose(tuple(vector), tuple(expected), atol=tolerance)


def connector_pair():
    """Create two labeled components with one connector each."""

    base = Box(1, 1, 1)
    base.label = "base"
    moving = Pos(5, 3, 2) * Box(1, 1, 1)
    moving.label = "moving"
    fixed_connector = MateConnector("fixed", base, Location((0, 0, 1)))
    moving_connector = MateConnector("moving", moving, Location((5, 3, 2)))
    assembly = Assembly((base, moving), label="pair").ground(base)
    return assembly, base, moving, fixed_connector, moving_connector


@pytest.mark.parametrize(
    ("mate_type", "values", "position", "orientation"),
    [
        (FastenedMate, {}, (0, 0, 1), (0, 0, 0)),
        (RevoluteMate, {"rz": 30}, (0, 0, 1), (0, 0, 30)),
        (SliderMate, {"tz": 2}, (0, 0, 3), (0, 0, 0)),
        (
            PlanarMate,
            {"tx": 1, "ty": 2, "rz": 30},
            (1, 2, 1),
            (0, 0, 30),
        ),
        (
            CylindricalMate,
            {"tz": 2, "rz": 30},
            (0, 0, 3),
            (0, 0, 30),
        ),
        (PinSlotMate, {"tx": 2, "rz": 30}, (2, 0, 1), (0, 0, 30)),
    ],
)
def test_connector_mate_motion(mate_type, values, position, orientation):
    """Connector mate DOFs follow Onshape's Z-primary coordinate convention."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    mate = assembly.add_mate(mate_type("mate", connector1, connector2), solve=False)
    for dof, value in values.items():
        mate.set_value(dof, value)

    result = assembly.solve()

    assert result.success
    assert_vector(moving.location.position, position)
    assert_vector(moving.location.orientation, orientation)


def test_ball_mate_preserves_rotation_and_coincides_centers():
    """Ball mates lock translation while retaining all rotational DOFs."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    moving.location = Location((5, 3, 2), (20, 10, 30))
    assembly.add_mate(BallMate("ball", connector1, connector2))

    assert_vector(connector1.location.position, connector2.location.position)
    assert_vector(moving.location.orientation, (20, 10, 30), tolerance=1e-4)


def test_parallel_mate_locks_tilt_only():
    """Parallel mates leave XYZ translation and Z rotation free."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    moving.location = Location((5, 3, 2), (25, -15, 40))
    assembly.add_mate(ParallelMate("parallel", connector1, connector2))

    z1 = np.asarray(tuple(connector1.location.z_axis.direction))
    z2 = np.asarray(tuple(connector2.location.z_axis.direction))
    assert np.dot(z1, z2) > 1 - 1e-7
    assert_vector(moving.location.position, (5, 3, 2), tolerance=1e-4)


def test_tangent_mate_propagates_after_fixed_component_moves():
    """Tangent contact is solved geometrically, including after penetration."""

    base = Box(
        10,
        10,
        1,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    base.label = "base"
    ball = Pos(0, 0, 4) * Sphere(1)
    ball.label = "ball"
    top = base.faces().sort_by(Axis.Z)[-1]
    sphere_face = ball.faces()[0]
    assembly = Assembly((base, ball)).ground(base)
    assembly.add_mate(
        TangentMate(
            "tangent",
            base,
            top,
            ball,
            sphere_face,
            propagate=False,
        )
    )
    assert_vector(ball.location.position, (0, 0, 2), tolerance=1e-4)

    base.move(Pos(0, 0, 2))
    result = assembly.solve(max_iterations=500)

    assert result.success
    assert_vector(ball.location.position, (0, 0, 4), tolerance=1e-4)


def test_tangent_mate_accepts_analytic_faces():
    """Analytic swept faces are valid Tangent mate selections."""

    # A sphere provides an analytic control selection for the positive case.
    sphere1 = Sphere(1)
    sphere2 = Pos(3, 0, 0) * Sphere(1)
    TangentMate(
        "analytic",
        sphere1,
        sphere1.faces()[0],
        sphere2,
        sphere2.faces()[0],
        propagate=False,
    )


def test_tangent_selection_validation(monkeypatch):
    """Tangent validates components, selections, and unsupported surfaces."""

    first = Box(1, 1, 1)
    second = Pos(2, 0, 0) * Box(1, 1, 1)
    with pytest.raises(ValueError):
        TangentMate(
            "same",
            first,
            first.faces()[0],
            first,
            first.faces()[1],
        )
    with pytest.raises(TypeError):
        TangentMate("bad", first, first, second, second.faces()[0])

    monkeypatch.setattr(
        Face,
        "geom_type",
        property(lambda _: GeomType.BSPLINE),
    )
    with pytest.raises(ValueError):
        TangentMate(
            "spline",
            first,
            first.faces()[0],
            second,
            second.faces()[0],
        )


def test_tangent_mate_propagates_across_tangent_edges():
    """Tangent propagation follows connected edges with continuous tangents."""

    first = Polyline((0, 0), (1, 0), (2, 0))
    second = Pos(0, 1, 0) * Polyline((0, 0), (1, 0), (2, 0))
    mate = TangentMate(
        "edge propagation",
        first,
        first.edges()[0],
        second,
        second.edges()[0],
    )

    assert len(mate.entities1) == 2
    assert len(mate.entities2) == 2


def test_tangent_helper_entity_combinations():
    """Tangent helpers cover face, edge, and vertex selections."""

    box = Box(2, 2, 2)
    face = box.faces()[0]
    edge = box.edges()[0]
    vertex = box.vertices()[0]
    other_edge = Edge.make_line((10, 0, 0), (11, 0, 0))

    assert not assembly_module._shared_tangent_edge(box.faces()[0], box.faces()[-1])
    assert not assembly_module._edges_tangent_at_shared_vertex(edge, other_edge)
    assert assembly_module._propagated_faces(box, face)
    assert assembly_module._propagated_entities(box, face)
    assert assembly_module._propagated_faces(Box(1, 1, 1), face) == [face]
    assert assembly_module._propagated_edges(box, edge)
    assert assembly_module._propagated_edges(Box(1, 1, 1), other_edge) == [other_edge]
    assert assembly_module._propagated_entities(box, vertex) == [vertex]

    edge_parameters = assembly_module._entity_parameters(edge, edge.position_at(0.5))
    assert len(edge_parameters) == 1
    assert assembly_module._entity_parameters(vertex, vertex.center()) == []
    for entity in (face, edge, vertex):
        candidates = assembly_module._parameter_candidates(entity)
        assert candidates
        point, direction = assembly_module._entity_point_direction(
            entity, candidates[0]
        )
        assert len(point) == 3
        assert (direction is None) is isinstance(entity, Vertex)

    face_direction = np.array((0.0, 0.0, 1.0))
    edge_direction = np.array((1.0, 0.0, 0.0))
    assert (
        assembly_module._tangent_alignment_error(
            vertex, None, edge, edge_direction, False
        )
        == 0
    )
    assert (
        assembly_module._tangent_alignment_error(
            face, face_direction, edge, edge_direction, False
        )
        == 0
    )
    assert (
        assembly_module._tangent_alignment_error(
            edge, edge_direction, other_edge, edge_direction, False
        )
        == 0
    )
    with pytest.raises(TypeError):
        assembly_module._EntityReference(box, box)


@pytest.mark.parametrize(
    ("first_kind", "second_kind"),
    [
        ("face", "edge"),
        ("edge", "face"),
        ("edge", "edge"),
        ("vertex", "vertex"),
    ],
)
def test_tangent_residual_selection_pairs(first_kind, second_kind):
    """Every supported Tangent entity pairing produces solver residuals."""

    first = Box(2, 2, 2)
    second = Pos(3, 0, 0) * Box(2, 2, 2)

    def select(component, kind):
        return {
            "face": component.faces()[0],
            "edge": component.edges()[0],
            "vertex": component.vertices()[0],
        }[kind]

    mate = TangentMate(
        "pair",
        first,
        select(first, first_kind),
        second,
        select(second, second_kind),
        propagate=False,
    )
    poses = assembly_module._PoseMap(
        {
            id(first): assembly_module._location_matrix(first.location),
            id(second): assembly_module._location_matrix(second.location),
        }
    )

    assert mate.residual(poses, 1).size >= 3
    assert mate.suppress().suppressed


def test_width_mate_centers_one_tab_on_slot_plane():
    """A one-tab Width mate behaves as a planar center constraint."""

    slot = Box(10, 10, 1)
    slot.label = "slot"
    tab = Location((0, 6, 0), (-90, 0, 0)) * Box(2, 1, 1)
    tab.label = "tab"
    width1 = MateConnector("width1", slot, Location((0, -2, 0)))
    width2 = MateConnector("width2", slot, Location((0, 2, 0)))
    tab_connector = MateConnector("tab", tab, tab.location)
    assembly = Assembly((slot, tab)).ground(slot)

    assembly.add_mate(WidthMate("width", tab_connector, (width1, width2)))

    assert isclose(tab_connector.location.position.Y, 0, abs_tol=1e-5)


def test_width_mate_two_tabs_remain_symmetric():
    """Two Width tabs on separate parts remain mirrored about the center plane."""

    slot = Box(10, 10, 1)
    slot.label = "slot"
    tab1 = Location((0, -1, 0), (-90, 0, 0)) * Box(1, 1, 1)
    tab1.label = "tab1"
    tab2 = Location((0, 1, 0), (90, 0, 0)) * Box(1, 1, 1)
    tab2.label = "tab2"
    width1 = MateConnector("width1", slot, Location((0, -3, 0)))
    width2 = MateConnector("width2", slot, Location((0, 3, 0)))
    connector1 = MateConnector("tab1", tab1, tab1.location)
    connector2 = MateConnector("tab2", tab2, tab2.location)
    assembly = Assembly((slot, tab1, tab2)).ground(slot)

    assembly.add_mate(WidthMate("width", (connector1, connector2), (width1, width2)))
    tab1.move(Pos(0, -1, 0))
    assembly.solve()

    assert isclose(
        connector1.location.position.Y,
        -connector2.location.position.Y,
        abs_tol=1e-5,
    )


def test_width_and_group_validation_and_suppression():
    """Width and Group validate their multi-component selections."""

    first = Box(1, 1, 1)
    second = Pos(2, 0, 0) * Box(1, 1, 1)
    third = Pos(4, 0, 0) * Box(1, 1, 1)
    first_connector = MateConnector("first", first, first.location)
    second_connector = MateConnector("second", second, second.location)
    third_connector = MateConnector("third", third, third.location)

    for tabs, widths in (
        ((), (second_connector, third_connector)),
        ((first_connector,), (second_connector,)),
    ):
        with pytest.raises(ValueError):
            WidthMate("width", tabs, widths)
    with pytest.raises(TypeError):
        WidthMate(
            "types",
            (first_connector,),
            (second_connector, object()),
        )
    with pytest.raises(ValueError):
        WidthMate(
            "overlap",
            first_connector,
            (first_connector, second_connector),
        )

    width = WidthMate(
        "valid",
        first_connector,
        (second_connector, third_connector),
    )
    assert width.suppress().suppressed

    with pytest.raises(ValueError):
        GroupMate("few", (first,))
    with pytest.raises(TypeError):
        GroupMate("type", (first, object()))
    with pytest.raises(ValueError):
        GroupMate("duplicate", (first, first))
    group = GroupMate("group", (first, second))
    assert group.suppress().suppressed


def test_offsets_flip_and_secondary_reorientation():
    """Offsets and mate-connector orientation controls remain persistent."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    mate = FastenedMate(
        "offset",
        connector1,
        connector2,
        offset=MateOffset((1, 2, 3), (0, 0, 15)),
        flip_primary=True,
        reorient_secondary=1,
    )
    assembly.add_mate(mate)

    assert_vector(moving.location.position, (1, 2, 4), tolerance=1e-4)
    assembly.component("base").move(Pos(5, 0, 0))
    assembly.solve()
    assert_vector(moving.location.position, (6, 2, 4), tolerance=1e-4)


def test_offset_and_limit_validation():
    """Each mate exposes only the Onshape-supported offset and limit fields."""

    _, _, _, connector1, connector2 = connector_pair()
    with pytest.raises(ValueError):
        RevoluteMate(
            "invalid-offset",
            connector1,
            connector2,
            offset=MateOffset((1, 0, 0)),
        )
    with pytest.raises(ValueError):
        SliderMate(
            "invalid-limit",
            connector1,
            connector2,
            limits={"rz": (-10, 10)},
        )
    with pytest.raises(ValueError):
        MateLimit(10, -10)

    limited = RevoluteMate(
        "limited",
        connector1,
        connector2,
        limits={"rz": (-30, 30)},
    )
    with pytest.raises(ValueError):
        limited.set_value("rz", 45)


def test_connector_mate_validation_and_coordinate_helpers():
    """Connector validation covers all public coordinate forms."""

    _, base, _, connector1, connector2 = connector_pair()
    with pytest.raises(TypeError):
        FastenedMate("bad", connector1, object())
    same_component = MateConnector("same", base, Location())
    with pytest.raises(ValueError):
        FastenedMate("same", connector1, same_component)
    with pytest.raises(ValueError):
        CylindricalMate(
            "rotation",
            connector1,
            connector2,
            offset=MateOffset(rotation=(10, 0, 0)),
        )
    with pytest.raises(ValueError):
        FastenedMate("fixed", connector1, connector2).set_value("tz", 1)

    slider = SliderMate("slider", connector1, connector2)
    slider.set_value("tz", 2).set_value("tz", None)
    assert slider.values == {}
    assert MateDOF.coerce("TZ") is MateDOF.TZ
    assert MateLimit(-1, 1).contains(0)

    relative = assembly_module._location_matrix(Location((1, 2, 3), (10, 20, 30)))
    coordinates = {
        dof: Mate.coordinate_from_relative(relative, dof)
        for dof in (
            MateDOF.TX,
            MateDOF.TY,
            MateDOF.TZ,
            MateDOF.RX,
            MateDOF.RY,
            MateDOF.RZ,
            MateDOF.SWING,
        )
    }
    assert_vector(
        (
            coordinates[MateDOF.TX],
            coordinates[MateDOF.TY],
            coordinates[MateDOF.TZ],
        ),
        (1, 2, 3),
    )

    limited = SliderMate(
        "range",
        connector1,
        connector2,
        limits={"tz": (-1, 1)},
    )
    below = np.eye(4)
    below[2, 3] = -2
    within = np.eye(4)
    assert limited._limit_residuals(below, 1)[0] < 0
    assert limited._limit_residuals(within, 1) == [0]

    with pytest.raises(ValueError):
        assembly_module._normalized(np.zeros(3))


def test_ball_conical_swing_limit():
    """Ball limits are a maximum angular swing away from connector Z."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    moving.location = Location((5, 3, 2), (60, 0, 0))
    assembly.add_mate(
        BallMate("ball", connector1, connector2, limits={"swing": (0, 20)})
    )

    relative_z = connector1.location.z_axis.direction.get_angle(
        connector2.location.z_axis.direction
    )
    assert relative_z <= 20 + 1e-4


def test_suppressed_mate_is_inactive():
    """Suppression retains a mate while removing it from the solve."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    mate = FastenedMate("mate", connector1, connector2, suppressed=True)
    assembly.add_mate(mate)
    assert_vector(moving.location.position, (5, 3, 2))

    mate.suppress(False)
    assembly.solve()
    assert_vector(moving.location.position, (0, 0, 1))


def test_inconsistent_mates_report_failure():
    """Closed constraint graphs fail clearly when their equations conflict."""

    assembly, base, _, connector1, connector2 = connector_pair()
    assembly.add_mate(
        FastenedMate("first", connector1, connector2),
        solve=False,
    )
    base_conflict = MateConnector("conflict", base, Location((0, 0, 3)))
    assembly.add_mate(
        FastenedMate("second", base_conflict, connector2),
        solve=False,
    )

    with pytest.raises(MateSolveError):
        assembly.solve()


def test_assembly_container_validation_and_convenience_methods():
    """Assembly covers container errors, lookups, grounding, and shortcuts."""

    duplicate1 = Box(1, 1, 1)
    duplicate1.label = "same"
    duplicate2 = Box(1, 1, 1)
    duplicate2.label = "same"
    with pytest.raises(ValueError):
        Assembly((duplicate1, duplicate2))

    empty = Assembly()
    assert empty.components == ()
    assert empty.solve().success
    with pytest.raises(TypeError):
        empty.add(object())

    first = Box(1, 1, 1)
    first.label = "first"
    assembly = Assembly((first,))
    with pytest.raises(ValueError):
        assembly.add(first)
    second = Box(1, 1, 1)
    assembly.add(second, name="second", fixed=True)
    assert assembly.is_fixed(second)
    assembly.ground(second, False)
    assert not assembly.is_fixed(second)
    with pytest.raises(ValueError):
        assembly.add(Box(1, 1, 1), name="second")
    with pytest.raises(KeyError):
        assembly.component("missing")
    with pytest.raises(ValueError):
        assembly.ground(Box(1, 1, 1))
    with pytest.raises(TypeError):
        assembly.add_mate(object())
    with pytest.raises(TypeError):
        assembly.add_relation(object())

    assert Assembly((Box(1, 1, 1),)).solve().success

    for method_name in (
        "fastened",
        "revolute",
        "slider",
        "planar",
        "cylindrical",
        "pin_slot",
        "ball",
        "parallel",
    ):
        current, _, _, connector1, connector2 = connector_pair()
        result = getattr(current, method_name)(
            method_name, connector1, connector2, solve=False
        )
        assert current.mate(method_name) is result

    current, base, moving, _, _ = connector_pair()
    tangent = current.tangent(
        "tangent shortcut",
        base,
        base.faces()[0],
        moving,
        moving.faces()[0],
        propagate=False,
        solve=False,
    )
    assert current.mate("tangent shortcut") is tangent

    slot = Box(1, 4, 1)
    tab = Pos(0, 2, 0) * Box(1, 1, 1)
    width1 = MateConnector("w1", slot, Location((0, -1, 0)))
    width2 = MateConnector("w2", slot, Location((0, 1, 0)))
    tab_connector = MateConnector("tab", tab, tab.location)
    current = Assembly((slot, tab))
    width = current.width(
        "width shortcut",
        tab_connector,
        (width1, width2),
        solve=False,
    )
    assert current.mate("width shortcut") is width

    group = current.group("group shortcut", (slot, tab), solve=False)
    assert current.mate("group shortcut") is group
    with pytest.raises(ValueError):
        current.add_mate(GroupMate("group shortcut", (slot, tab)), solve=False)
    with pytest.raises(KeyError):
        current.mate("missing")
    with pytest.raises(KeyError):
        current.relation("missing")


def test_assembly_rolls_back_failed_features():
    """Immediately solved invalid features are removed transactionally."""

    assembly, base, _, connector1, connector2 = connector_pair()
    assembly.add_mate(FastenedMate("first", connector1, connector2))
    conflict = MateConnector("conflict", base, Location((0, 0, 3)))
    with pytest.raises(MateSolveError):
        assembly.add_mate(FastenedMate("second", conflict, connector2))
    assert [mate.label for mate in assembly.mates] == ["first"]

    class ImpossibleRelation(MateRelation):
        @property
        def mates(self):
            return (assembly.mates[0],)

        def residual(self, poses, length_scale):
            return np.ones(1)

    impossible = ImpossibleRelation("impossible")
    with pytest.raises(MateSolveError):
        assembly.add_relation(impossible)
    assert impossible not in assembly.relations

    result = assembly.add_relation(impossible, solve=False)
    assert assembly.relation("impossible") is result
    with pytest.raises(ValueError):
        assembly.add_relation(impossible, solve=False)


def test_shallow_copies_are_distinct_component_instances():
    """Identity-based pose storage supports equal shallow-copy instances."""

    bolt = Cylinder(1, 2)
    bolt.label = "bolt1"
    end1 = MateConnector("end", bolt, Location((0, 0, 0)))
    bolt2 = copy.copy(bolt)
    bolt2.label = "bolt2"
    bolt2.move(Pos(5, 0, 0))
    base = Box(10, 2, 1)
    base.label = "base"
    base1 = MateConnector("base1", base, Location((-2, 0, 1)))
    base2 = MateConnector("base2", base, Location((2, 0, 1)))
    end2 = bolt2.joints["end"]
    assembly = Assembly((base, bolt, bolt2)).ground(base)
    assembly.add_mate(FastenedMate("one", base1, end1), solve=False)
    assembly.add_mate(FastenedMate("two", base2, end2), solve=False)

    assembly.solve()

    assert_vector(end1.location.position, (-2, 0, 1))
    assert_vector(end2.location.position, (2, 0, 1))


def test_deepcopy_preserves_independent_mates_and_grounding():
    """Deep-copied assemblies retain independently solvable design intent."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    mate = assembly.add_mate(RevoluteMate("hinge", connector1, connector2), solve=False)
    mate.set_value("rz", 15)
    assembly.solve()

    cloned = copy.deepcopy(assembly)
    assert cloned.is_fixed(cloned.component("base"))
    cloned.mate("hinge").set_value("rz", 45)
    cloned.solve()

    assert isclose(moving.location.orientation.Z, 15, abs_tol=1e-4)
    assert isclose(
        cloned.component("moving").location.orientation.Z,
        45,
        abs_tol=1e-4,
    )


def test_group_mate_preserves_component_origin_relationships():
    """A Group mate makes selected origins a persistent rigid cluster."""

    base = Box(1, 1, 1)
    base.label = "base"
    first = Pos(2, 0, 0) * Box(1, 1, 1)
    first.label = "first"
    second = Pos(2, 3, 0) * Box(1, 1, 1)
    second.label = "second"
    assembly = Assembly((base, first, second)).ground(base)
    assembly.add_mate(GroupMate("rigid cluster", (first, second)), solve=False)
    connector1 = MateConnector("base", base, Location())
    connector2 = MateConnector("group", first, first.location)
    assembly.add_mate(FastenedMate("mount", connector1, connector2))

    base.move(Pos(5, 0, 0))
    assembly.solve()

    assert_vector(first.location.position, (5, 0, 0), tolerance=1e-4)
    assert_vector(second.location.position, (5, 3, 0), tolerance=1e-4)


def rotational_pair():
    """Create two revolute components attached to a fixed base."""

    base = Box(1, 1, 1)
    base.label = "base"
    first = Pos(3, 0, 0) * Cylinder(1, 1)
    first.label = "first"
    second = Pos(-3, 0, 0) * Cylinder(1, 1)
    second.label = "second"
    base1 = MateConnector("base1", base, Location((3, 0, 1)))
    base2 = MateConnector("base2", base, Location((-3, 0, 1)))
    first_connector = MateConnector("first", first, Location((3, 0, 0)))
    second_connector = MateConnector("second", second, Location((-3, 0, 0)))
    assembly = Assembly((base, first, second)).ground(base)
    mate1 = assembly.add_mate(
        RevoluteMate("mate1", base1, first_connector), solve=False
    )
    mate2 = assembly.add_mate(
        RevoluteMate("mate2", base2, second_connector), solve=False
    )
    assembly.solve()
    return assembly, mate1, mate2


def test_relation_validation_and_suppression():
    """Mate relations reject incompatible DOFs and nonpositive ratios."""

    _, _, _, connector1, connector2 = connector_pair()
    revolute = RevoluteMate("revolute", connector1, connector2)
    slider = SliderMate("slider", connector1, connector2)
    cylindrical = CylindricalMate("cylindrical", connector1, connector2)
    parallel = ParallelMate("parallel", connector1, connector2)

    base_relation = MateRelation("base")
    assert base_relation.suppress().suppressed
    with pytest.raises(NotImplementedError):
        _ = base_relation.mates
    with pytest.raises(NotImplementedError):
        base_relation.residual({}, 1)

    with pytest.raises(ValueError):
        GearRelation("missing", slider, revolute)
    with pytest.raises(ValueError):
        GearRelation(
            "wrong kind",
            parallel,
            revolute,
            dof1="tx",
        )
    with pytest.raises(ValueError):
        GearRelation("ratio", revolute, revolute, ratio=0)

    with pytest.raises(ValueError):
        RackAndPinionRelation(
            "rotation",
            parallel,
            slider,
            1,
            rotational_dof="tx",
        )
    with pytest.raises(ValueError):
        RackAndPinionRelation(
            "linear",
            revolute,
            parallel,
            1,
            linear_dof="rz",
        )
    with pytest.raises(ValueError):
        RackAndPinionRelation("travel", revolute, slider, 0)

    with pytest.raises(ValueError):
        ScrewRelation("missing", revolute, 1)
    with pytest.raises(ValueError):
        ScrewRelation("travel", cylindrical, 0)

    with pytest.raises(ValueError):
        LinearRelation(
            "kind",
            parallel,
            slider,
            dof1="rz",
        )
    with pytest.raises(ValueError):
        LinearRelation("ratio", slider, slider, ratio=0)


def test_gear_relation():
    """Gear relations couple rotational DOFs with ratio and direction."""

    assembly, mate1, mate2 = rotational_pair()
    assembly.add_relation(GearRelation("gear", mate1, mate2, ratio=2))
    mate1.set_value("rz", 30)
    assembly.solve()

    assert isclose(
        mate2.connector2.parent.location.orientation.Z,
        -60,
        abs_tol=1e-4,
    )


def test_rack_and_pinion_relation():
    """Rack-and-pinion relates rotation to travel per revolution."""

    assembly, rotational, _ = rotational_pair()
    slider_component = Pos(0, 4, 0) * Box(1, 1, 1)
    slider_component.label = "rack"
    slider_base = MateConnector("rack-base", assembly.component("base"), Location())
    slider_end = MateConnector("rack-end", slider_component, slider_component.location)
    assembly.add(slider_component)
    slider = assembly.add_mate(
        SliderMate("slider", slider_base, slider_end), solve=False
    )
    assembly.solve()
    assembly.add_relation(RackAndPinionRelation("rack", rotational, slider, 20))
    rotational.set_value("rz", 180)
    assembly.solve()

    assert isclose(
        slider.connector2.parent.location.position.Z,
        10,
        abs_tol=1e-4,
    )


def test_rack_and_pinion_preserves_multiple_revolutions():
    """Commanded angles retain turn count when converted to linear travel."""

    assembly, rotational, _ = rotational_pair()
    slider_component = Pos(0, 4, 0) * Box(1, 1, 1)
    slider_component.label = "rack"
    slider_base = MateConnector("rack-base", assembly.component("base"), Location())
    slider_end = MateConnector("rack-end", slider_component, slider_component.location)
    assembly.add(slider_component)
    slider = assembly.add_mate(
        SliderMate("slider", slider_base, slider_end), solve=False
    )
    assembly.solve()
    assembly.add_relation(RackAndPinionRelation("rack", rotational, slider, 20))
    rotational.set_value("rz", 720)
    assembly.solve()

    assert isclose(slider_component.location.position.Z, 40, abs_tol=1e-4)


def test_screw_relation():
    """Screw relations couple two DOFs of one cylindrical mate."""

    assembly, _, moving, connector1, connector2 = connector_pair()
    mate = assembly.add_mate(
        CylindricalMate("cylindrical", connector1, connector2), solve=False
    )
    assembly.solve()
    assembly.add_relation(ScrewRelation("screw", mate, 2))
    initial_z = moving.location.position.Z
    mate.set_value("rz", 180)
    assembly.solve()

    assert isclose(moving.location.position.Z, initial_z + 1, abs_tol=1e-4)


def test_linear_relation():
    """Linear relations couple two translational DOFs."""

    base = Box(1, 1, 1)
    base.label = "base"
    first = Pos(3, 0, 0) * Box(1, 1, 1)
    first.label = "first"
    second = Pos(-3, 0, 0) * Box(1, 1, 1)
    second.label = "second"
    base1 = MateConnector("base1", base, Location((3, 0, 0)))
    base2 = MateConnector("base2", base, Location((-3, 0, 0)))
    end1 = MateConnector("end1", first, first.location)
    end2 = MateConnector("end2", second, second.location)
    assembly = Assembly((base, first, second)).ground(base)
    mate1 = assembly.add_mate(SliderMate("one", base1, end1), solve=False)
    mate2 = assembly.add_mate(SliderMate("two", base2, end2), solve=False)
    assembly.solve()
    assembly.add_relation(LinearRelation("linear", mate1, mate2, ratio=0.5))
    mate1.set_value("tz", 4)
    assembly.solve()

    assert isclose(second.location.position.Z, -2, abs_tol=1e-4)
