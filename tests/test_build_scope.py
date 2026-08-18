"""Behavioral contract tests for the Unified Build Scope migration."""

# pylint: disable=missing-function-docstring,no-member,duplicate-code

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Barrier

import pytest

from build123d import (
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Line,
    Locations,
    Mode,
    Plane,
    Pos,
    Rectangle,
    Rot,
)
from build123d.build_common import (
    BaseObject,
    BaseObjectMeta,
    BuildScope,
    Builder,
    LocationList,
    _build_scope_context,
    _get_build_scope,
    _pop_build_scope,
    _push_build_scope,
)


class CountingBuildPart(BuildPart):
    """BuildPart that records publication dispatch calls."""

    publication_calls: int = 0

    def _add_to_context(self, *objects, **kwargs):
        self.publication_calls += 1
        return super()._add_to_context(*objects, **kwargs)


def test_build_scope_identity_defaults():
    scope = BuildScope()
    other_scope = BuildScope()

    assert scope.parent is None
    assert scope.builder is None
    assert scope.operation_locations == (Pos(),)
    assert scope.publication_locations == (Pos(),)
    assert scope.output_placements == (Pos(),)
    assert scope.owner is None
    assert scope.publication_target is None
    assert scope.isolated is False
    assert scope.location_context is None
    assert scope.object_context is None
    assert scope.object_placements == (Pos(),)
    assert scope.operation_locations is not other_scope.operation_locations
    assert scope.operation_locations[0] is not other_scope.operation_locations[0]


def test_build_scope_rejects_empty_placement_state():
    for field in (
        "operation_locations",
        "publication_locations",
        "output_placements",
        "object_local_locations",
        "object_placements",
    ):
        with pytest.raises(ValueError, match=field):
            BuildScope(**{field: ()})


def test_build_scope_is_immutable():
    scope = BuildScope()

    with pytest.raises(FrozenInstanceError):
        setattr(scope, "isolated", True)


def test_build_scope_derives_child_with_explicit_overrides():
    builder = BuildPart()
    owner = object()
    location_context = LocationList([Pos(4, 0, 0)])
    parent = BuildScope(
        builder=builder,
        operation_locations=(Pos(1, 0, 0),),
        publication_locations=(Pos(2, 0, 0),),
        output_placements=(Pos(3, 0, 0),),
        owner=owner,
        publication_target=builder,
        location_context=location_context,
    )

    child = parent.derive(
        builder=None,
        operation_locations=(Pos(),),
        owner=None,
        isolated=True,
    )

    assert child.parent is parent
    assert child.builder is None
    assert child.operation_locations == (Pos(),)
    assert child.publication_locations == parent.publication_locations
    assert child.output_placements == parent.output_placements
    assert child.owner is None
    assert child.publication_target is builder
    assert child.isolated is True
    assert child.location_context is location_context
    assert child.object_context is None
    assert child.object_local_locations == (Pos(),)
    assert child.object_placements == parent.object_placements


def test_build_scope_is_authoritative_for_context_reads():
    builder = BuildPart()
    location_context = LocationList([Pos(1, 2, 3)])
    scope = BuildScope(
        builder=builder,
        location_context=location_context,
    )

    with _build_scope_context(scope):
        assert Builder._get_context(log=False) is builder
        assert LocationList._get_context() is location_context
        assert BaseObjectMeta._get_context() is None


def test_build_scope_context_restores_context_reads():
    builder = BuildPart()
    location_context = LocationList([Pos(1, 2, 3)])
    scope = BuildScope(
        builder=builder,
        location_context=location_context,
    )

    with _build_scope_context(scope):
        assert _get_build_scope() is scope
        assert Builder._get_context(log=False) is builder
        assert LocationList._get_context() is location_context
        assert BaseObjectMeta._get_context() is None

    assert _get_build_scope() is None
    assert Builder._get_context(log=False) is None
    assert LocationList._get_context() is None
    assert BaseObjectMeta._get_context() is None


def test_build_scope_push_and_pop_restore_previous_scope():
    root = BuildScope(owner="root")
    child = root.derive(owner="child")

    root_token = _push_build_scope(root)
    try:
        assert _get_build_scope() is root
        child_token = _push_build_scope(child)
        try:
            assert _get_build_scope() is child
        finally:
            _pop_build_scope(child_token)
        assert _get_build_scope() is root
    finally:
        _pop_build_scope(root_token)

    assert _get_build_scope() is None


def test_build_scope_context_restores_after_exception():
    scope = BuildScope(owner="failing")

    with pytest.raises(RuntimeError, match="scope failure"):
        with _build_scope_context(scope):
            assert _get_build_scope() is scope
            raise RuntimeError("scope failure")

    assert _get_build_scope() is None


def test_build_scope_contextvar_is_isolated_between_threads():
    barrier = Barrier(2)

    def observe_scope(identifier: int):
        scope = BuildScope(owner=identifier)
        with _build_scope_context(scope):
            barrier.wait()
            return _get_build_scope()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(observe_scope, (1, 2)))

    assert [scope.owner for scope in results if scope is not None] == [1, 2]
    assert _get_build_scope() is None


def test_build_scope_contextvar_is_isolated_between_async_tasks():
    async def observe_scope(
        identifier: int, ready: asyncio.Event, other: asyncio.Event
    ):
        scope = BuildScope(owner=identifier)
        with _build_scope_context(scope):
            ready.set()
            await other.wait()
            return _get_build_scope()

    async def run_tasks():
        first_ready = asyncio.Event()
        second_ready = asyncio.Event()
        return await asyncio.gather(
            observe_scope(1, first_ready, second_ready),
            observe_scope(2, second_ready, first_ready),
        )

    results = asyncio.run(run_tasks())
    assert [scope.owner for scope in results if scope is not None] == [1, 2]
    assert _get_build_scope() is None


def _build_part_in_called_function() -> BuildPart:
    """Create a Builder in a different Python frame."""
    with BuildPart() as child:
        Box(1, 1, 1)
    return child


def test_same_frame_builder_publishes_to_parent():
    with BuildPart() as parent:
        with BuildPart() as child:
            Box(1, 1, 1)

    assert child.builder_parent is parent
    assert len(parent.solids()) == 1


def test_cross_frame_builder_does_not_publish_to_parent():
    with BuildPart() as parent:
        with Locations((10, 0, 0)):
            Box(1, 1, 1)
        child = _build_part_in_called_function()

    assert child.builder_parent is None
    assert len(parent.solids()) == 1
    assert parent.solid().center().X == pytest.approx(10)


def test_builder_exception_retains_current_publication_behavior():
    with BuildPart() as parent:
        with pytest.raises(RuntimeError, match="construction failed"):
            with BuildPart():
                Box(1, 1, 1)
                raise RuntimeError("construction failed")

    assert parent.part.volume == pytest.approx(1)


def test_builder_mode_private_does_not_publish():
    with BuildPart() as parent:
        Box(1, 1, 1)
        with BuildPart(mode=Mode.PRIVATE) as private:
            Box(2, 2, 2)

    assert private.part.volume == pytest.approx(8)
    assert parent.part.volume == pytest.approx(1)


@pytest.mark.parametrize(
    ("mode", "expected_volume"),
    [
        (Mode.ADD, 68),
        (Mode.SUBTRACT, 60),
        (Mode.INTERSECT, 4),
        (Mode.REPLACE, 8),
    ],
)
def test_nested_builder_combination_modes(mode: Mode, expected_volume: float):
    with BuildPart() as parent:
        Box(4, 4, 4)
        with BuildPart(mode=mode):
            with Locations((2, 0, 0)):
                Box(2, 2, 2)

    assert parent.part is not None
    assert parent.part.volume == pytest.approx(expected_volume)


def test_contextvars_are_isolated_between_threads():
    barrier = Barrier(2)

    def observe_context(_identifier: int):
        with BuildPart() as builder:
            barrier.wait()
            return BuildPart._get_context(log=False), builder

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(observe_context, (1, 2)))

    assert results[0][0] is not results[1][0]
    assert all(context is builder for context, builder in results)


def test_contextvars_are_isolated_between_async_tasks():
    async def observe_context(ready: asyncio.Event, other: asyncio.Event):
        with BuildPart() as builder:
            ready.set()
            await other.wait()
            return BuildPart._get_context(log=False), builder

    async def run_tasks():
        first_ready = asyncio.Event()
        second_ready = asyncio.Event()
        return await asyncio.gather(
            observe_context(first_ready, second_ready),
            observe_context(second_ready, first_ready),
        )

    results = asyncio.run(run_tasks())
    assert results[0][0] is not results[1][0]
    assert all(context is builder for context, builder in results)


def test_outer_location_owns_root_scope_and_restores_scope_state():
    with Locations((1, 2, 3)) as locations:
        scope = _get_build_scope()
        assert scope is not None
        assert scope.parent is None
        assert scope.owner is locations
        assert scope.operation_locations == (Pos(1, 2, 3),)
        assert scope.location_context is locations

    assert _get_build_scope() is None
    assert LocationList._get_context() is None


def test_nested_locations_restore_exact_parent_scope():
    with Locations((10, 0, 0)) as outer:
        outer_scope = _get_build_scope()
        with Locations((1, 2, 3)) as inner:
            inner_scope = _get_build_scope()
            assert inner_scope is not None
            assert inner_scope.parent is outer_scope
            assert inner_scope.owner is inner
            assert inner_scope.operation_locations == (Pos(11, 2, 3),)
        assert _get_build_scope() is outer_scope
        assert LocationList._get_context() is outer


def test_location_scope_restores_after_exception():
    with pytest.raises(RuntimeError, match="location failure"):
        with Locations((1, 2, 3)):
            raise RuntimeError("location failure")

    assert _get_build_scope() is None


def test_outer_location_scope_survives_builder_lifecycle():
    with Locations((10, 0, 0)) as locations:
        location_scope = _get_build_scope()
        with BuildPart() as builder:
            assert _get_build_scope().parent is location_scope
            Box(1, 1, 1)
        assert _get_build_scope() is location_scope
        assert LocationList._get_context() is locations

    assert builder.part.center().X == pytest.approx(10)


def test_outer_locations_publish_completed_part():
    with Locations((10, 20, 30)):
        with BuildPart() as builder:
            Box(2, 4, 6)

    assert tuple(builder.part.center()) == pytest.approx((10, 20, 30))


def test_outer_locations_publish_completed_sketch():
    with Locations((10, 20)):
        with BuildSketch() as builder:
            Rectangle(2, 4)

    assert tuple(builder.sketch.face().center()) == pytest.approx((10, 20, 0))


def test_outer_locations_publish_completed_line():
    with Locations((10, 20)):
        with BuildLine() as builder:
            Line((0, 0), (2, 0))

    assert tuple(builder.line.edge().center()) == pytest.approx((11, 20, 0))


def test_part_selectors_are_local_and_part_is_placed():
    with BuildPart(Plane.YX) as builder:
        Box(2, 4, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
        local_z = builder.faces().sort_by(Axis.Z)[-1].center().Z
        active_placed_min_z = builder.part.bounding_box().min.Z

    assert local_z == pytest.approx(6)
    assert active_placed_min_z == pytest.approx(-6)
    assert builder.part.bounding_box().min.Z == pytest.approx(-6)
    assert builder.part_local.bounding_box().max.Z == pytest.approx(6)


def test_sketch_selectors_are_local_and_sketch_is_placed():
    with BuildSketch(Plane.XZ) as builder:
        Circle(2)
        assert builder.face().normal_at().Z == pytest.approx(1)

    assert abs(builder.sketch.face().normal_at().Y) == pytest.approx(1)
    assert builder.sketch_local.face().normal_at().Z == pytest.approx(1)


def test_line_selectors_are_local_and_line_is_placed():
    with BuildLine(Plane.YZ) as builder:
        Line((0, 0), (2, 0))
        assert tuple(builder.edge().end_point()) == pytest.approx((2, 0, 0))
        active_placed_end = builder.line.edge().end_point()

    assert tuple(active_placed_end) == pytest.approx((0, 2, 0))
    assert tuple(builder.line.edge().end_point()) == pytest.approx((0, 2, 0))
    assert tuple(builder.line_local.edge().end_point()) == pytest.approx((2, 0, 0))


def test_build_line_accepts_placement_keyword():
    with BuildLine(placement=Plane.YZ) as builder:
        Line((0, 0), (2, 0))

    assert tuple(builder.line.edge().end_point()) == pytest.approx((0, 2, 0))


def test_publication_locations_and_placements_form_cross_product():
    with Locations((-10, 0, 0), (10, 0, 0)):
        with BuildPart(Plane.XY, Plane.XY.offset(20)) as builder:
            Box(1, 1, 1)

    assert len(builder.part.solids()) == 4
    assert sorted(solid.center().X for solid in builder.part.solids()) == pytest.approx(
        [-10, -10, 10, 10]
    )
    assert sorted(solid.center().Z for solid in builder.part.solids()) == pytest.approx(
        [0, 0, 20, 20]
    )


def test_publication_location_precedes_output_placement():
    publication_location = Pos(10, 0, 0) * Rot(0, 0, 90)
    with Locations(publication_location):
        with BuildPart(Pos(2, 0, 0)) as builder:
            Box(1, 1, 1)

    assert tuple(builder.part.center()) == pytest.approx((10, 2, 0))


def test_publication_service_aggregates_before_parent_dispatch():
    parent = CountingBuildPart()
    parent.publication_calls = 0
    with parent:
        with Locations((-10, 0, 0), (10, 0, 0)):
            with BuildPart(Plane.XY, Plane.XY.offset(20)):
                Box(1, 1, 1)

    assert parent.publication_calls == 1
    assert len(parent.solids()) == 4


def test_base_object_operation_locations_publish_once_as_aggregate():
    builder = CountingBuildPart()
    builder.publication_calls = 0
    with builder:
        with Locations((-5, 0, 0), (5, 0, 0)):
            box = Box(1, 1, 1)

    assert builder.publication_calls == 1
    assert len(builder.solids()) == 2
    assert len(box.solids()) == 2


def test_curve_operation_locations_are_centralized():
    with BuildLine() as builder:
        with Locations((-5, 0), (5, 0)):
            Line((0, 0), (1, 0))

    assert sorted(edge.center().X for edge in builder.edges()) == pytest.approx(
        [-4.5, 5.5]
    )


def test_aggregate_placement_preserves_product_label():
    with BuildPart(Plane.XY, Plane.XY.offset(20)) as builder:
        Box(1, 1, 1)
        builder.part_local.label = "placed-part"

    assert builder.part.label == "placed-part"


def test_base_object_captures_builder_placements():
    class PlacementProbe(BaseObject):
        """Capture BaseObject protected API values during construction."""

        def __init__(self):
            self.builder = self._get_builder_context()
            self.locations = self._get_object_locations()
            self.local_locations = self._get_object_local_locations()
            self.placements = self._get_object_placements()

    with BuildPart(Plane.XZ) as builder:
        with Locations(Pos(10, 0, 0)):
            probe = PlacementProbe()

    assert probe.builder is builder
    assert probe.locations == (Pos(10, 0, 0),)
    assert probe.local_locations == (Pos(10, 0, 0),)
    assert probe.placements == (Plane.XZ.location,)


def test_external_line_geometry_is_not_inverse_transformed():
    reference = Line((0, 0), (2, 0))
    with BuildLine(Plane.YZ) as builder:
        Line(reference @ 0, reference @ 1)

    assert tuple(builder.line_local.edge().end_point()) == pytest.approx((2, 0, 0))
    assert tuple(builder.line.edge().end_point()) == pytest.approx((0, 2, 0))
