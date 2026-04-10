from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import build123d.brep_from_stl as bfs
from build123d import *
from build123d import Shape


class DummyVertex:
    def __init__(self, point: Vector):
        self._point = point

    def center(self) -> Vector:
        return self._point


class DummyEdge:
    def __init__(self, start: Vector, end: Vector):
        self._vertices = [DummyVertex(start), DummyVertex(end)]

    def vertices(self):
        return self._vertices


class DummyBBox:
    def __init__(self, diagonal: float = 1.0):
        self.diagonal = diagonal
        self.min = Vector(0, 0, 0)
        self.max = Vector(diagonal, diagonal, diagonal)
        self.size = Vector(diagonal, diagonal, diagonal)


class DummyFace:
    def __init__(
        self,
        *,
        edges=None,
        vertices=None,
        center=Vector(0, 0, 0),
        normal=Vector(0, 0, 1),
        area: float = 1.0,
        inside: bool = True,
        bbox: DummyBBox | None = None,
    ):
        self._edges = edges or []
        self._vertices = vertices or []
        self._center = center
        self._normal = normal
        self.area = area
        self._inside = inside
        self._bbox = bbox or DummyBBox()

    def edges(self):
        return self._edges

    def vertices(self):
        return self._vertices

    def center(self) -> Vector:
        return self._center

    def normal_at(self) -> Vector:
        return self._normal

    def bounding_box(self):
        return self._bbox

    def is_inside(self, _point, tolerance=0.0) -> bool:
        return self._inside


class DummyComponent:
    def __init__(self, faces):
        self._faces = faces

    def faces(self):
        return self._faces


class DummyCleanShape:
    def __init__(self, faces, diagonal: float = 10.0):
        self._faces = faces
        self._bbox = DummyBBox(diagonal)

    def clean(self):
        return self

    def faces(self):
        return self._faces

    def bounding_box(self):
        return self._bbox


class DummyFaceCollection(list):
    def filter_by(self, _geom_type):
        return self


# Demo/support
def mesh_and_reload(shape, path: str | Path):
    mesh_path = Path(path)
    mesher = Mesher()
    mesher.add_shape(shape, linear_deflection=0.01, angular_deflection=1)
    mesher.write(mesh_path)
    return Mesher().read(mesh_path)[0]


def geom_equal(reference_shape: Shape, code_str: str):
    """Evaluate generated code and compare geometry, not strings."""
    _, expr = code_str.split("=", 1)  # remove the r00 = to make it an expression
    shape: Shape = eval(expr)
    assert (
        abs(shape.area - reference_shape.area) < 0.1
    ), f"Area mismatch: {shape.area} vs {reference_shape.area}"

    ref_bbox = reference_shape.bounding_box()
    code_bbox = shape.bounding_box()
    assert (ref_bbox.min - code_bbox.min).length < 1e-2, "Bounding Box min mismatch"
    assert (ref_bbox.max - code_bbox.max).length < 1e-2, "Bounding Box max mismatch"

    return True


def make_face_sample(
    index: int,
    center: Vector,
    normal: Vector,
    face: DummyFace | Face | None = None,
) -> bfs.FaceSample:
    if face is None:
        face = DummyFace(center=center, normal=normal)
    return bfs.FaceSample(index=index, face=face, center=center, normal=normal)


def make_mesh_index(
    faces=None,
    samples=None,
    adjacency=None,
    face_key_lookup=None,
) -> bfs.MeshIndex:
    return bfs.MeshIndex(
        faces=faces or [],
        face_samples=samples or [],
        face_key_lookup=face_key_lookup or {},
        adjacent_face_indices=adjacency,
    )


def test_cylinder(tmp_path):
    mesh = mesh_and_reload(
        split(
            Cylinder(1, 2, align=None) + Sphere(1),
            Plane.XY.offset(1).rotated((0, 30, 0)),
            Keep.BOTTOM,
        ),
        tmp_path / "surface_detection_v3_cylinder.stl",
    )
    primitives, leftovers, code_lines = bfs.detect_primitives(mesh)
    assert len(primitives.filter_by(GeomType.PLANE)) >= 1
    assert len(primitives.filter_by(GeomType.CYLINDER)) == 1
    assert len(primitives.filter_by(GeomType.SPHERE)) == 1

    for primitive, code in zip(primitives, code_lines):
        assert geom_equal(primitive, code)


def test_sphere(tmp_path):
    mesh = mesh_and_reload(Sphere(1), tmp_path / "surface_detection_v3_sphere.stl")
    primitives, leftovers, code_lines = bfs.detect_primitives(mesh)
    assert len(primitives.filter_by(GeomType.PLANE)) == 0
    assert len(primitives.filter_by(GeomType.CYLINDER)) == 0
    assert len(primitives.filter_by(GeomType.SPHERE)) == 1
    assert len(leftovers) == 0

    for primitive, code in zip(primitives, code_lines):
        assert geom_equal(primitive, code)


def test_box(tmp_path):
    mesh = mesh_and_reload(
        fillet(Box(1, 1, 1).edges(), 0.1), tmp_path / "surface_detection_v3_box.stl"
    )
    primitives, leftovers, code_lines = bfs.detect_primitives(mesh)
    assert len(primitives.filter_by(GeomType.PLANE)) == 6
    assert len(primitives.filter_by(GeomType.CYLINDER)) == 12
    assert len(primitives.filter_by(GeomType.SPHERE)) == 8
    assert len(leftovers) == 0

    for primitive, code in zip(primitives, code_lines):
        assert geom_equal(primitive, code)


def test_box_with_hole(tmp_path):
    mesh = mesh_and_reload(
        Box(5, 5, 1) - Cylinder(1, 1),
        tmp_path / "surface_detection_v3_box_with_hole.stl",
    )
    primitives, leftovers, code_lines = bfs.detect_primitives(mesh)

    assert len(primitives.filter_by(GeomType.PLANE)) == 6
    assert len(primitives.filter_by(GeomType.CYLINDER)) == 1
    assert len(primitives.filter_by(GeomType.SPHERE)) == 0
    assert len(leftovers) == 0

    for primitive, code in zip(primitives, code_lines):
        assert geom_equal(primitive, code)


def test_helper_edge_cases():
    face = Rectangle(1, 1).face()

    assert bfs._median_scalar([1.0, 3.0, 2.0]) == 2.0
    assert bfs._cluster_points([(0.0, 0.0)], eps=0.1, min_samples=2) == []
    assert bfs._cluster_unit_vectors([Vector(1, 0, 0)], eps=0.1, min_samples=2) == []
    assert bfs._as_face(face, "already-a-face") is face
    assert bfs._pick_non_collinear_triplet([Vector(0, 0, 0), Vector(1, 0, 0)]) is None
    assert (
        bfs._pick_non_collinear_triplet(
            [Vector(0, 0, 0), Vector(1, 0, 0), Vector(2, 0, 0)]
        )
        is None
    )
    assert (
        bfs._circumradius_from_points(Vector(0, 0, 0), Vector(1, 0, 0), Vector(2, 0, 0))
        is None
    )
    assert bfs._relative_radius_spread((0.0, 0.0, 1.0)) == float("inf")

    with pytest.raises(RuntimeError, match="Expected Face"):
        bfs._as_face(object(), "broken")

    with pytest.raises(ValueError, match="near-zero"):
        bfs._normalized((0.0, 0.0, 0.0))

    with pytest.raises(ValueError, match="at least three points"):
        bfs._fit_plane_to_points([Vector(0, 0, 0), Vector(1, 0, 0)])


def test_build_face_edge_midpoint_adjacency_ignores_non_manifold_edges():
    shared_edge = DummyEdge(Vector(0, 0, 0), Vector(1, 0, 0))
    mesh_index = make_mesh_index(
        faces=[
            DummyFace(edges=[shared_edge]),
            DummyFace(edges=[shared_edge]),
            DummyFace(edges=[shared_edge]),
        ]
    )

    adjacency = bfs._build_face_edge_midpoint_adjacency(mesh_index)

    assert adjacency == {0: [], 1: [], 2: []}


def test_build_cylinder_face_error_paths(monkeypatch):
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    support_faces = [Rectangle(1, 1).face()]
    vertices = [Vector(1, 0, 0), Vector(1, 0, 2), Vector(0, 1, 0), Vector(0, 1, 2)]
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda faces: vertices)

    class PlaneWithoutFaces:
        def __mul__(self, _other):
            return object()

    monkeypatch.setattr(bfs, "Plane", lambda *args, **kwargs: PlaneWithoutFaces())
    with pytest.raises(RuntimeError, match="provide faces"):
        bfs.build_cylinder_face(patch, support_faces)

    class BrokenShape:
        def faces(self):
            return DummyFaceCollection([object()])

    class PlaneWithBrokenFaces:
        def __mul__(self, _other):
            return BrokenShape()

    monkeypatch.setattr(bfs, "Plane", lambda *args, **kwargs: PlaneWithBrokenFaces())
    with pytest.raises(RuntimeError, match="cylindrical face"):
        bfs.build_cylinder_face(patch, support_faces)


def test_axis_property_and_build_cylinder_face_skips_axis_vertices(monkeypatch):
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    assert patch.axis.direction == Vector(0, 0, 1)

    monkeypatch.setattr(
        bfs,
        "_unique_face_vertices",
        lambda _faces: [
            Vector(0, 0, 0),
            Vector(1, 0, 0),
            Vector(1, 0, 2),
            Vector(0, 1, 0),
            Vector(0, 1, 2),
        ],
    )

    class GoodShape:
        def faces(self):
            return DummyFaceCollection([Rectangle(1, 1).face()])

    class PlaneWithFaces:
        def __mul__(self, _other):
            return GoodShape()

    monkeypatch.setattr(bfs, "Plane", lambda *args, **kwargs: PlaneWithFaces())
    assert isinstance(bfs.build_cylinder_face(patch, [Rectangle(1, 1).face()]), Face)


def test_sphere_like_face_components_and_face_error_helpers(monkeypatch):
    mesh_index = make_mesh_index()

    def fake_signature(_adjacency, _mesh_index, face_index, _allowed):
        return () if face_index == 0 else (1.0, 1.05, 1.1)

    monkeypatch.setattr(
        bfs,
        "_build_face_edge_midpoint_adjacency",
        lambda _mesh_index: {0: [], 1: []},
    )
    monkeypatch.setattr(bfs, "_face_radius_signature", fake_signature)
    monkeypatch.setattr(
        bfs,
        "_connected_face_components",
        lambda _mesh_index, indices: [sorted(indices)],
    )

    assert bfs._sphere_like_face_components(mesh_index, {0, 1}) == [[1]]

    cylinder_patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    sphere_patch = bfs.SpherePatch(
        kind="sphere",
        face_indices=frozenset({0}),
        center=Vector(0, 0, 0),
        radius=1.0,
        residual=0.0,
    )

    assert (
        bfs._cylinder_face_error(
            make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
            cylinder_patch,
            10.0,
        )
        is None
    )
    assert (
        bfs._cylinder_face_error(
            make_face_sample(0, Vector(2, 0, 0), Vector(1, 0, 0)),
            cylinder_patch,
            10.0,
        )
        is None
    )
    assert (
        bfs._sphere_face_error(
            make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
            sphere_patch,
            10.0,
        )
        is None
    )
    assert (
        bfs._sphere_face_error(
            make_face_sample(0, Vector(2, 0, 0), Vector(1, 0, 0)),
            sphere_patch,
            10.0,
        )
        is None
    )


def test_grow_curved_patch_skips_zero_length_radials(monkeypatch):
    cylinder_patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0, 1}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.25,
    )
    cylinder_mesh = make_mesh_index(
        samples=[
            make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
            make_face_sample(1, Vector(1, 0, 0), Vector(1, 0, 0)),
        ],
        adjacency={0: set(), 1: set()},
    )
    monkeypatch.setattr(bfs, "_cylinder_face_error", lambda *_args: 0.0)
    grown_cylinder = bfs.grow_curved_patch(cylinder_mesh, cylinder_patch, {0, 1}, 10.0)
    assert grown_cylinder.radius == pytest.approx(1.0)

    sphere_patch = bfs.SpherePatch(
        kind="sphere",
        face_indices=frozenset({0, 1}),
        center=Vector(0, 0, 0),
        radius=1.0,
        residual=0.5,
    )
    sphere_mesh = make_mesh_index(
        samples=[
            make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
            make_face_sample(1, Vector(1, 0, 0), Vector(-1, 0, 0)),
        ],
        adjacency={0: set(), 1: set()},
    )
    monkeypatch.setattr(bfs, "_sphere_face_error", lambda *_args: 0.0)
    grown_sphere = bfs.grow_curved_patch(sphere_mesh, sphere_patch, {0, 1}, 10.0)
    assert grown_sphere.radius == pytest.approx(1.0)


def test_detect_planes_from_clean_proxy_guard_branches(monkeypatch):
    proxy_face = DummyFace(edges=[1, 2, 3, 4], center=Vector(0, 0, 0), area=2.0)
    shape = DummyCleanShape([proxy_face], diagonal=10.0)
    sample = make_face_sample(0, Vector(0, 0, 0), Vector(0, 0, 1))
    mesh_index = make_mesh_index(faces=[sample.face], samples=[sample])

    monkeypatch.setattr(bfs, "_bounding_boxes_overlap", lambda *_args: False)
    assert bfs._detect_planes_from_clean_proxy(shape, mesh_index) == []

    monkeypatch.setattr(bfs, "_bounding_boxes_overlap", lambda *_args: True)
    proxy_face._inside = False
    assert bfs._detect_planes_from_clean_proxy(shape, mesh_index) == []

    proxy_face._inside = True
    assert bfs._detect_planes_from_clean_proxy(shape, mesh_index) == []


@pytest.mark.parametrize(
    ("face_indices", "vertices", "distances", "normals", "expected"),
    [
        ([0], [Vector(0, 0, 0)] * 3, [0.0], [Vector(0, 0, 1)], None),
        ([0, 1], [Vector(0, 0, 0), Vector(1, 0, 0)], [0.0], [Vector(0, 0, 1)], None),
        (
            [0, 1],
            [Vector(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)],
            [1.0],
            [Vector(0, 0, 1), Vector(0, 0, 1)],
            None,
        ),
        (
            [0, 1],
            [Vector(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)],
            [0.0],
            [Vector(0, 0, 1), Vector(1, 0, 0)],
            None,
        ),
    ],
)
def test_build_plane_patch_rejects_invalid_inputs(
    monkeypatch, face_indices, vertices, distances, normals, expected
):
    faces = [DummyFace() for _ in range(max(face_indices, default=0) + 1)]
    samples = [
        make_face_sample(
            index, Vector(index, 0, 0), normals[min(index, len(normals) - 1)]
        )
        for index in range(len(faces))
    ]
    mesh_index = make_mesh_index(faces=faces, samples=samples)
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: vertices)
    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda _vertices: (Vector(0, 0, 0), Vector(0, 0, 1)),
    )
    monkeypatch.setattr(bfs, "_plane_point_distances", lambda *_args: distances)

    assert bfs._build_plane_patch(mesh_index, face_indices, shape_scale=1.0) is expected


def test_merge_equivalent_cylinders_group_merge_branches():
    sample = make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0))
    mesh_index = make_mesh_index(samples=[sample])
    patches = [
        bfs.CylinderPatch(
            kind="cylinder",
            face_indices=frozenset({0}),
            axis_point=Vector(0, 0, 0),
            axis_direction=Vector(0, 0, 1),
            radius=1.0,
            normal_sign=1,
            residual=0.1,
        ),
        bfs.CylinderPatch(
            kind="cylinder",
            face_indices=frozenset({0}),
            axis_point=Vector(0, 0, 0),
            axis_direction=Vector(0, 0, 1),
            radius=1.0,
            normal_sign=1,
            residual=0.2,
        ),
    ]

    assert bfs.merge_equivalent_cylinders(mesh_index, patches, 10.0) == []


def test_merge_equivalent_cylinders_merges_group_with_residuals():
    samples = [
        make_face_sample(0, Vector(1, 0, 0), Vector(1, 0, 0)),
        make_face_sample(1, Vector(0, 1, 0), Vector(0, 1, 0)),
    ]
    mesh_index = make_mesh_index(samples=samples)
    patches = [
        bfs.CylinderPatch(
            kind="cylinder",
            face_indices=frozenset({0}),
            axis_point=Vector(0, 0, 0),
            axis_direction=Vector(0, 0, 1),
            radius=1.0,
            normal_sign=1,
            residual=0.1,
        ),
        bfs.CylinderPatch(
            kind="cylinder",
            face_indices=frozenset({1}),
            axis_point=Vector(0, 0, 0),
            axis_direction=Vector(0, 0, 1),
            radius=1.0,
            normal_sign=1,
            residual=0.2,
        ),
    ]

    merged = bfs.merge_equivalent_cylinders(mesh_index, patches, 10.0)
    assert len(merged) == 1
    assert merged[0].face_indices == frozenset({0, 1})


@pytest.mark.parametrize(
    (
        "vertices",
        "patch_radius",
        "circumradius",
        "distances",
        "plane_normals",
        "expected",
    ),
    [
        (
            [Vector(0, 0, 0)] * 5,
            1.0,
            1.0,
            [0.0],
            [Vector(0, 0, 1), Vector(0, 0, 1)],
            False,
        ),
        (
            [Vector(0, 0, 0)] * 6,
            1.0,
            1.0,
            [0.0],
            [Vector(0, 0, 1), Vector(0, 0, 1)],
            False,
        ),
        (
            [
                Vector(1, 0, -1),
                Vector(0, 1, -1),
                Vector(-1, 0, -1),
                Vector(1, 0, 1),
                Vector(0, 1, 1),
                Vector(-1, 0, 1),
            ],
            2.0,
            1.0,
            [0.0, 0.0, 0.0],
            [Vector(0, 0, 1), Vector(0, 0, 1)],
            False,
        ),
        (
            [
                Vector(2, 0, -1),
                Vector(0, 2, -1),
                Vector(-2, 0, -1),
                Vector(1, 0, 1),
                Vector(0, 1, 1),
                Vector(-1, 0, 1),
            ],
            1.5,
            1.0,
            [0.0, 0.0, 0.0],
            [Vector(0, 0, 1), Vector(0, 0, 1)],
            False,
        ),
    ],
)
def test_validate_bounded_cylinder_basic_failure_modes(
    monkeypatch,
    vertices,
    patch_radius,
    circumradius,
    distances,
    plane_normals,
    expected,
):
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=patch_radius,
        normal_sign=1,
        residual=0.0,
    )
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: vertices)
    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda points: (
            Vector(0, 0, -1 if points[0].Z < 0 else 1),
            plane_normals[0] if points[0].Z < 0 else plane_normals[1],
        ),
    )
    monkeypatch.setattr(bfs, "_plane_point_distances", lambda *_args: distances)
    monkeypatch.setattr(
        bfs, "_pick_non_collinear_triplet", lambda points: tuple(points[:3])
    )
    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: circumradius)

    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is expected


def test_validate_bounded_cylinder_late_failure_modes(monkeypatch):
    vertices = [
        Vector(1, 0, -1),
        Vector(0, 1, -1),
        Vector(-1, 0, -1),
        Vector(1, 0, 1),
        Vector(0, 1, 1),
        Vector(-1, 0, 1),
    ]
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: vertices)
    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda points: (
            Vector(0, 0, -1 if points[0].Z < 0 else 1),
            Vector(0, 0, 1 if points[0].Z < 0 else 0),
        ),
    )
    monkeypatch.setattr(bfs, "_plane_point_distances", lambda *_args: [0.0, 0.0, 0.0])
    monkeypatch.setattr(
        bfs, "_pick_non_collinear_triplet", lambda points: tuple(points[:3])
    )

    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: None)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: 0.0)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: 1e-12)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False


def test_validate_bounded_cylinder_remaining_failure_modes(monkeypatch):
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )

    sparse_bins = [
        Vector(1, 0, -1),
        Vector(0, 1, -1),
        Vector(-1, 0, 1),
        Vector(0, 1, 1),
        Vector(-1, 0, 1),
        Vector(0, -1, 1),
    ]
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: sparse_bins)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    uneven_bins = [
        Vector(1, 0, -1),
        Vector(0, 1, -1),
        Vector(-1, 0, -1),
        Vector(1, 0, 1),
        Vector(0, 1, 1),
        Vector(-1, 0, 1),
        Vector(1, 1, 1),
        Vector(-1, -1, 1),
        Vector(0.5, 0.5, 1),
        Vector(-0.5, -0.5, 1),
    ]
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: uneven_bins)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    unit_uneven_bins = [
        Vector(1, 0, -1),
        Vector(0, 1, -1),
        Vector(-1, 0, -1),
        Vector(1, 0, 1),
        Vector(0, 1, 1),
        Vector(-1, 0, 1),
        Vector(0, -1, 1),
        Vector(0.707, 0.707, 1),
        Vector(-0.707, 0.707, 1),
        Vector(0.707, -0.707, 1),
    ]
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: unit_uneven_bins)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    base_vertices = [
        Vector(1, 0, -1),
        Vector(0, 1, -1),
        Vector(-1, 0, -1),
        Vector(1, 0, 1),
        Vector(0, 1, 1),
        Vector(-1, 0, 1),
    ]
    monkeypatch.setattr(bfs, "_unique_face_vertices", lambda _faces: base_vertices)
    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda points: (
            Vector(0, 0, -1 if points[0].Z < 0 else 1),
            Vector(0, 0, 1),
        ),
    )
    monkeypatch.setattr(bfs, "_plane_point_distances", lambda *_args: [1.0, 1.0, 1.0])
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(bfs, "_plane_point_distances", lambda *_args: [0.0, 0.0, 0.0])
    monkeypatch.setattr(bfs, "_pick_non_collinear_triplet", lambda _points: None)
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(
        bfs,
        "_pick_non_collinear_triplet",
        lambda points: tuple(points[:3]),
    )
    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: 1.0)
    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda points: (
            Vector(0, 0, -1 if points[0].Z < 0 else 1),
            Vector(0, 0, 1 if points[0].Z < 0 else 0),
        ),
    )
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(
        bfs,
        "_fit_plane_to_points",
        lambda points: (
            Vector(0, 0, -1 if points[0].Z < 0 else 1),
            Vector(0, 0, 1),
        ),
    )
    real_mean = bfs._mean_scalar
    monkeypatch.setattr(
        bfs,
        "_mean_scalar",
        lambda values: 0.0 if len(values) == 2 else real_mean(values),
    )
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(
        bfs,
        "_mean_scalar",
        lambda values: real_mean(values),
    )
    circumradii = iter([1.0, 2.0])
    monkeypatch.setattr(
        bfs, "_circumradius_from_points", lambda *_args: next(circumradii)
    )
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: 1.0)
    monkeypatch.setattr(
        bfs,
        "_unique_face_vertices",
        lambda _faces: [
            Vector(2, 0, -1),
            Vector(0, 2, -1),
            Vector(-2, 0, -1),
            Vector(1, 0, 1),
            Vector(0, 1, 1),
            Vector(-1, 0, 1),
        ],
    )
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False

    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.5,
        normal_sign=1,
        residual=0.0,
    )
    monkeypatch.setattr(
        bfs,
        "_unique_face_vertices",
        lambda _faces: [
            Vector(1, 0, -1),
            Vector(0, 1, -1),
            Vector(-1, 0, -1),
            Vector(2, 0, 1),
            Vector(0, 2, 1),
            Vector(-2, 0, 1),
        ],
    )
    monkeypatch.setattr(bfs, "_std_scalar", lambda _values: 0.0)
    monkeypatch.setattr(bfs, "_circumradius_from_points", lambda *_args: 1.5)
    monkeypatch.setattr(
        bfs,
        "_mean_scalar",
        lambda values: sum(values) / len(values),
    )
    assert bfs.validate_bounded_cylinder(patch, [], shape_scale=10.0) is False


def test_fit_local_cylinder_failure_modes(monkeypatch):
    parallel_samples = [
        make_face_sample(i, Vector(i, 0, 0), Vector(1, 0, 0)) for i in range(4)
    ]
    assert bfs.fit_local_cylinder(parallel_samples, 10.0) is None

    samples = [
        make_face_sample(0, Vector(1, 0, 0), Vector(1, 0, 0)),
        make_face_sample(1, Vector(0, 1, 0), Vector(0, 1, 0)),
        make_face_sample(2, Vector(-1, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(3, Vector(0, -1, 0), Vector(0, -1, 0)),
    ]
    monkeypatch.setattr(bfs, "_cluster_unit_vectors", lambda *_args, **_kwargs: [])
    assert bfs.fit_local_cylinder(samples, 10.0) is None

    monkeypatch.setattr(
        bfs,
        "_cluster_unit_vectors",
        lambda *_args, **_kwargs: [
            np.asarray([True, False, False, False, False, False])
        ],
    )
    assert bfs.fit_local_cylinder(samples, 10.0) is None

    monkeypatch.setattr(
        bfs,
        "_cluster_unit_vectors",
        lambda *_args, **_kwargs: [np.asarray([True] * 6)],
    )
    flattened_samples = [
        make_face_sample(i, Vector(i, 0, 0), Vector(0, 0, 1)) for i in range(4)
    ]
    assert bfs.fit_local_cylinder(flattened_samples, 10.0) is None

    monkeypatch.setattr(
        bfs,
        "_intersect_2d_lines",
        lambda *_args, **_kwargs: None,
    )
    assert bfs.fit_local_cylinder(samples, 10.0) is None

    monkeypatch.setattr(
        bfs,
        "_intersect_2d_lines",
        lambda *_args, **_kwargs: (0.0, 0.0),
    )
    monkeypatch.setattr(bfs, "_cluster_points", lambda *_args, **_kwargs: [])
    assert bfs.fit_local_cylinder(samples, 10.0) is None

    monkeypatch.setattr(
        bfs,
        "_cluster_points",
        lambda *_args, **_kwargs: [np.asarray([True] * 6)],
    )
    axis_samples = [
        make_face_sample(i, Vector(0, 0, float(i)), Vector(1, 0, 0)) for i in range(4)
    ]
    assert bfs.fit_local_cylinder(axis_samples, 10.0) is None

    big_radius_samples = [
        make_face_sample(0, Vector(20, 0, 0), Vector(1, 0, 0)),
        make_face_sample(1, Vector(0, 20, 0), Vector(0, 1, 0)),
        make_face_sample(2, Vector(-20, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(3, Vector(0, -20, 0), Vector(0, -1, 0)),
    ]
    assert bfs.fit_local_cylinder(big_radius_samples, 10.0) is None

    bad_normal_samples = [
        make_face_sample(0, Vector(1, 0, 0), Vector(0, 0, 1)),
        make_face_sample(1, Vector(0, 1, 0), Vector(0, 0, 1)),
        make_face_sample(2, Vector(-1, 0, 0), Vector(0, 0, 1)),
        make_face_sample(3, Vector(0, -1, 0), Vector(0, 0, 1)),
    ]
    assert bfs.fit_local_cylinder(bad_normal_samples, 10.0) is None


def test_fit_local_cylinder_remaining_failure_modes(monkeypatch):
    monkeypatch.setattr(
        bfs,
        "_cluster_unit_vectors",
        lambda *_args, **_kwargs: [np.asarray([True] * 6)],
    )
    monkeypatch.setattr(
        bfs, "_intersect_2d_lines", lambda *_args, **_kwargs: (0.0, 0.0)
    )
    monkeypatch.setattr(
        bfs,
        "_cluster_points",
        lambda *_args, **_kwargs: [np.asarray([True] * 6)],
    )

    too_few_points = [
        make_face_sample(0, Vector(1, 0, 0), Vector(0, 0, 1)),
        make_face_sample(1, Vector(0, 1, 0), Vector(0, 1, 0)),
        make_face_sample(2, Vector(-1, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(3, Vector(0, -1, 0), Vector(0, -1, 0)),
    ]
    assert bfs.fit_local_cylinder(too_few_points, 10.0) is None

    on_axis = [
        make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
        make_face_sample(1, Vector(0, 0, 0), Vector(0, 1, 0)),
        make_face_sample(2, Vector(0, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(3, Vector(0, 0, 0), Vector(0, -1, 0)),
    ]
    assert bfs.fit_local_cylinder(on_axis, 10.0) is None

    bad_residuals = [
        make_face_sample(0, Vector(1, 0, 0), Vector(0, 1, 0)),
        make_face_sample(1, Vector(0, 1, 0), Vector(-1, 0, 0)),
        make_face_sample(2, Vector(-1, 0, 0), Vector(0, -1, 0)),
        make_face_sample(3, Vector(0, -1, 0), Vector(1, 0, 0)),
    ]
    assert bfs.fit_local_cylinder(bad_residuals, 10.0) is None

    monkeypatch.setattr(
        bfs, "_plane_basis", lambda _axis: (Vector(1, 0, 0), Vector(0, 1, 0))
    )
    too_few_projected = [
        make_face_sample(0, Vector(1, 0, 0), Vector(0, 0, 1)),
        make_face_sample(1, Vector(0, 1, 0), Vector(1, 0, 0)),
        make_face_sample(2, Vector(-1, 0, 0), Vector(0, 1, 0)),
        make_face_sample(3, Vector(0, -1, 0), Vector(-1, 0, 0)),
    ]
    assert bfs.fit_local_cylinder(too_few_projected, 10.0) is None


def test_fit_local_cylinder_large_sample_set():
    samples = []
    for index in range(96):
        angle = 2.0 * np.pi * index / 96.0
        x = float(np.cos(angle))
        y = float(np.sin(angle))
        z = -1.0 + 2.0 * (index % 12) / 11.0
        samples.append(make_face_sample(index, Vector(x, y, z), Vector(x, y, 0)))

    patch = bfs.fit_local_cylinder(samples, 10.0)

    assert patch is not None
    assert patch.axis_direction.dot(Vector(0, 0, 1)) == pytest.approx(1.0, abs=1e-2)
    assert patch.radius == pytest.approx(1.0, abs=1e-2)
    assert patch.normal_sign == 1


def test_cylinder_like_face_indices_and_fit_local_sphere_failure_modes(monkeypatch):
    mesh_index = make_mesh_index(
        samples=[
            make_face_sample(0, Vector(0, 0, 0), Vector(1, 0, 0)),
            make_face_sample(1, Vector(0, 0, 0), Vector(1, 0, 0)),
            make_face_sample(2, Vector(0, 0, 0), Vector(1, 0, 0)),
        ]
    )
    signatures = {
        0: (0.0, 1.0),
        1: (1.0, 2.0),
        2: (1.0, 1.05, 2.5),
    }
    monkeypatch.setattr(
        bfs,
        "_build_face_edge_midpoint_adjacency",
        lambda _mesh_index: {0: [], 1: [], 2: []},
    )
    monkeypatch.setattr(
        bfs,
        "_face_radius_signature",
        lambda _adjacency, _mesh_index, face_index, _allowed: signatures[face_index],
    )
    assert bfs._cylinder_like_face_indices(mesh_index, {0, 1, 2}) == {1, 2}

    signatures[2] = (0.0, 0.0, 2.5)
    assert bfs._cylinder_like_face_indices(mesh_index, {0, 2}) == set()

    assert bfs.fit_local_sphere([], 10.0) is None

    samples = [
        make_face_sample(i, Vector(float(i), 0, 0), Vector(1, 0, 0)) for i in range(4)
    ]
    monkeypatch.setattr(
        bfs.np.linalg,
        "lstsq",
        lambda *_args, **_kwargs: (np.asarray([0.0, 0.0, 0.0, 0.0]), None, 3, None),
    )
    assert bfs.fit_local_sphere(samples, 10.0) is None

    monkeypatch.setattr(
        bfs.np.linalg,
        "lstsq",
        lambda *_args, **_kwargs: (np.asarray([0.0, 0.0, 0.0, 0.0]), None, 4, None),
    )
    assert bfs.fit_local_sphere(samples, 10.0) is None

    coincident = [
        make_face_sample(i, Vector(1, 0, 0), Vector(1, 0, 0)) for i in range(4)
    ]
    monkeypatch.setattr(
        bfs.np.linalg,
        "lstsq",
        lambda *_args, **_kwargs: (np.asarray([-2.0, 0.0, 0.0, 0.0]), None, 4, None),
    )
    assert bfs.fit_local_sphere(coincident, 10.0) is None

    large_radius = [
        make_face_sample(0, Vector(25, 0, 0), Vector(1, 0, 0)),
        make_face_sample(1, Vector(-25, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(2, Vector(0, 25, 0), Vector(0, 1, 0)),
        make_face_sample(3, Vector(0, -25, 0), Vector(0, -1, 0)),
    ]
    assert bfs.fit_local_sphere(large_radius, 10.0) is None

    bad_normals = [
        make_face_sample(0, Vector(1, 0, 0), Vector(0, 1, 0)),
        make_face_sample(1, Vector(-1, 0, 0), Vector(0, 1, 0)),
        make_face_sample(2, Vector(0, 1, 0), Vector(1, 0, 0)),
        make_face_sample(3, Vector(0, -1, 0), Vector(1, 0, 0)),
    ]
    monkeypatch.setattr(
        bfs.np.linalg,
        "lstsq",
        lambda *_args, **_kwargs: (np.asarray([0.0, 0.0, 0.0, -1.0]), None, 4, None),
    )
    assert bfs.fit_local_sphere(bad_normals, 10.0) is None


def test_fit_local_sphere_radius_std_limit(monkeypatch):
    samples = [
        make_face_sample(0, Vector(1, 0, 0), Vector(-1, 0, 0)),
        make_face_sample(1, Vector(-1, 0, 0), Vector(1, 0, 0)),
        make_face_sample(2, Vector(0, 1, 0), Vector(0, -1, 0)),
        make_face_sample(3, Vector(0, -2, 0), Vector(0, 1, 0)),
    ]
    monkeypatch.setattr(
        bfs.np.linalg,
        "lstsq",
        lambda *_args, **_kwargs: (np.asarray([0.0, 0.0, 0.0, -1.0]), None, 4, None),
    )
    assert bfs.fit_local_sphere(samples, 10.0) is None


def test_cylinder_sphere_disambiguation_and_finalize_cylinder(monkeypatch):
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0, 1, 2, 3}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=1.0,
    )
    samples = [
        make_face_sample(i, Vector(float(i), 0, 0), Vector(1, 0, 0)) for i in range(4)
    ]

    monkeypatch.setattr(bfs, "fit_local_sphere", lambda *_args, **_kwargs: None)
    assert bfs._cylinder_patch_looks_spherical(samples, patch, 10.0) is False

    monkeypatch.setattr(
        bfs,
        "fit_local_sphere",
        lambda *_args, **_kwargs: bfs.SpherePatch(
            kind="sphere",
            face_indices=frozenset({0, 1, 2, 3}),
            center=Vector(0, 0, 0),
            radius=1.0,
            residual=0.2,
        ),
    )
    assert bfs._cylinder_patch_looks_spherical(samples, patch, 10.0) is True

    mesh_index = make_mesh_index(
        faces=[DummyFace() for _ in range(4)],
        samples=samples,
        adjacency={0: set(), 1: set(), 2: set(), 3: set()},
    )

    small_patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0, 1}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    monkeypatch.setattr(bfs, "grow_curved_patch", lambda *_args, **_kwargs: small_patch)
    assert (
        bfs._finalize_cylinder_patch(mesh_index, patch, {0, 1, 2, 3}, 10.0, 4, False)
        is None
    )

    grown_patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0, 1, 2, 3}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )
    grow_results = iter([grown_patch, small_patch])
    monkeypatch.setattr(
        bfs,
        "grow_curved_patch",
        lambda *_args, **_kwargs: next(grow_results),
    )
    monkeypatch.setattr(
        bfs, "fit_local_cylinder", lambda *_args, **_kwargs: small_patch
    )
    assert (
        bfs._finalize_cylinder_patch(mesh_index, patch, {0, 1, 2, 3}, 10.0, 4, False)
        is None
    )

    monkeypatch.setattr(bfs, "grow_curved_patch", lambda *_args, **_kwargs: grown_patch)
    monkeypatch.setattr(bfs, "fit_local_cylinder", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        bfs, "_cylinder_patch_looks_spherical", lambda *_args, **_kwargs: True
    )
    assert (
        bfs._finalize_cylinder_patch(mesh_index, patch, {0, 1, 2, 3}, 10.0, 4, False)
        is None
    )

    monkeypatch.setattr(bfs, "grow_curved_patch", lambda *_args, **_kwargs: grown_patch)
    monkeypatch.setattr(
        bfs, "_cylinder_patch_looks_spherical", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        bfs, "validate_bounded_cylinder", lambda *_args, **_kwargs: False
    )
    assert (
        bfs._finalize_cylinder_patch(mesh_index, patch, {0, 1, 2, 3}, 10.0, 4, True)
        is None
    )


def test_detect_planes_cylinders_and_spheres_skip_invalid_candidates(monkeypatch):
    mesh = SimpleNamespace(bounding_box=lambda: DummyBBox(10.0))
    mesh_index = make_mesh_index(
        faces=[DummyFace() for _ in range(6)],
        samples=[
            make_face_sample(i, Vector(float(i), 0, 0), Vector(0, 0, 1))
            for i in range(6)
        ],
    )

    monkeypatch.setattr(
        bfs, "_detect_planes_from_clean_proxy", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        bfs, "_plane_like_face_components", lambda *_args, **_kwargs: [[0, 1, 2, 3]]
    )
    monkeypatch.setattr(bfs, "_build_plane_patch", lambda *_args, **_kwargs: None)
    assert bfs.detect_planes(mesh, mesh_index) == []

    monkeypatch.setattr(
        bfs, "_group_indices_by_area", lambda *_args, **_kwargs: [[0, 1, 2, 3]]
    )
    monkeypatch.setattr(bfs.Face, "sew_faces", lambda faces: [DummyComponent(faces)])
    monkeypatch.setattr(
        bfs,
        "_indices_from_sewn_component",
        lambda _mesh_index, _component: [0, 1, 2, 3],
    )
    monkeypatch.setattr(bfs, "fit_local_cylinder", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        bfs, "_cylinder_like_face_indices", lambda *_args, **_kwargs: [4, 5]
    )
    monkeypatch.setattr(bfs, "_bfs_patch", lambda *_args, **_kwargs: [4, 5, 0, 1])
    monkeypatch.setattr(bfs, "_finalize_cylinder_patch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bfs, "merge_equivalent_cylinders", lambda *_args, **_kwargs: [])
    assert bfs.detect_cylinders(mesh, mesh_index, blocked_indices=set()) == []

    sphere_patch = bfs.SpherePatch(
        kind="sphere",
        face_indices=frozenset({0, 1, 2, 3}),
        center=Vector(0, 0, 0),
        radius=1.0,
        residual=0.0,
    )
    monkeypatch.setattr(
        bfs, "_sphere_like_face_components", lambda *_args, **_kwargs: [[0, 1, 2, 3]]
    )
    monkeypatch.setattr(bfs, "fit_local_sphere", lambda *_args, **_kwargs: None)
    assert (
        bfs.detect_spheres(
            mesh, mesh_index, blocked_indices=set(), min_component_size=4
        )
        == []
    )

    monkeypatch.setattr(bfs, "fit_local_sphere", lambda *_args, **_kwargs: sphere_patch)
    monkeypatch.setattr(
        bfs,
        "grow_curved_patch",
        lambda *_args, **_kwargs: bfs.SpherePatch(
            kind="sphere",
            face_indices=frozenset({0, 1}),
            center=Vector(0, 0, 0),
            radius=1.0,
            residual=0.0,
        ),
    )
    assert (
        bfs.detect_spheres(
            mesh, mesh_index, blocked_indices=set(), min_component_size=4
        )
        == []
    )


def test_detect_planes_accepts_two_face_component(monkeypatch):
    mesh = SimpleNamespace(bounding_box=lambda: DummyBBox(10.0))
    mesh_index = make_mesh_index(
        faces=[DummyFace(), DummyFace()],
        samples=[
            make_face_sample(0, Vector(0, 0, 0), Vector(0, 0, 1)),
            make_face_sample(1, Vector(1, 0, 0), Vector(0, 0, 1)),
        ],
    )
    patch = bfs.PlanePatch(
        kind="plane",
        face_indices=frozenset({0, 1}),
        origin=Vector(0, 0, 0),
        normal=Vector(0, 0, 1),
        u_min=0.0,
        u_max=1.0,
        v_min=0.0,
        v_max=1.0,
        residual=0.0,
    )

    monkeypatch.setattr(
        bfs, "_detect_planes_from_clean_proxy", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        bfs, "_plane_like_face_components", lambda *_args, **_kwargs: [[0, 1]]
    )
    monkeypatch.setattr(bfs, "_build_plane_patch", lambda *_args, **_kwargs: patch)

    assert bfs.detect_planes(mesh, mesh_index, min_two_face_area_factor=0.0) == [patch]


def test_detect_cylinders_additional_continue_paths(monkeypatch):
    mesh = SimpleNamespace(bounding_box=lambda: DummyBBox(10.0))
    mesh_index = make_mesh_index(
        faces=[DummyFace() for _ in range(6)],
        samples=[
            make_face_sample(i, Vector(float(i), 0, 0), Vector(0, 0, 1))
            for i in range(6)
        ],
    )
    patch = bfs.CylinderPatch(
        kind="cylinder",
        face_indices=frozenset({0, 1, 2, 3}),
        axis_point=Vector(0, 0, 0),
        axis_direction=Vector(0, 0, 1),
        radius=1.0,
        normal_sign=1,
        residual=0.0,
    )

    monkeypatch.setattr(
        bfs, "_group_indices_by_area", lambda *_args, **_kwargs: [[0, 1, 2, 3]]
    )
    monkeypatch.setattr(bfs.Face, "sew_faces", lambda faces: [DummyComponent(faces)])
    monkeypatch.setattr(
        bfs,
        "_indices_from_sewn_component",
        lambda _mesh_index, _component: [0, 1, 2, 3],
    )
    monkeypatch.setattr(bfs, "fit_local_cylinder", lambda *_args, **_kwargs: patch)
    monkeypatch.setattr(bfs, "_finalize_cylinder_patch", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        bfs, "_cylinder_like_face_indices", lambda *_args, **_kwargs: [4]
    )
    monkeypatch.setattr(bfs, "_bfs_patch", lambda *_args, **_kwargs: [4, 5])
    monkeypatch.setattr(bfs, "merge_equivalent_cylinders", lambda *_args, **_kwargs: [])
    assert bfs.detect_cylinders(mesh, mesh_index, blocked_indices=set()) == []

    monkeypatch.setattr(bfs, "_group_indices_by_area", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bfs, "_bfs_patch", lambda *_args, **_kwargs: [4, 5, 0, 1])
    monkeypatch.setattr(bfs, "_finalize_cylinder_patch", lambda *_args, **_kwargs: None)
    assert bfs.detect_cylinders(mesh, mesh_index, blocked_indices=set()) == []


def test_suppress_duplicate_spheres_and_shapes_to_code_branches(monkeypatch):
    duplicate = bfs.suppress_duplicate_spheres(
        [
            bfs.SpherePatch("sphere", frozenset({0, 1}), Vector(0, 0, 0), 1.0, 0.2),
            bfs.SpherePatch("sphere", frozenset({0, 1}), Vector(0.01, 0, 0), 1.01, 0.1),
        ],
        center_tolerance=0.1,
    )
    assert len(duplicate) == 1

    plane_face = Rectangle(2, 1).face()

    class FakeRect:
        def intersect(self, _primitive):
            return [Rectangle(3, 3).face()]

    class FakeLocalVertices:
        def group_by(self, _axis):
            return [self]

        def sort_by(self, _axis):
            return [Vector(0, 0, 0)]

    class FakeLocalRect:
        def vertices(self):
            return FakeLocalVertices()

        def bounding_box(self):
            return SimpleNamespace(size=Vector(2, 1, 0))

    class FakePlaneForCode:
        def __init__(
            self, origin=Vector(0, 0, 0), x_dir=Vector(1, 0, 0), z_dir=Vector(0, 0, 1)
        ):
            self.origin = origin
            self.z_dir = z_dir

        def to_local_coords(self, _primitive):
            return FakeLocalRect()

        def from_local_coords(self, local_origin):
            return local_origin

        def shift_origin(self, global_origin):
            return FakePlaneForCode(origin=global_origin, z_dir=self.z_dir)

        def __mul__(self, _other):
            return FakeRect()

    monkeypatch.setattr(bfs, "Plane", FakePlaneForCode)
    monkeypatch.setattr(bfs, "_as_face", lambda _value, _context: FakeRect())
    plane_code = bfs.shapes_to_code([plane_face])[0]
    assert "Rectangle(1, 2" in plane_code

    class BrokenPlane(FakePlaneForCode):
        def shift_origin(self, global_origin):
            return object()

    monkeypatch.setattr(bfs, "Plane", BrokenPlane)
    with pytest.raises(RuntimeError, match="shift_origin"):
        bfs.shapes_to_code([plane_face])

    class EmptyIntersectRect(FakeRect):
        def intersect(self, _primitive):
            return []

    # monkeypatch.setattr(bfs, "Plane", FakePlaneForCode)
    # monkeypatch.setattr(bfs, "_as_face", lambda _value, _context: EmptyIntersectRect())
    # with pytest.raises(RuntimeError, match="planar rectangle"):
    #     bfs.shapes_to_code([plane_face])

    monkeypatch.setattr(bfs, "Plane", Plane)
    monkeypatch.setattr(bfs, "_PLANE_CONFIGS", [])
    cylinder_face = Cylinder(1, 2).faces().filter_by(GeomType.CYLINDER)[0]
    code = bfs.shapes_to_code([cylinder_face])[0]
    assert code.startswith("Location")


def test_detect_primitives_empty_sort_pair_path(monkeypatch):
    mesh = SimpleNamespace()
    sample_face = Rectangle(1, 1).face()
    mesh_index = make_mesh_index(faces=[sample_face], samples=[], face_key_lookup={})

    monkeypatch.setattr(bfs.MeshIndex, "from_shape", lambda _mesh: mesh_index)
    monkeypatch.setattr(bfs, "detect_planes", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bfs, "detect_spheres", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bfs, "detect_cylinders", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(bfs, "shapes_to_code", lambda primitives: [])

    primitives, leftovers, code_lines = bfs.detect_primitives(mesh)

    assert list(primitives) == []
    assert list(leftovers) == [sample_face]
    assert code_lines == []
