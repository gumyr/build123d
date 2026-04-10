"""
build123d BREP from STL

name: brep_from_stl.py
by:   gumyr with codex gpt-5.4
date: April 8th, 2026

desc:
    This python module reconstructs approximate analytic BREP primitives from a
    triangulated STL-like surface mesh.

    The user-facing entry point is ``detect_primitives``. The reconstruction
    pipeline first builds a mesh index of face centers, normals, and adjacency.
    It then searches for planes, spheres, and cylinders in that order so
    simpler and more stable primitives claim faces before more ambiguous curved
    regions are processed.

    Each detector uses a broad classification step to identify candidate faces,
    sews or connects them into regions, fits a local analytic primitive, and
    grows the region across adjacent compatible faces while validating the fit.
    The resulting primitive faces are then converted into build123d code strings
    aligned with the returned primitives.

license:

    Copyright 2026 gumyr

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

import copy
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from math import acos, ceil, log10, sqrt
from typing import Any, Literal, TypeAlias, TypeVar, overload

import numpy as np
from sklearn.cluster import DBSCAN  # type: ignore[import-untyped]

from build123d import (
    TOL_DIGITS,
    Align,
    Axis,
    Cylinder,
    Face,
    GeomType,
    Location,
    Plane,
    Pos,
    Rectangle,
    Shape,
    ShapeList,
    Sphere,
    Vector,
    Vertex,
)

EPS = 1e-9
T = TypeVar("T")
EdgeKey: TypeAlias = tuple[tuple[float, float, float], tuple[float, float, float]]


# Data model
@dataclass(frozen=True)
class FaceSample:
    """Cached geometric data for a mesh face."""

    index: int
    face: Face
    center: Vector
    normal: Vector


@dataclass(frozen=True)
class PlanePatch:
    """Plane primitive fitted to a set of mesh faces."""

    kind: Literal["plane"]
    face_indices: frozenset[int]
    origin: Vector
    normal: Vector
    u_min: float
    u_max: float
    v_min: float
    v_max: float
    residual: float


@dataclass(frozen=True)
class CylinderPatch:
    """Cylinder primitive fitted to a set of mesh faces."""

    kind: Literal["cylinder"]
    face_indices: frozenset[int]
    axis_point: Vector
    axis_direction: Vector
    radius: float
    normal_sign: Literal[-1, 1]
    residual: float

    @property
    def axis(self) -> Axis:
        """Axis property"""
        return Axis(self.axis_point, self.axis_direction)


@dataclass(frozen=True)
class SpherePatch:
    """Sphere primitive fitted to a set of mesh faces."""

    kind: Literal["sphere"]
    face_indices: frozenset[int]
    center: Vector
    radius: float
    residual: float


DetectedPatch = PlanePatch | CylinderPatch | SpherePatch


@dataclass
class MeshIndex:
    """Indexed mesh data reused by the primitive detectors."""

    faces: list[Face]
    face_samples: list[FaceSample]
    face_key_lookup: dict[tuple[tuple[float, float, float], ...], int]
    adjacent_face_indices: dict[int, set[int]] | None = None

    @classmethod
    def from_shape(cls, shape) -> "MeshIndex":
        """Create a mesh index from all faces of a shape."""

        faces = list(shape.faces())
        return cls(
            faces=faces,
            face_samples=[
                FaceSample(
                    index=index,
                    face=face,
                    center=face.center(),
                    normal=_normalized(face.normal_at()),
                )
                for index, face in enumerate(faces)
            ],
            face_key_lookup={
                _face_key(face): index for index, face in enumerate(faces)
            },
        )

    def ensure_adjacency(self) -> None:
        """Build the face adjacency map on first use."""

        if self.adjacent_face_indices is not None:
            return
        edge_to_face_indices: defaultdict[object, set[int]] = defaultdict(set)
        for index, face in enumerate(self.faces):
            for edge in face.edges():
                edge_to_face_indices[_edge_key(edge)].add(index)

        adjacency: dict[int, set] = {index: set() for index in range(len(self.faces))}
        for face_indices in edge_to_face_indices.values():
            for face_index in face_indices:
                adjacency[face_index].update(face_indices - {face_index})
        self.adjacent_face_indices = adjacency

    def face_set(self, face_indices: Iterable[int]) -> list[Face]:
        """Return faces by index while preserving the provided order."""

        return [self.faces[index] for index in face_indices]


# Basic numeric and vector helpers
def _rounded_vertex_key(vector: Vector, digits: int = 9) -> tuple[float, float, float]:
    """Convert a vector into a rounded, hashable key."""

    return tuple(round(value, digits) for value in vector)


def _vector_rows(vectors: Sequence[Vector]) -> np.ndarray:
    """Convert vectors into a NumPy row matrix."""

    return np.asarray([tuple(vector) for vector in vectors], dtype=float)


def _mean_scalar(values: Sequence[float]) -> float:
    """Return the arithmetic mean of scalar values."""

    return sum(values) / len(values)


def _median_scalar(values: Sequence[float]) -> float:
    """Return the median of scalar values."""

    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _std_scalar(values: Sequence[float]) -> float:
    """Return the population standard deviation of scalar values."""

    mean = _mean_scalar(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _mean_vector(vectors: Sequence[Vector]) -> Vector:
    """Return the arithmetic mean of vectors."""

    total = Vector()
    for vector in vectors:
        total += vector
    return total / len(vectors)


def _point_rows(points: Sequence[Sequence[float]]) -> np.ndarray:
    """Convert point coordinates into a NumPy row matrix."""

    return np.asarray(points, dtype=float)


def _evenly_spaced_subset(values: Sequence[T], max_count: int) -> list[T]:
    """Return a deterministic evenly spaced subset of a sequence."""

    if max_count <= 0:
        return []
    if len(values) <= max_count:
        return list(values)
    if max_count == 1:
        return [values[0]]
    last_index = len(values) - 1
    return [values[round(i * last_index / (max_count - 1))] for i in range(max_count)]


# Clustering and low-level geometry helpers
def _cluster_points(
    points: Sequence[Sequence[float]], eps: float, min_samples: int
) -> list[np.ndarray]:
    """Cluster points with DBSCAN and return one mask per cluster."""

    if len(points) < min_samples:
        return []
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit(_point_rows(points)).labels_
    return [np.asarray(labels == label) for label in sorted(set(labels)) if label != -1]


def _edge_key(edge) -> EdgeKey:
    """Create an order-independent key for an edge."""

    vertices = edge.vertices()
    ends = sorted(_rounded_vertex_key(vertex.center()) for vertex in vertices)
    return ends[0], ends[1]


def _face_key(face: Face) -> tuple[tuple[float, float, float], ...]:
    """Create an order-independent key for a face."""

    return tuple(
        sorted(_rounded_vertex_key(vertex.center()) for vertex in face.vertices())
    )


def _as_face(value: Any, context: str) -> Face:
    """Extract a Face from a build123d value or raise a descriptive error."""

    if isinstance(value, Face):
        return value
    face_method = getattr(value, "face", None)
    if callable(face_method):
        face = face_method()
        if isinstance(face, Face):
            return face
    raise RuntimeError(f"Expected Face while building {context}")


def _plane_basis(normal: Vector) -> tuple[Vector, Vector]:
    """Construct an orthonormal basis lying in a plane."""

    helper = Vector(1.0, 0.0, 0.0)
    if abs(helper.dot(normal)) > 0.9:
        helper = Vector(0.0, 1.0, 0.0)
    u = _normalized(normal.cross(helper))
    v = _normalized(normal.cross(u))
    return u, v


def _plane_point_distances(
    points: Sequence[Vector], plane_origin: Vector, plane_normal: Vector
) -> list[float]:
    """Measure point distances from a plane."""

    return [abs((point - plane_origin).dot(plane_normal)) for point in points]


def _pick_non_collinear_triplet(
    points: Sequence[Vector],
) -> tuple[Vector, Vector, Vector] | None:
    """Return the first non-collinear triplet of points, if any."""

    if len(points) < 3:
        return None
    for point_a, point_b, point_c in combinations(points, 3):
        if (point_b - point_a).cross(point_c - point_a).length > EPS:
            return point_a, point_b, point_c
    return None


def _cluster_unit_vectors(
    vectors: Sequence[Vector], eps: float, min_samples: int
) -> list[np.ndarray]:
    """Cluster unit vectors with cosine-distance DBSCAN."""

    if len(vectors) < min_samples:
        return []
    labels = (
        DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
        .fit(_vector_rows(vectors))
        .labels_
    )
    return [np.asarray(labels == label) for label in sorted(set(labels)) if label != -1]


def _circumradius_from_points(
    point_a: Vector, point_b: Vector, point_c: Vector
) -> float | None:
    """Return the circumradius of three non-collinear points."""

    side_a = (point_b - point_c).length
    side_b = (point_a - point_c).length
    side_c = (point_a - point_b).length
    area_twice = (point_b - point_a).cross(point_c - point_a).length
    if area_twice <= EPS:
        return None
    return (side_a * side_b * side_c) / (2.0 * area_twice)


def _unique_face_vertices(faces: Sequence[Face]) -> list[Vector]:
    """Collect unique face vertices using rounded coordinates."""

    vertices: dict[tuple[float, float, float], Vector] = {}
    for face in faces:
        for vertex in face.vertices():
            center = vertex.center()
            vertices.setdefault(_rounded_vertex_key(center), center)
    return list(vertices.values())


def _normalized(vector: Vector | Sequence[float]) -> Vector:
    """Return a normalized vector or raise for near-zero input."""

    unit = Vector(vector)
    if unit.length <= EPS:
        raise ValueError("Cannot normalize near-zero vector")
    return unit.normalized()


def _canonicalize_direction(direction: Vector | Sequence[float]) -> Vector:
    """Flip a direction to a stable canonical orientation."""

    unit = _normalized(direction)
    values = tuple(unit)
    max_index = max(range(3), key=lambda i: abs(values[i]))
    return unit if values[max_index] >= 0 else -unit


def _fit_plane_to_points(points: Sequence[Vector]) -> tuple[Vector, Vector]:
    """Fit a plane to points with singular value decomposition."""

    if len(points) < 3:
        raise ValueError("Need at least three points to fit a plane")
    centroid = _mean_vector(points)
    rows = np.asarray([tuple(point - centroid) for point in points], dtype=float)
    _u, _s, vh = np.linalg.svd(rows, full_matrices=False)
    normal = _canonicalize_direction(Vector(*vh[-1]))
    return centroid, normal


# Adjacency and grouping helpers
def _bfs_patch(
    mesh_index: MeshIndex,
    seed_index: int,
    allowed_indices: set[int],
    max_depth: int,
) -> list[int]:
    """Collect a local face patch with bounded breadth-first search."""

    mesh_index.ensure_adjacency()
    assert mesh_index.adjacent_face_indices is not None
    visited = {seed_index}
    frontier = [(seed_index, 0)]
    patch = []
    while frontier:
        face_index, depth = frontier.pop(0)
        patch.append(face_index)
        if depth >= max_depth:
            continue
        for neighbor_index in mesh_index.adjacent_face_indices[face_index]:
            if neighbor_index in visited or neighbor_index not in allowed_indices:
                continue
            visited.add(neighbor_index)
            frontier.append((neighbor_index, depth + 1))
    return patch


def _group_indices_by_area(
    mesh_index: MeshIndex,
    allowed_indices: set[int],
    tol_digits: int = 5,
) -> list[list[int]]:
    """Group face indices by approximately equal face area."""

    by_area: defaultdict[float, list[int]] = defaultdict(list)
    for face_index in allowed_indices:
        by_area[round(mesh_index.faces[face_index].area, tol_digits)].append(face_index)
    return sorted(by_area.values(), key=len, reverse=True)


def _indices_from_sewn_component(mesh_index: MeshIndex, component) -> list[int]:
    """Map a sewn component back to mesh face indices."""

    indices = []
    for face in component.faces():
        face_index = mesh_index.face_key_lookup.get(_face_key(face))
        if face_index is not None:
            indices.append(face_index)
    return sorted(set(indices))


def _build_face_edge_midpoint_adjacency(
    mesh_index: MeshIndex,
) -> dict[int, list[tuple[int, Vector]]]:
    """Build face adjacency keyed by shared edge midpoints."""

    edge_to_faces: defaultdict[EdgeKey, list[int]] = defaultdict(list)
    edge_midpoints: dict[EdgeKey, Vector] = {}

    for index, face in enumerate(mesh_index.faces):
        for edge in face.edges():
            edge_key = _edge_key(edge)
            edge_to_faces[edge_key].append(index)
            vertices = [vertex.center() for vertex in edge.vertices()]
            edge_midpoints[edge_key] = Vector(
                (vertices[0].X + vertices[1].X) / 2.0,
                (vertices[0].Y + vertices[1].Y) / 2.0,
                (vertices[0].Z + vertices[1].Z) / 2.0,
            )

    adjacency: dict[int, list[tuple[int, Vector]]] = {
        index: [] for index in range(len(mesh_index.faces))
    }
    for edge_key, face_indices in edge_to_faces.items():
        if len(face_indices) != 2:
            continue
        first, second = face_indices
        midpoint = edge_midpoints[edge_key]
        adjacency[first].append((second, midpoint))
        adjacency[second].append((first, midpoint))

    return {
        index: sorted(neighbors, key=lambda item: item[0])
        for index, neighbors in adjacency.items()
    }


# Primitive face builders
def build_plane_face(patch: PlanePatch) -> Face:
    """Create a planar Face from a fitted plane patch."""

    u_size = patch.u_max - patch.u_min
    v_size = patch.v_max - patch.v_min
    u_center = (patch.u_min + patch.u_max) / 2.0
    v_center = (patch.v_min + patch.v_max) / 2.0
    u_vec, _v_vec = _plane_basis(patch.normal)
    plane = Plane(origin=patch.origin, x_dir=u_vec, z_dir=patch.normal)
    return _as_face(
        plane * Pos(u_center, v_center, 0) * Rectangle(u_size, v_size),
        "plane primitive",
    )


def build_cylinder_face(patch: CylinderPatch, support_faces: Sequence[Face]) -> Face:
    """Create a cylindrical Face from a fitted cylinder patch."""

    vertices = _unique_face_vertices(support_faces)
    axis_values = [
        (vertex - patch.axis_point).dot(patch.axis_direction) for vertex in vertices
    ]
    radial_distances = []
    for vertex in vertices:
        offset = vertex - patch.axis_point
        radial = offset - patch.axis_direction * offset.dot(patch.axis_direction)
        if radial.length <= EPS:
            continue
        radial_distances.append(radial.length)
    axis_min = min(axis_values)
    axis_max = max(axis_values)
    radius = _median_scalar(radial_distances)
    cylinder_shape = Plane(
        origin=patch.axis_point + patch.axis_direction * axis_min,
        z_dir=patch.axis_direction,
    ) * Cylinder(radius, axis_max - axis_min, align=Align.NONE)
    cylinder_faces = getattr(cylinder_shape, "faces", None)
    if not callable(cylinder_faces):
        raise RuntimeError("Expected cylinder shape to provide faces()")
    filtered_faces = cylinder_faces().filter_by(GeomType.CYLINDER)
    if not filtered_faces or not isinstance(filtered_faces[0], Face):
        raise RuntimeError(
            "Expected cylindrical face while building cylinder primitive"
        )
    return filtered_faces[0] if patch.normal_sign > 0 else -filtered_faces[0]


def build_sphere_face(patch: SpherePatch, support_faces: Sequence[Face]) -> Face:
    """Create a spherical Face from a fitted sphere patch."""

    vertices = _unique_face_vertices(support_faces)
    radius = _median_scalar([(vertex - patch.center).length for vertex in vertices])
    return _as_face(Pos(*tuple(patch.center)) * Sphere(radius), "sphere primitive")


# Local signature and patch-growth helpers
def _relative_radius_spread(signature: tuple[float, ...]) -> float:
    """Measure radius spread relative to the midpoint value."""

    finite = [value for value in signature if np.isfinite(value)]
    if len(finite) < 3:
        return float("inf")
    low = finite[0]
    mid = finite[len(finite) // 2]
    high = finite[-1]
    if mid <= EPS:
        return float("inf")
    return (high - low) / mid


def _face_radius_signature(
    edge_adjacency: dict[int, list[tuple[int, Vector]]],
    mesh_index: MeshIndex,
    face_index: int,
    allowed_indices: set[int],
) -> tuple[float, ...]:
    """Estimate local radii implied by neighboring faces."""

    sample = mesh_index.face_samples[face_index]
    estimates: list[float] = []
    for neighbor_index, edge_midpoint in edge_adjacency[face_index]:
        if neighbor_index not in allowed_indices:
            continue
        neighbor = mesh_index.face_samples[neighbor_index]
        radius = _circumradius_from_points(
            sample.center,
            neighbor.center,
            edge_midpoint,
        )
        estimates.append(radius if radius is not None else float("inf"))
    return tuple(sorted(estimates))


def _connected_face_components(
    mesh_index: MeshIndex,
    face_indices: set[int],
) -> list[list[int]]:
    """Split a face set into connected components."""

    mesh_index.ensure_adjacency()
    assert mesh_index.adjacent_face_indices is not None
    remaining = set(face_indices)
    components: list[list[int]] = []

    while remaining:
        seed_index = remaining.pop()
        component = [seed_index]
        frontier = [seed_index]
        while frontier:
            face_index = frontier.pop()
            for neighbor_index in mesh_index.adjacent_face_indices[face_index]:
                if neighbor_index not in remaining:
                    continue
                remaining.remove(neighbor_index)
                component.append(neighbor_index)
                frontier.append(neighbor_index)
        components.append(sorted(component))

    return sorted(components, key=len, reverse=True)


def _sphere_like_face_components(
    mesh_index: MeshIndex,
    allowed_indices: set[int],
    similarity_tolerance: float = 1.0,
) -> list[list[int]]:
    """Return connected components whose signatures look spherical."""

    edge_adjacency = _build_face_edge_midpoint_adjacency(mesh_index)
    sphere_like_indices: set[int] = set()

    for face_index in allowed_indices:
        signature = _face_radius_signature(
            edge_adjacency,
            mesh_index,
            face_index,
            allowed_indices,
        )
        if not signature:
            continue
        if _relative_radius_spread(signature) <= similarity_tolerance:
            sphere_like_indices.add(face_index)

    return _connected_face_components(mesh_index, sphere_like_indices)


def _cylinder_face_error(
    sample: FaceSample, patch: CylinderPatch, shape_scale: float
) -> float | None:
    """Score how well a face sample matches a cylinder patch."""

    offset = sample.center - patch.axis_point
    radial = offset - patch.axis_direction * offset.dot(patch.axis_direction)
    if radial.length <= EPS:
        return None
    radius_error = abs(radial.length - patch.radius)
    normal_error = 1.0 - abs(radial.normalized().dot(sample.normal))
    radius_tolerance = max(shape_scale * 0.01, patch.radius * 0.02)
    if radius_error > radius_tolerance or normal_error > 0.03:
        return None
    return radius_error / max(radius_tolerance, EPS) + normal_error / 0.03


def _sphere_face_error(
    sample: FaceSample, patch: SpherePatch, shape_scale: float
) -> float | None:
    """Score how well a face sample matches a sphere patch."""

    radial = patch.center - sample.center
    if radial.length <= EPS:
        return None
    radius_error = abs(radial.length - patch.radius)
    normal_error = 1.0 - abs(radial.normalized().dot(sample.normal))
    radius_tolerance = max(shape_scale * 0.01, patch.radius * 0.02)
    if radius_error > radius_tolerance or normal_error > 0.03:
        return None
    return radius_error / max(radius_tolerance, EPS) + normal_error / 0.03


def _bounding_boxes_overlap(box1, box2, tolerance: float = 0.0) -> bool:
    """Return whether two axis-aligned bounding boxes overlap."""

    return not (
        box1.max.X < box2.min.X - tolerance
        or box2.max.X < box1.min.X - tolerance
        or box1.max.Y < box2.min.Y - tolerance
        or box2.max.Y < box1.min.Y - tolerance
        or box1.max.Z < box2.min.Z - tolerance
        or box2.max.Z < box1.min.Z - tolerance
    )


@overload
def grow_curved_patch(
    mesh_index: MeshIndex,
    patch: CylinderPatch,
    allowed_indices: set[int],
    shape_scale: float,
) -> CylinderPatch: ...


@overload
def grow_curved_patch(
    mesh_index: MeshIndex,
    patch: SpherePatch,
    allowed_indices: set[int],
    shape_scale: float,
) -> SpherePatch: ...


def grow_curved_patch(
    mesh_index: MeshIndex,
    patch: CylinderPatch | SpherePatch,
    allowed_indices: set[int],
    shape_scale: float,
) -> CylinderPatch | SpherePatch:
    """Grow a curved patch across adjacent compatible faces."""

    mesh_index.ensure_adjacency()
    assert mesh_index.adjacent_face_indices is not None
    claimed = set(patch.face_indices) & allowed_indices
    frontier = list(claimed)

    while frontier:
        face_index = frontier.pop()
        for neighbor_index in mesh_index.adjacent_face_indices[face_index]:
            if neighbor_index in claimed or neighbor_index not in allowed_indices:
                continue
            sample = mesh_index.face_samples[neighbor_index]
            score = (
                _cylinder_face_error(sample, patch, shape_scale)
                if isinstance(patch, CylinderPatch)
                else _sphere_face_error(sample, patch, shape_scale)
            )
            if score is None:
                continue
            claimed.add(neighbor_index)
            frontier.append(neighbor_index)

    claimed_samples = [mesh_index.face_samples[index] for index in sorted(claimed)]
    if isinstance(patch, CylinderPatch):
        radii = []
        residuals = []
        for sample in claimed_samples:
            offset = sample.center - patch.axis_point
            radial = offset - patch.axis_direction * offset.dot(patch.axis_direction)
            if radial.length <= EPS:
                continue
            radii.append(radial.length)
            residuals.append(1.0 - abs(radial.normalized().dot(sample.normal)))
        return CylinderPatch(
            kind="cylinder",
            face_indices=frozenset(claimed),
            axis_point=patch.axis_point,
            axis_direction=patch.axis_direction,
            radius=_mean_scalar(radii) if radii else patch.radius,
            normal_sign=patch.normal_sign,
            residual=_mean_scalar(residuals) if residuals else patch.residual,
        )

    radii = []
    residuals = []
    for sample in claimed_samples:
        radial = patch.center - sample.center
        if radial.length <= EPS:
            continue
        radii.append(radial.length)
        residuals.append(1.0 - abs(radial.normalized().dot(sample.normal)))
    return SpherePatch(
        kind="sphere",
        face_indices=frozenset(claimed),
        center=patch.center,
        radius=_mean_scalar(radii) if radii else patch.radius,
        residual=_mean_scalar(residuals) if residuals else patch.residual,
    )


# Plane detection
def _plane_like_face_components(
    mesh_index: MeshIndex,
    allowed_indices: set[int],
    normal_digits: int = 3,
) -> list[list[int]]:
    """Return connected components of approximately coplanar faces."""

    normal_groups: defaultdict[tuple[float, float, float], set[int]] = defaultdict(set)
    for face_index in allowed_indices:
        normal = _canonicalize_direction(mesh_index.face_samples[face_index].normal)
        normal_groups[tuple(round(value, normal_digits) for value in normal)].add(
            face_index
        )

    components: list[list[int]] = []
    for face_indices in normal_groups.values():
        components.extend(_connected_face_components(mesh_index, face_indices))
    return sorted(components, key=len, reverse=True)


def _detect_planes_from_clean_proxy(
    shape,
    mesh_index: MeshIndex,
    normal_tolerance: float = 1e-3,
    plane_tolerance_factor: float = 0.002,
    bbox_tolerance_factor: float = 0.002,
    inside_tolerance_factor: float = 0.002,
    min_proxy_edges: int = 4,
    min_proxy_area_ratio: float = 0.5,
) -> list[PlanePatch]:
    """Detect dominant planes from cleaned proxy faces."""

    shape_scale = shape.bounding_box().diagonal
    plane_tolerance = shape_scale * plane_tolerance_factor
    bbox_tolerance = shape_scale * bbox_tolerance_factor
    inside_tolerance = shape_scale * inside_tolerance_factor

    cleaned_shape = copy.deepcopy(shape).clean()
    proxy_faces = [
        face for face in cleaned_shape.faces() if len(face.edges()) >= min_proxy_edges
    ]
    if not proxy_faces:
        return []

    max_area = max(face.area for face in proxy_faces)
    proxy_faces = [
        face for face in proxy_faces if face.area >= max_area * min_proxy_area_ratio
    ]

    patches: list[PlanePatch] = []
    for proxy_face in proxy_faces:
        proxy_normal = _canonicalize_direction(proxy_face.normal_at())
        proxy_center = proxy_face.center()
        proxy_bbox = proxy_face.bounding_box()

        matched_indices = []
        distances = []
        for sample in mesh_index.face_samples:
            if 1.0 - abs(sample.normal.dot(proxy_normal)) > normal_tolerance:
                continue
            distance = abs((sample.center - proxy_center).dot(proxy_normal))
            if distance > plane_tolerance:
                continue
            if not _bounding_boxes_overlap(
                sample.face.bounding_box(), proxy_bbox, bbox_tolerance
            ):
                continue
            if not proxy_face.is_inside(sample.center, tolerance=inside_tolerance):
                continue
            matched_indices.append(sample.index)
            distances.append(distance)

        if len(matched_indices) < 2:
            continue

        support_faces = mesh_index.face_set(matched_indices)
        vertices = _unique_face_vertices(support_faces)
        u_vec, v_vec = _plane_basis(proxy_normal)
        u_values = [(vertex - proxy_center).dot(u_vec) for vertex in vertices]
        v_values = [(vertex - proxy_center).dot(v_vec) for vertex in vertices]
        patches.append(
            PlanePatch(
                kind="plane",
                face_indices=frozenset(matched_indices),
                origin=proxy_center,
                normal=proxy_normal,
                u_min=min(u_values),
                u_max=max(u_values),
                v_min=min(v_values),
                v_max=max(v_values),
                residual=_mean_scalar(distances),
            )
        )
    return patches


def _build_plane_patch(
    mesh_index: MeshIndex,
    face_indices: list[int],
    shape_scale: float,
    plane_tolerance_factor: float = 0.003,
    normal_tolerance: float = 0.01,
) -> PlanePatch | None:
    """Fit and validate a plane patch from candidate faces."""

    if len(face_indices) < 2:
        return None
    support_faces = mesh_index.face_set(face_indices)
    vertices = _unique_face_vertices(support_faces)
    if len(vertices) < 3:
        return None

    origin, normal = _fit_plane_to_points(vertices)
    normal = _canonicalize_direction(normal)
    distances = _plane_point_distances(vertices, origin, normal)
    plane_tolerance = shape_scale * plane_tolerance_factor
    if max(distances) > plane_tolerance:
        return None

    samples = [mesh_index.face_samples[index] for index in face_indices]
    normal_errors = [1.0 - abs(sample.normal.dot(normal)) for sample in samples]
    if normal_errors and max(normal_errors) > normal_tolerance:
        return None

    u_vec, v_vec = _plane_basis(normal)
    u_values = [(vertex - origin).dot(u_vec) for vertex in vertices]
    v_values = [(vertex - origin).dot(v_vec) for vertex in vertices]
    return PlanePatch(
        kind="plane",
        face_indices=frozenset(face_indices),
        origin=origin,
        normal=normal,
        u_min=min(u_values),
        u_max=max(u_values),
        v_min=min(v_values),
        v_max=max(v_values),
        residual=_mean_scalar(distances) if distances else 0.0,
    )


def _direction_angle_delta(direction_a: Vector, direction_b: Vector) -> float:
    """Return the unsigned angle between two directions."""

    dot = abs(
        _canonicalize_direction(direction_a).dot(_canonicalize_direction(direction_b))
    )
    return float(acos(min(1.0, max(-1.0, dot))))


def _perpendicular_axis_shift(
    point_a: Vector,
    direction_a: Vector,
    point_b: Vector,
    direction_b: Vector,
) -> float:
    """Measure the perpendicular separation between two axes."""

    average_direction = _canonicalize_direction(
        _mean_vector(
            [_canonicalize_direction(direction_a), _canonicalize_direction(direction_b)]
        )
    )
    delta = point_b - point_a
    perpendicular = delta - average_direction * delta.dot(average_direction)
    return perpendicular.length


def merge_equivalent_cylinders(
    mesh_index: MeshIndex,
    patches: Sequence[CylinderPatch],
    shape_scale: float,
    axis_angle_tolerance: float = 0.04,
    axis_shift_factor: float = 0.015,
    radius_ratio_tolerance: float = 0.12,
) -> list[CylinderPatch]:
    """Merge cylinder patches that describe the same cylinder."""

    groups: list[list[CylinderPatch]] = []
    for patch in patches:
        placed = False
        for group in groups:
            representative = group[0]
            if (
                _direction_angle_delta(
                    representative.axis_direction, patch.axis_direction
                )
                <= axis_angle_tolerance
                and _perpendicular_axis_shift(
                    representative.axis_point,
                    representative.axis_direction,
                    patch.axis_point,
                    patch.axis_direction,
                )
                <= shape_scale * axis_shift_factor
                and abs(representative.radius - patch.radius)
                / max(representative.radius, patch.radius, EPS)
                <= radius_ratio_tolerance
            ):
                group.append(patch)
                placed = True
                break
        if not placed:
            groups.append([patch])

    merged: list[CylinderPatch] = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue
        face_indices = frozenset().union(*(patch.face_indices for patch in group))
        samples = [mesh_index.face_samples[index] for index in sorted(face_indices)]
        axis_direction = _canonicalize_direction(
            _mean_vector([patch.axis_direction for patch in group])
        )
        axis_point = _mean_vector([patch.axis_point for patch in group])
        radii = []
        residuals = []
        for sample in samples:
            offset = sample.center - axis_point
            radial = offset - axis_direction * offset.dot(axis_direction)
            if radial.length <= EPS:
                continue
            radii.append(radial.length)
            residuals.append(1.0 - abs(radial.normalized().dot(sample.normal)))
        if not radii:
            continue
        merged.append(
            CylinderPatch(
                kind="cylinder",
                face_indices=face_indices,
                axis_point=axis_point,
                axis_direction=axis_direction,
                radius=_mean_scalar(radii),
                normal_sign=(
                    1
                    if sum(p.normal_sign * len(p.face_indices) for p in group) >= 0
                    else -1
                ),
                residual=(
                    _mean_scalar(residuals)
                    if residuals
                    else _mean_scalar([p.residual for p in group])
                ),
            )
        )
    return merged


def validate_bounded_cylinder(
    patch: CylinderPatch,
    support_faces: Sequence[Face],
    shape_scale: float,
    plane_tolerance_factor: float = 0.004,
    radius_tolerance_factor: float = 0.01,
    min_bin_fraction: float = 0.35,
    max_radius_std_ratio: float = 0.08,
    plane_parallel_tolerance: float = 0.02,
    end_radius_ratio_tolerance: float = 0.12,
) -> bool:
    """Validate that support faces form a bounded cylindrical patch."""

    vertices = _unique_face_vertices(support_faces)
    if len(vertices) < 6:
        return False

    radial_distances = []
    for vertex in vertices:
        offset = vertex - patch.axis_point
        radial = offset - patch.axis_direction * offset.dot(patch.axis_direction)
        if radial.length <= EPS:
            continue
        radial_distances.append(radial.length)
    if not radial_distances:
        return False
    radius_tolerance = max(shape_scale * radius_tolerance_factor, patch.radius * 0.02)
    radius_mean = _mean_scalar(radial_distances)
    radius_std = _std_scalar(radial_distances)
    if abs(radius_mean - patch.radius) > radius_tolerance:
        return False
    if radius_std / max(radius_mean, EPS) > max_radius_std_ratio:
        return False

    center = _mean_vector(vertices)
    axial_values = [(vertex - center).dot(patch.axis_direction) for vertex in vertices]
    negative_bin = [
        vertex for vertex, value in zip(vertices, axial_values) if value < 0
    ]
    positive_bin = [
        vertex for vertex, value in zip(vertices, axial_values) if value >= 0
    ]
    if len(negative_bin) < 3 or len(positive_bin) < 3:
        return False
    if (
        len(negative_bin) / len(vertices) < min_bin_fraction
        or len(positive_bin) / len(vertices) < min_bin_fraction
    ):
        return False

    plane_tolerance = shape_scale * plane_tolerance_factor
    end_planes: list[tuple[Vector, Vector]] = []
    end_radii: list[float] = []
    for point_bin in [negative_bin, positive_bin]:
        plane_origin, plane_normal = _fit_plane_to_points(point_bin)
        distances = _plane_point_distances(point_bin, plane_origin, plane_normal)
        if (
            max(distances) > plane_tolerance
            or _mean_scalar(distances) > plane_tolerance / 2.0
        ):
            return False
        end_planes.append((plane_origin, plane_normal))

        triplet = _pick_non_collinear_triplet(point_bin)
        if triplet is None:
            return False
        end_radius = _circumradius_from_points(*triplet)
        if end_radius is None or end_radius <= EPS:
            return False
        end_radii.append(end_radius)

    if (
        abs(abs(end_planes[0][1].dot(end_planes[1][1])) - 1.0)
        > plane_parallel_tolerance
    ):
        return False

    mean_end_radius = _mean_scalar(end_radii)
    if mean_end_radius <= EPS:
        return False
    if (
        max(abs(radius - mean_end_radius) for radius in end_radii) / mean_end_radius
        > end_radius_ratio_tolerance
    ):
        return False

    if (
        max(abs(radius - mean_end_radius) for radius in radial_distances)
        / mean_end_radius
        > 0.2
    ):
        return False
    return True


def fit_local_cylinder(
    samples: Sequence[FaceSample],
    shape_scale: float,
    max_pair_face_count: int = 64,
    max_intersection_face_count: int = 64,
) -> CylinderPatch | None:
    """Fit a cylinder patch to local face samples."""

    axis_samples = _evenly_spaced_subset(samples, max_pair_face_count)
    records: list[tuple[tuple[int, int], Vector]] = []
    for sample_a, sample_b in combinations(axis_samples, 2):
        cross = sample_a.normal.cross(sample_b.normal)
        if cross.length <= 1e-3:
            continue
        records.append(
            ((sample_a.index, sample_b.index), _canonicalize_direction(cross))
        )
    if not records:
        return None

    masks = _cluster_unit_vectors(
        [direction for _, direction in records], eps=0.03, min_samples=4
    )
    if not masks:
        return None

    best_mask = max(masks, key=lambda mask: int(np.count_nonzero(mask)))
    cluster_records = [record for record, keep in zip(records, best_mask) if keep]
    face_indices = sorted(
        {index for indices, _ in cluster_records for index in indices}
    )
    if len(face_indices) < 4:
        return None

    face_group = [sample for sample in samples if sample.index in face_indices]
    axis_direction = _canonicalize_direction(
        _mean_vector([direction for _, direction in cluster_records])
    )
    u_vec, v_vec = _plane_basis(axis_direction)

    center_samples = _evenly_spaced_subset(face_group, max_intersection_face_count)
    points_2d = []
    normals_2d = []
    axis_coords = []
    for sample in center_samples:
        projected_normal = (sample.normal.dot(u_vec), sample.normal.dot(v_vec))
        projected_length = sqrt(projected_normal[0] ** 2 + projected_normal[1] ** 2)
        if projected_length <= 1e-3:
            continue
        points_2d.append((sample.center.dot(u_vec), sample.center.dot(v_vec)))
        normals_2d.append(
            (
                projected_normal[0] / projected_length,
                projected_normal[1] / projected_length,
            )
        )
        axis_coords.append(sample.center.dot(axis_direction))
    if len(points_2d) < 4:
        return None

    intersections_2d = [
        intersection
        for (point_a, direction_a), (point_b, direction_b) in combinations(
            zip(points_2d, normals_2d), 2
        )
        if (
            intersection := _intersect_2d_lines(
                point_a, direction_a, point_b, direction_b
            )
        )
        is not None
    ]
    if len(intersections_2d) < 4:
        return None

    point_masks = _cluster_points(
        intersections_2d, eps=shape_scale * 0.03, min_samples=4
    )
    if not point_masks:
        return None
    best_point_mask = max(point_masks, key=lambda mask: int(np.count_nonzero(mask)))
    best_points = [
        point for point, keep in zip(intersections_2d, best_point_mask) if keep
    ]
    center_2d = (
        _mean_scalar([point[0] for point in best_points]),
        _mean_scalar([point[1] for point in best_points]),
    )
    axis_point = (
        u_vec * center_2d[0]
        + v_vec * center_2d[1]
        + axis_direction * _mean_scalar(axis_coords)
    )

    radii = []
    residuals = []
    signed_alignments = []
    for sample in face_group:
        offset = sample.center - axis_point
        radial = offset - axis_direction * offset.dot(axis_direction)
        if radial.length <= EPS:
            continue
        radial_direction = radial.normalized()
        radii.append(radial.length)
        signed_alignment = radial_direction.dot(sample.normal)
        signed_alignments.append(signed_alignment)
        residuals.append(1.0 - abs(signed_alignment))
    if not radii:
        return None
    radius = _mean_scalar(radii)
    if radius <= EPS or radius > shape_scale:
        return None
    radius_std = _std_scalar(radii)
    residual = _mean_scalar(residuals) if residuals else 0.0
    if radius_std / max(radius, EPS) > 0.15 or residual > 0.05:
        return None
    return CylinderPatch(
        kind="cylinder",
        face_indices=frozenset(face_indices),
        axis_point=axis_point,
        axis_direction=axis_direction,
        radius=radius,
        normal_sign=1 if _mean_scalar(signed_alignments) >= 0 else -1,
        residual=residual,
    )


def _intersect_2d_lines(
    point_a: tuple[float, float],
    direction_a: tuple[float, float],
    point_b: tuple[float, float],
    direction_b: tuple[float, float],
) -> tuple[float, float] | None:
    """Intersect two 2D lines expressed as point-direction pairs."""

    determinant = direction_b[0] * direction_a[1] - direction_a[0] * direction_b[1]
    if abs(determinant) <= EPS:
        return None
    delta_x = point_b[0] - point_a[0]
    delta_y = point_b[1] - point_a[1]
    scale_a = (direction_b[0] * delta_y - direction_b[1] * delta_x) / determinant
    return (
        point_a[0] + scale_a * direction_a[0],
        point_a[1] + scale_a * direction_a[1],
    )


def detect_planes(
    mesh,
    mesh_index: MeshIndex,
    normal_digits: int = 3,
    plane_tolerance_factor: float = 0.003,
    min_component_size: int = 2,
    min_two_face_area_factor: float = 0.05,
) -> list[PlanePatch]:
    """Detect planar regions in a mesh."""

    shape_scale = mesh.bounding_box().diagonal
    plane_patches = _detect_planes_from_clean_proxy(mesh, mesh_index)
    claimed = (
        set().union(*(patch.face_indices for patch in plane_patches))
        if plane_patches
        else set()
    )
    remaining = set(range(len(mesh_index.faces))) - claimed

    for component_indices in _plane_like_face_components(
        mesh_index,
        remaining,
        normal_digits=normal_digits,
    ):
        component_indices = [
            face_index for face_index in component_indices if face_index in remaining
        ]
        if len(component_indices) < min_component_size:
            continue
        if len(component_indices) == 2 and (
            sum(mesh_index.faces[face_index].area for face_index in component_indices)
            < (shape_scale**2) * min_two_face_area_factor
        ):
            continue
        patch = _build_plane_patch(mesh_index, component_indices, shape_scale)
        if patch is None:
            continue
        plane_patches.append(patch)
        remaining.difference_update(patch.face_indices)

    return plane_patches


# Cylinder detection
def _cylinder_like_face_indices(
    mesh_index: MeshIndex,
    allowed_indices: set[int],
    pair_similarity_tolerance: float = 0.35,
    anisotropy_ratio_threshold: float = 1.5,
) -> set[int]:
    """Broadly classify which faces are plausible cylinder candidates."""

    edge_adjacency = _build_face_edge_midpoint_adjacency(mesh_index)
    cylinder_like_indices: set[int] = set()

    for face_index in allowed_indices:
        signature = _face_radius_signature(
            edge_adjacency,
            mesh_index,
            face_index,
            allowed_indices,
        )
        finite = [value for value in signature if np.isfinite(value)]
        if len(finite) < 2:
            continue
        if len(finite) == 2:
            low, high = finite[0], finite[1]
            if low <= EPS:
                continue
            anisotropy = high / low if high > EPS else 0.0
            if anisotropy >= anisotropy_ratio_threshold:
                cylinder_like_indices.add(face_index)
            continue
        low, mid, high = finite[0], finite[1], finite[2]
        if low <= EPS or mid <= EPS:
            continue
        pair_similarity = abs(mid - low) / mid
        anisotropy = high / mid if high > EPS else 0.0
        if (
            pair_similarity <= pair_similarity_tolerance
            and anisotropy >= anisotropy_ratio_threshold
        ):
            cylinder_like_indices.add(face_index)
    return cylinder_like_indices


def fit_local_sphere(
    samples: list[FaceSample],
    shape_scale: float,
    radius_std_ratio_limit: float = 0.2,
    normal_error_limit: float = 0.08,
) -> SpherePatch | None:
    """Fit a sphere patch to local face samples."""

    if len(samples) < 4:
        return None

    rows = []
    rhs = []
    for sample in samples:
        x, y, z = tuple(sample.center)
        rows.append([x, y, z, 1.0])
        rhs.append(-(x * x + y * y + z * z))

    coeffs, _residuals, rank, _singular = np.linalg.lstsq(
        np.asarray(rows, dtype=float),
        np.asarray(rhs, dtype=float),
        rcond=None,
    )
    if rank < 4:
        return None

    a, b, c, d = coeffs
    center = Vector(-a / 2.0, -b / 2.0, -c / 2.0)
    radius_sq = center.dot(center) - d
    if radius_sq <= EPS:
        return None

    radii = []
    normal_errors = []
    for sample in samples:
        radial = center - sample.center
        radial_length = radial.length
        if radial_length <= EPS:
            continue
        radii.append(radial_length)
        normal_errors.append(1.0 - abs(radial.normalized().dot(sample.normal)))

    if len(radii) < 4:
        return None

    radius = sum(radii) / len(radii)
    if radius <= EPS or radius > shape_scale:
        return None

    radius_std = float(np.std(radii))
    normal_error = sum(normal_errors) / len(normal_errors) if normal_errors else 0.0
    residual = sum(abs(value - radius) for value in radii) / len(radii)

    if radius_std / max(radius, EPS) > radius_std_ratio_limit:
        return None
    if normal_error > normal_error_limit:
        return None

    return SpherePatch(
        kind="sphere",
        face_indices=frozenset(sample.index for sample in samples),
        center=center,
        radius=radius,
        residual=residual,
    )


def _cylinder_patch_looks_spherical(
    samples: list[FaceSample],
    cylinder_patch: CylinderPatch,
    shape_scale: float,
    residual_factor: float = 0.35,
) -> bool:
    """Reject cylinders that are better explained by a sphere fit."""

    sphere_patch = fit_local_sphere(samples, shape_scale)
    if sphere_patch is None:
        return False
    return sphere_patch.residual <= cylinder_patch.residual * residual_factor


def _finalize_cylinder_patch(
    mesh_index: MeshIndex,
    patch: CylinderPatch,
    remaining: set[int],
    shape_scale: float,
    min_component_size: int,
    require_bounded_validation: bool,
) -> CylinderPatch | None:
    """Grow, refit, and validate a cylinder patch candidate."""

    grown_patch = grow_curved_patch(
        mesh_index,
        patch,
        remaining,
        shape_scale,
    )
    if len(grown_patch.face_indices) < min_component_size:
        return None

    grown_samples = [
        mesh_index.face_samples[index] for index in sorted(grown_patch.face_indices)
    ]
    refit_patch = fit_local_cylinder(grown_samples, shape_scale)
    if refit_patch is not None:
        grown_patch = grow_curved_patch(
            mesh_index,
            refit_patch,
            remaining,
            shape_scale,
        )
        if len(grown_patch.face_indices) < min_component_size:
            return None
        grown_samples = [
            mesh_index.face_samples[index] for index in sorted(grown_patch.face_indices)
        ]

    if require_bounded_validation:
        support_faces = mesh_index.face_set(sorted(grown_patch.face_indices))
        if not validate_bounded_cylinder(grown_patch, support_faces, shape_scale):
            return None
    elif _cylinder_patch_looks_spherical(grown_samples, grown_patch, shape_scale):
        return None

    return CylinderPatch(
        kind="cylinder",
        face_indices=frozenset(grown_patch.face_indices),
        axis_point=grown_patch.axis_point,
        axis_direction=grown_patch.axis_direction,
        radius=grown_patch.radius,
        normal_sign=grown_patch.normal_sign,
        residual=grown_patch.residual,
    )


def detect_cylinders(
    mesh,
    mesh_index: MeshIndex,
    blocked_indices: set[int],
    area_tol_digits: int = 5,
    pair_similarity_tolerance: float = 0.35,
    anisotropy_ratio_threshold: float = 1.5,
    local_seed_depth: int = 2,
    min_component_size: int = 4,
) -> list[CylinderPatch]:
    """Detect cylindrical regions in a mesh."""

    remaining = set(range(len(mesh_index.faces))) - blocked_indices
    shape_scale = mesh.bounding_box().diagonal
    patches: list[CylinderPatch] = []

    for area_group in _group_indices_by_area(
        mesh_index, remaining, tol_digits=area_tol_digits
    ):
        group_faces = mesh_index.face_set(area_group)
        for component in Face.sew_faces(group_faces):
            component_indices = [
                face_index
                for face_index in _indices_from_sewn_component(mesh_index, component)
                if face_index in remaining
            ]
            if len(component_indices) < min_component_size:
                continue
            component_samples = [
                mesh_index.face_samples[index] for index in component_indices
            ]
            patch = fit_local_cylinder(component_samples, shape_scale)
            if patch is None:
                continue
            finalized_patch = _finalize_cylinder_patch(
                mesh_index,
                patch,
                remaining,
                shape_scale,
                min_component_size,
                require_bounded_validation=True,
            )
            if finalized_patch is None:
                continue
            patches.append(finalized_patch)
            remaining.difference_update(finalized_patch.face_indices)

    tried_seed_indices: set[int] = set()
    clfi = sorted(
        _cylinder_like_face_indices(
            mesh_index,
            remaining,
            pair_similarity_tolerance=pair_similarity_tolerance,
            anisotropy_ratio_threshold=anisotropy_ratio_threshold,
        )
    )
    for seed_index in clfi:
        if seed_index not in remaining or seed_index in tried_seed_indices:
            continue
        tried_seed_indices.add(seed_index)
        local_indices = _bfs_patch(
            mesh_index,
            seed_index,
            remaining,
            local_seed_depth,
        )
        if len(local_indices) < min_component_size:
            continue
        local_samples = [mesh_index.face_samples[index] for index in local_indices]
        patch = fit_local_cylinder(local_samples, shape_scale)
        if patch is None:
            continue
        finalized_patch = _finalize_cylinder_patch(
            mesh_index,
            patch,
            remaining,
            shape_scale,
            min_component_size,
            require_bounded_validation=False,
        )
        if finalized_patch is None:
            continue
        patches.append(finalized_patch)
        remaining.difference_update(finalized_patch.face_indices)

    return merge_equivalent_cylinders(mesh_index, patches, shape_scale)


# Sphere detection
def suppress_duplicate_spheres(
    patches: Sequence[SpherePatch],
    center_tolerance: float,
    radius_ratio_tolerance: float = 0.1,
    overlap_ratio_tolerance: float = 0.5,
) -> list[SpherePatch]:
    """Remove overlapping sphere detections that describe the same surface."""

    kept: list[SpherePatch] = []
    for patch in sorted(patches, key=lambda p: (p.residual, -len(p.face_indices))):
        duplicate = False
        for kept_patch in kept:
            center_shift = (patch.center - kept_patch.center).length
            radius_delta = abs(patch.radius - kept_patch.radius) / max(
                patch.radius, kept_patch.radius, EPS
            )
            overlap = len(patch.face_indices & kept_patch.face_indices) / max(
                min(len(patch.face_indices), len(kept_patch.face_indices)),
                1,
            )
            if (
                center_shift <= center_tolerance
                and radius_delta <= radius_ratio_tolerance
                and overlap >= overlap_ratio_tolerance
            ):
                duplicate = True
                break
        if not duplicate:
            kept.append(patch)
    return kept


def detect_spheres(
    mesh,
    mesh_index: MeshIndex,
    blocked_indices: set[int],
    similarity_tolerance: float = 0.2,
    min_component_size: int = 6,
) -> list[SpherePatch]:
    """Detect spherical regions in a mesh."""

    remaining = set(range(len(mesh_index.faces))) - blocked_indices
    shape_scale = mesh.bounding_box().diagonal
    patches: list[SpherePatch] = []

    for radius_group in _sphere_like_face_components(
        mesh_index,
        remaining,
        similarity_tolerance=similarity_tolerance,
    ):
        group_faces = mesh_index.face_set(radius_group)
        for component in Face.sew_faces(group_faces):
            component_indices = [
                face_index
                for face_index in _indices_from_sewn_component(mesh_index, component)
                if face_index in remaining
            ]
            if len(component_indices) < min_component_size:
                continue
            component_samples = [
                mesh_index.face_samples[index] for index in component_indices
            ]
            patch = fit_local_sphere(component_samples, shape_scale)
            if patch is None:
                continue
            grown_patch = grow_curved_patch(
                mesh_index,
                patch,
                remaining,
                shape_scale,
            )
            if len(grown_patch.face_indices) < min_component_size:
                continue
            patches.append(
                SpherePatch(
                    kind="sphere",
                    face_indices=frozenset(grown_patch.face_indices),
                    center=grown_patch.center,
                    radius=grown_patch.radius,
                    residual=grown_patch.residual,
                )
            )
            remaining.difference_update(grown_patch.face_indices)

    return suppress_duplicate_spheres(
        patches,
        center_tolerance=shape_scale * 0.03,
    )


# Shape to build123d code conversion
TOLERANCE = 1e-4


def _offset(base: str, val: float) -> str:
    """Format a plane offset expression for generated code."""

    return f"{base} * " if abs(val) < TOLERANCE else f"{base}.offset({val:0.6g}) * "


def _pos(a: float, b: float) -> str:
    """Format an in-plane translation expression for generated code."""

    return (
        ""
        if (abs(a) < TOLERANCE and abs(b) < TOLERANCE)
        else f"Pos({a:0.6g}, {b:0.6g}) * "
    )


# All axis-aligned plane configs:
# (z_dir_vec, x_dir_vec, plane_name, offset_sign, offset_coord, pos_coords)
# offset_coord and pos_coords are lambdas over (x, y, z)
_PLANE_CONFIGS = [
    (
        Vector(0, 0, 1),
        Vector(1, 0, 0),
        "Plane.XY",
        1,
        lambda x, y, z: z,
        lambda x, y, z: (x, y),
    ),
    (
        Vector(0, 0, -1),
        Vector(0, 1, 0),
        "Plane.YX",
        -1,
        lambda x, y, z: z,
        lambda x, y, z: (y, x),
    ),
    (
        Vector(0, 1, 0),
        Vector(0, 0, 1),
        "Plane.ZX",
        1,
        lambda x, y, z: y,
        lambda x, y, z: (z, x),
    ),
    (
        Vector(0, -1, 0),
        Vector(1, 0, 0),
        "Plane.XZ",
        -1,
        lambda x, y, z: y,
        lambda x, y, z: (x, z),
    ),
    (
        Vector(1, 0, 0),
        Vector(0, 1, 0),
        "Plane.YZ",
        1,
        lambda x, y, z: x,
        lambda x, y, z: (y, z),
    ),
    (
        Vector(-1, 0, 0),
        Vector(0, 0, 1),
        "Plane.ZY",
        -1,
        lambda x, y, z: x,
        lambda x, y, z: (z, y),
    ),
]


def plane_sort_key(s: str) -> tuple:
    """Extract a stable sort key from generated plane-based code."""

    # Extract the plane/location name (e.g. "Plane.XY", "Plane.ZX", "Location")
    m = re.match(r"(Plane\.\w+|Location)", s)
    name = m.group(1) if m else "ZZZ"  # unknowns sort last

    # Extract numeric offset if present, e.g. Plane.XY.offset(-3.5) → -3.5
    offset_m = re.search(r"\.offset\(([^)]+)\)", s)
    offset = float(offset_m.group(1)) if offset_m else 0.0

    return (name, offset)


def shapes_to_code(primitives: Iterable[Shape]) -> list[str]:
    """Convert detected primitive faces into build123d code strings."""

    code_lines: list[str] = []
    for primitive in primitives:
        match primitive.geom_type:
            case GeomType.PLANE:

                pln = Plane(primitive)
                z_dir = pln.z_dir

                # Find matching config (or fall back to None)
                cfg = next(
                    (c for c in _PLANE_CONFIGS if z_dir.dot(c[0]) > 1 - TOLERANCE), None
                )

                if cfg is not None:
                    z_vec, x_vec, pln_name, sign, offset_fn, pos_fn = cfg
                    pln = Plane(pln.origin, x_dir=x_vec, z_dir=z_vec)

                center_oriented_rect = pln.to_local_coords(primitive)
                local_origin = (
                    center_oriented_rect.vertices()
                    .group_by(Axis.X)[0]
                    .sort_by(Axis.Y)[0]
                )
                local_origin = Vertex(local_origin.X, local_origin.Y, 0)
                global_origin = pln.from_local_coords(local_origin)
                shifted_plane = pln.shift_origin(global_origin)
                if not isinstance(shifted_plane, Plane):
                    raise RuntimeError("Expected Plane.shift_origin() to return Plane")
                pln = shifted_plane
                bbox = center_oriented_rect.bounding_box()

                w, height = bbox.size.X, bbox.size.Y
                rect = _as_face(
                    pln * Rectangle(w, height, align=Align.MIN), "planar rectangle"
                )
                common = rect.intersect(primitive)
                if not common or not isinstance(common[0], Face):
                    code_lines.append("Error in generating planar rectangle")
                    continue
                    # raise RuntimeError("Error in generating planar rectangle")
                if abs(common[0].area - primitive.area) > TOLERANCE:
                    height, w = w, height

                x, y, z = (round(d, TOL_DIGITS) for d in pln.origin)

                if cfg is not None:
                    pln_str = _offset(pln_name, sign * offset_fn(x, y, z))
                    pos_str = _pos(*pos_fn(x, y, z))
                else:
                    pln_str = ""
                    pos_str = f"Location{Location(pln):0.6g} * "

                rect_str = (
                    pln_str
                    + pos_str
                    + f"Rectangle({w:0.6g}, {height:0.6g}, align=Align.MIN)"
                )
                code_lines.append(rect_str)

            case GeomType.CYLINDER:
                pln = Plane(primitive.axis_of_rotation)
                z_dir = pln.z_dir
                # Find matching config (or fall back to None)
                cfg = next(
                    (c for c in _PLANE_CONFIGS if z_dir.dot(c[0]) > 1 - TOLERANCE), None
                )
                if cfg is not None:
                    z_vec, x_vec, pln_name, sign, offset_fn, pos_fn = cfg
                    pln = Plane(pln.origin, x_dir=x_vec, z_dir=z_vec)

                bbox = primitive.bounding_box()
                local_cyl = pln.to_local_coords(primitive)
                height = local_cyl.bounding_box().size.Z
                x, y, z = (round(d, TOL_DIGITS) for d in pln.origin)
                if cfg is not None:
                    pln_str = _offset(pln_name, sign * offset_fn(x, y, z))
                    pos_str = _pos(*pos_fn(x, y, z))
                else:
                    pln_str = f"Location{primitive.location:0.6g} * "
                    pos_str = ""
                cylinder_str = (
                    pln_str
                    + pos_str
                    + f"Face.extrude(Circle({primitive.radius:0.6g}).edge(), (0, 0, {height:0.6g}))"
                )
                code_lines.append(cylinder_str)

            case GeomType.SPHERE:
                sphere_str = (
                    f"Pos({primitive.position:0.6g}) * "
                    f"Sphere({primitive.radius:0.6g}).faces().filter_by(GeomType.SPHERE)[0]"
                )
                code_lines.append(sphere_str)

    return code_lines


# High-level pipeline
def detect_primitives(
    mesh: Shape,
) -> tuple[ShapeList[Face], ShapeList[Face], list[str]]:
    """Detect analytic primitives in a mesh and return faces, leftovers, and code.

    This is the user-facing entry point for STL-to-BREP reconstruction. The
    mesh is indexed first so face geometry and adjacency can be reused
    throughout the pipeline.

    Detection proceeds in stages:
    1. Planes are found first from cleaned proxy faces and coplanar connected
       components.
    2. Spheres are found next from broad radius-signature classification,
       connected or sewn regions, local sphere fitting, and region growth.
    3. Cylinders are detected last from area-grouped sewn regions and local
       cylinder seeds, then grown, refit, and validated.

    Each accepted patch is converted into a build123d Face, unmatched mesh
    faces are returned as leftovers, and the generated code strings are sorted
    in the same order as the returned primitives.
    """

    mesh_index = MeshIndex.from_shape(mesh)
    # shape_scale = mesh.bounding_box().diagonal

    plane_patches = detect_planes(mesh, mesh_index)
    plane_indices = (
        set().union(*(patch.face_indices for patch in plane_patches))
        if plane_patches
        else set()
    )

    sphere_patches = detect_spheres(mesh, mesh_index, plane_indices)
    sphere_indices = (
        set().union(*(patch.face_indices for patch in sphere_patches))
        if sphere_patches
        else set()
    )

    cylinder_patches = detect_cylinders(
        mesh,
        mesh_index,
        plane_indices | sphere_indices,
    )
    # cylinder_indices = (
    #     set().union(*(patch.face_indices for patch in cylinder_patches))
    #     if cylinder_patches
    #     else set()
    # )

    patches: list[DetectedPatch] = [*plane_patches, *cylinder_patches, *sphere_patches]

    # primitives: list[tuple[Face, Shell]] = []
    primitives: list[Face] = []
    claimed: set[int] = set()
    for patch in patches:
        support_faces = mesh_index.face_set(sorted(patch.face_indices))
        claimed.update(patch.face_indices)
        # try:
        #     support_shell = Shell(support_faces)
        # except TypeError:
        #     support_shell = Shell()
        if patch.kind == "plane":
            primitive_face = build_plane_face(patch)
        elif patch.kind == "cylinder":
            primitive_face = build_cylinder_face(patch, support_faces)
        else:
            primitive_face = build_sphere_face(patch, support_faces)
        primitives.append(primitive_face)

    leftovers = mesh_index.face_set(sorted(set(range(len(mesh_index.faces))) - claimed))

    code_lines = shapes_to_code(primitives)
    primitive_code_pairs = sorted(
        zip(primitives, code_lines),
        key=lambda item: plane_sort_key(item[1]),
    )
    if primitive_code_pairs:
        primitives, code_lines = map(list, zip(*primitive_code_pairs))
    else:
        primitives, code_lines = [], []

    # Add instance variables to the generated code
    if code_lines:
        num_lines = len(code_lines)
        num_digits = ceil(log10(num_lines))
        SHAPE_KEYS = [("Rectangle", "r"), ("Circle", "c"), ("Sphere", "s")]
        for i in range(num_lines):
            code_type = next(
                (key for label, key in SHAPE_KEYS if label in code_lines[i]), None
            )
            code_lines[i] = f"{code_type}{i:0{num_digits}d} = {code_lines[i]}"

    return ShapeList(primitives), ShapeList(leftovers), code_lines
