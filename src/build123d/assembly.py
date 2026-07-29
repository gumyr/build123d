"""
Persistent assembly mates and mate relations.

This module models assembly intent independently from the one-shot positioning
performed by :mod:`build123d.joints`.  Mates remain attached to an ``Assembly``
and are solved simultaneously whenever ``Assembly.solve`` is called.

The mate coordinate system follows Onshape's convention: Z is the primary axis
and X is the secondary axis.  Linear values use build123d model units and
angular values use degrees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import acos, degrees, inf, pi
from typing import ClassVar, Iterable, Mapping, Sequence

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.gp import gp_Quaternion, gp_Trsf, gp_Vec
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as SciPyRotation
from typing_extensions import Self

from build123d.build_enums import GeomType
from build123d.geometry import Location, Vector
from build123d.joints import RigidJoint
from build123d.topology import Compound, Edge, Face, Shape, Vertex
from build123d.topology.shape_core import _make_topods_compound_from_shapes


class MateSolveError(RuntimeError):
    """Raised when an assembly's active mate system cannot be satisfied."""


class MateDOF(str, Enum):
    """Degrees of freedom expressed in a mate connector coordinate system."""

    TX = "tx"
    TY = "ty"
    TZ = "tz"
    RX = "rx"
    RY = "ry"
    RZ = "rz"
    SWING = "swing"

    @classmethod
    def coerce(cls, value: MateDOF | str) -> MateDOF:
        """Convert a string or enum member into a ``MateDOF``."""

        return value if isinstance(value, cls) else cls(value.lower())


@dataclass(frozen=True)
class MateLimit:
    """Optional minimum and maximum values for one mate degree of freedom."""

    minimum: float = -inf
    maximum: float = inf

    def __post_init__(self):
        if self.minimum > self.maximum:
            raise ValueError("Mate limit minimum must not exceed maximum")

    def contains(self, value: float) -> bool:
        """Return whether ``value`` lies inside this limit."""

        return self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class MateOffset:
    """Fixed transform applied from the first mate connector to the second."""

    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)


class MateConnector(RigidJoint):
    """An oriented local coordinate system used to define assembly mates.

    ``MateConnector`` intentionally derives from ``RigidJoint`` so existing
    joint storage, copying, builder transfer, and parent rebinding continue to
    work.  Existing ``RigidJoint`` instances may also be supplied to mates.
    """


class _PoseMap(dict[object, np.ndarray]):
    """Identity-keyed component pose lookup accepting Shape instances."""

    def __getitem__(self, key):
        return super().__getitem__(id(key) if isinstance(key, Shape) else key)


def _location_matrix(location: Location) -> np.ndarray:
    """Convert a build123d ``Location`` to a homogeneous matrix."""

    transform = location.wrapped.Transformation()
    result = np.eye(4)
    for row in range(1, 4):
        for column in range(1, 4):
            result[row - 1, column - 1] = transform.Value(row, column)
        result[row - 1, 3] = transform.Value(row, 4)
    return result


def _matrix_location(matrix: np.ndarray) -> Location:
    """Convert a homogeneous matrix to a build123d ``Location``."""

    transform = gp_Trsf()
    rotation = SciPyRotation.from_matrix(matrix[:3, :3]).as_quat()
    transform.SetRotation(
        gp_Quaternion(
            float(rotation[0]),
            float(rotation[1]),
            float(rotation[2]),
            float(rotation[3]),
        )
    )
    transform.SetTranslationPart(
        gp_Vec(
            float(matrix[0, 3]),
            float(matrix[1, 3]),
            float(matrix[2, 3]),
        )
    )
    return Location(transform)


def _matrix_pose(matrix: np.ndarray) -> np.ndarray:
    """Convert a homogeneous matrix to translation plus rotation-vector pose."""

    return np.concatenate(
        (matrix[:3, 3], SciPyRotation.from_matrix(matrix[:3, :3]).as_rotvec())
    )


def _pose_matrix(pose: Sequence[float] | np.ndarray) -> np.ndarray:
    """Convert translation plus rotation-vector pose to a homogeneous matrix."""

    result = np.eye(4)
    result[:3, 3] = pose[:3]
    result[:3, :3] = SciPyRotation.from_rotvec(pose[3:]).as_matrix()
    return result


def _wrap_radians(value: float) -> float:
    """Wrap an angle to the interval [-pi, pi)."""

    return (value + pi) % (2 * pi) - pi


def _vector_tuple(vector: Vector) -> np.ndarray:
    """Convert a build123d vector into a NumPy vector."""

    return np.array((vector.X, vector.Y, vector.Z), dtype=float)


def _normalized(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm <= 1e-15:
        raise ValueError("Cannot normalize a zero-length vector")
    return vector / norm


def _coerce_limits(
    limits: Mapping[MateDOF | str, MateLimit | tuple[float, float]] | None,
) -> dict[MateDOF, MateLimit]:
    result: dict[MateDOF, MateLimit] = {}
    for dof, value in (limits or {}).items():
        key = MateDOF.coerce(dof)
        result[key] = value if isinstance(value, MateLimit) else MateLimit(*value)
    return result


class Mate:
    """Base class for persistent connector-based mates."""

    free_dofs: ClassVar[frozenset[MateDOF]] = frozenset()
    offset_translation_dofs: ClassVar[frozenset[MateDOF]] = frozenset()
    supports_rotation_offset: ClassVar[bool] = False
    limit_dofs: ClassVar[frozenset[MateDOF]] = frozenset()
    supports_values: ClassVar[bool] = True

    def __init__(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        *,
        offset: MateOffset | None = None,
        limits: Mapping[MateDOF | str, MateLimit | tuple[float, float]] | None = None,
        flip_primary: bool = False,
        reorient_secondary: int = 0,
        suppressed: bool = False,
    ):
        if not isinstance(connector1, RigidJoint) or not isinstance(
            connector2, RigidJoint
        ):
            raise TypeError("Connector mates require two RigidJoint-like connectors")
        if connector1.parent is connector2.parent:
            raise ValueError("A mate must connect different components")

        self.label = label
        self.connector1 = connector1
        self.connector2 = connector2
        self.offset = offset or MateOffset()
        self.flip_primary = bool(flip_primary)
        self.reorient_secondary = int(reorient_secondary) % 4
        self.suppressed = bool(suppressed)
        self.limits = _coerce_limits(limits)
        self.values: dict[MateDOF, float] = {}
        self._validate_options()

    @property
    def components(self) -> tuple[Shape, ...]:
        """The two components constrained by this mate."""

        return self.connector1.parent, self.connector2.parent  # type: ignore[return-value]

    def _validate_options(self):
        translation = self.offset.translation
        translation_dofs = (MateDOF.TX, MateDOF.TY, MateDOF.TZ)
        for dof, value in zip(translation_dofs, translation):
            if value and dof not in self.offset_translation_dofs:
                raise ValueError(
                    f"{type(self).__name__} does not support an offset along {dof.value}"
                )
        if any(self.offset.rotation) and not self.supports_rotation_offset:
            raise ValueError(
                f"{type(self).__name__} does not support a rotation offset"
            )
        invalid_limits = set(self.limits) - self.limit_dofs
        if invalid_limits:
            names = ", ".join(sorted(dof.value for dof in invalid_limits))
            raise ValueError(
                f"{type(self).__name__} does not support limits for {names}"
            )

    def set_value(self, dof: MateDOF | str, value: float | None) -> Mate:
        """Drive or release one of the mate's degrees of freedom."""

        key = MateDOF.coerce(dof)
        if not self.supports_values or key not in self.free_dofs:
            raise ValueError(
                f"{type(self).__name__} does not expose a {key.value} mate value"
            )
        if value is None:
            self.values.pop(key, None)
            return self
        if key in self.limits and not self.limits[key].contains(value):
            raise ValueError(f"{key.value} value {value} is outside {self.limits[key]}")
        self.values[key] = float(value)
        return self

    def suppress(self, suppressed: bool = True) -> Mate:
        """Suppress or unsuppress this mate without deleting it."""

        self.suppressed = suppressed
        return self

    def _alignment_matrix(self) -> np.ndarray:
        result = np.eye(4)
        result[:3, 3] = self.offset.translation

        orientation = SciPyRotation.from_euler(
            "xyz", self.offset.rotation, degrees=True
        )
        if self.flip_primary:
            orientation = SciPyRotation.from_euler("x", 180, degrees=True) * orientation
        if self.reorient_secondary:
            orientation = (
                SciPyRotation.from_euler(
                    "z", 90 * self.reorient_secondary, degrees=True
                )
                * orientation
            )
        result[:3, :3] = orientation.as_matrix()
        return result

    def _relative_matrix(self, poses: Mapping[object, np.ndarray]) -> np.ndarray:
        frame1 = poses[self.connector1.parent] @ _location_matrix(
            self.connector1.relative_location
        )
        frame2 = poses[self.connector2.parent] @ _location_matrix(
            self.connector2.relative_location
        )
        return np.linalg.inv(frame1) @ frame2 @ np.linalg.inv(self._alignment_matrix())

    def coordinate(
        self, poses: Mapping[object, np.ndarray], dof: MateDOF | str
    ) -> float:
        """Return the current value of a mate degree of freedom."""

        key = MateDOF.coerce(dof)
        if key in self.values:
            return self.values[key]
        relative = self._relative_matrix(poses)
        return self.coordinate_from_relative(relative, key)

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        """Return normalized residuals for the locked and driven mate DOFs."""

        relative = self._relative_matrix(poses)
        residuals: list[float] = []

        translation = relative[:3, 3]
        for index, dof in enumerate((MateDOF.TX, MateDOF.TY, MateDOF.TZ)):
            if dof not in self.free_dofs:
                residuals.append(float(translation[index]) / length_scale)
            elif dof in self.values:
                residuals.append(
                    (float(translation[index]) - self.values[dof]) / length_scale
                )

        rotation = relative[:3, :3]
        rotational_free = self.free_dofs.intersection(
            (MateDOF.RX, MateDOF.RY, MateDOF.RZ)
        )
        if not rotational_free:
            residuals.extend(SciPyRotation.from_matrix(rotation).as_rotvec().tolist())
        elif rotational_free == {MateDOF.RZ}:
            residuals.extend((rotation[:, 2] - np.array((0.0, 0.0, 1.0))).tolist())
            if MateDOF.RZ in self.values:
                angle = np.arctan2(rotation[1, 0], rotation[0, 0])
                residuals.append(
                    _wrap_radians(angle - np.deg2rad(self.values[MateDOF.RZ]))
                )

        residuals.extend(self._limit_residuals(relative, length_scale))
        return np.asarray(residuals, dtype=float)

    def _limit_residuals(
        self, relative: np.ndarray, length_scale: float
    ) -> list[float]:
        result: list[float] = []
        for dof, limit in self.limits.items():
            value = self.coordinate_from_relative(relative, dof)
            angular = dof in (
                MateDOF.RX,
                MateDOF.RY,
                MateDOF.RZ,
                MateDOF.SWING,
            )
            scale = 180 / pi if angular else length_scale
            if value < limit.minimum:
                result.append((value - limit.minimum) / scale)
            elif value > limit.maximum:
                result.append((value - limit.maximum) / scale)
            else:
                result.append(0.0)
        return result

    @staticmethod
    # A direct branch for each enum member keeps the coordinate definitions clear.
    # pylint: disable=too-many-return-statements
    def coordinate_from_relative(relative: np.ndarray, dof: MateDOF) -> float:
        """Extract a DOF value from an already computed relative transform."""

        if dof == MateDOF.TX:
            return float(relative[0, 3])
        if dof == MateDOF.TY:
            return float(relative[1, 3])
        if dof == MateDOF.TZ:
            return float(relative[2, 3])
        if dof == MateDOF.RZ:
            return degrees(float(np.arctan2(relative[1, 0], relative[0, 0])))
        euler = SciPyRotation.from_matrix(relative[:3, :3]).as_euler(
            "xyz", degrees=True
        )
        if dof == MateDOF.RX:
            return float(euler[0])
        if dof == MateDOF.RY:
            return float(euler[1])
        if dof == MateDOF.SWING:
            return degrees(acos(float(np.clip(relative[2, 2], -1.0, 1.0))))
        raise ValueError(f"Unknown mate degree of freedom {dof}")


class FastenedMate(Mate):
    """Remove all six relative degrees of freedom."""

    offset_translation_dofs = frozenset((MateDOF.TX, MateDOF.TY, MateDOF.TZ))
    supports_rotation_offset = True
    supports_values = False


class RevoluteMate(Mate):
    """Allow rotation about the mate connector Z axis."""

    free_dofs = frozenset((MateDOF.RZ,))
    offset_translation_dofs = frozenset((MateDOF.TZ,))
    supports_rotation_offset = True
    limit_dofs = free_dofs


class SliderMate(Mate):
    """Allow translation along the mate connector Z axis."""

    free_dofs = frozenset((MateDOF.TZ,))
    offset_translation_dofs = frozenset((MateDOF.TX, MateDOF.TY))
    supports_rotation_offset = True
    limit_dofs = free_dofs


class PlanarMate(Mate):
    """Allow X/Y translation and Z rotation in the connector plane."""

    free_dofs = frozenset((MateDOF.TX, MateDOF.TY, MateDOF.RZ))
    offset_translation_dofs = frozenset((MateDOF.TZ,))
    supports_rotation_offset = True
    limit_dofs = free_dofs


class CylindricalMate(Mate):
    """Allow translation along and rotation about the connector Z axis."""

    free_dofs = frozenset((MateDOF.TZ, MateDOF.RZ))
    limit_dofs = free_dofs


class PinSlotMate(Mate):
    """Allow translation along X and rotation about connector Z."""

    free_dofs = frozenset((MateDOF.TX, MateDOF.RZ))
    offset_translation_dofs = frozenset((MateDOF.TZ,))
    supports_rotation_offset = True
    limit_dofs = free_dofs


class BallMate(Mate):
    """Allow rotation about all three axes with an optional conical swing limit."""

    free_dofs = frozenset((MateDOF.RX, MateDOF.RY, MateDOF.RZ))
    limit_dofs = frozenset((MateDOF.SWING,))
    supports_values = False


class ParallelMate(Mate):
    """Keep connector Z axes parallel while leaving four degrees of freedom."""

    free_dofs = frozenset((MateDOF.TX, MateDOF.TY, MateDOF.TZ, MateDOF.RZ))
    limit_dofs = free_dofs


@dataclass(frozen=True)
class _EntityReference:
    """A selected topological entity stored relative to an owning component."""

    component: Shape
    entity: Shape
    relative_location: Location = field(init=False)
    local_entity: Shape = field(init=False)

    def __post_init__(self):
        if not isinstance(self.entity, (Face, Edge, Vertex)):
            raise TypeError("Tangent mates accept only faces, edges, or vertices")
        object.__setattr__(
            self,
            "relative_location",
            _matrix_location(
                np.linalg.inv(_location_matrix(self.component.location))
                @ _location_matrix(self.entity.location)
            ),
        )
        object.__setattr__(self, "local_entity", self.entity.located(Location()))

    def located(self, poses: Mapping[object, np.ndarray]) -> Shape:
        """Return this entity positioned by its component's candidate pose."""

        location = poses[self.component] @ _location_matrix(self.relative_location)
        return self.local_entity.located(_matrix_location(location))


def _shared_tangent_edge(face1: Face, face2: Face) -> bool:
    """Return whether two faces share a tangent-continuous edge."""

    for edge1 in face1.edges():
        for edge2 in face2.edges():
            if not edge1.is_same(edge2):
                continue
            point = edge1.position_at(0.5)
            normal1 = _normalized(_vector_tuple(face1.normal_at(point)))
            normal2 = _normalized(_vector_tuple(face2.normal_at(point)))
            return abs(float(np.dot(normal1, normal2))) >= 1 - 1e-7
    return False


def _propagated_faces(component: Shape, selected: Face) -> list[Face]:
    """Collect tangent-connected analytic faces for Tangent propagation."""

    faces = list(component.faces())
    selected_index = next(
        (index for index, face in enumerate(faces) if face.is_same(selected)), None
    )
    if selected_index is None:
        return [selected]

    result = [faces[selected_index]]
    pending = [faces[selected_index]]
    remaining = [face for index, face in enumerate(faces) if index != selected_index]
    while pending:
        current = pending.pop()
        attached = [
            candidate
            for candidate in remaining
            if _shared_tangent_edge(current, candidate)
        ]
        for candidate in attached:
            remaining.remove(candidate)
            result.append(candidate)
            pending.append(candidate)
    return result


def _edges_tangent_at_shared_vertex(edge1: Edge, edge2: Edge) -> bool:
    """Return whether two edges meet with tangent-continuous directions."""

    shared = next(
        (
            vertex1
            for vertex1 in edge1.vertices()
            for vertex2 in edge2.vertices()
            if vertex1.is_same(vertex2)
        ),
        None,
    )
    if shared is None:
        return False
    point = shared.center()
    tangent1 = _normalized(_vector_tuple(edge1.tangent_at(point)))
    tangent2 = _normalized(_vector_tuple(edge2.tangent_at(point)))
    return abs(float(np.dot(tangent1, tangent2))) >= 1 - 1e-7


def _propagated_edges(component: Shape, selected: Edge) -> list[Edge]:
    """Collect tangent-connected edges for Tangent propagation."""

    edges = list(component.edges())
    selected_index = next(
        (index for index, edge in enumerate(edges) if edge.is_same(selected)), None
    )
    if selected_index is None:
        return [selected]

    result = [edges[selected_index]]
    pending = [edges[selected_index]]
    remaining = [edge for index, edge in enumerate(edges) if index != selected_index]
    while pending:
        current = pending.pop()
        attached = [
            candidate
            for candidate in remaining
            if _edges_tangent_at_shared_vertex(current, candidate)
        ]
        for candidate in attached:
            remaining.remove(candidate)
            result.append(candidate)
            pending.append(candidate)
    return result


def _propagated_entities(component: Shape, selected: Shape) -> list[Shape]:
    """Apply Onshape-style Tangent propagation for the selected entity kind."""

    if isinstance(selected, Face):
        return _propagated_faces(component, selected)
    if isinstance(selected, Edge):
        return _propagated_edges(component, selected)
    return [selected]


def _entity_parameters(entity: Shape, point: Vector) -> list[float]:
    """Find normalized surface/curve parameters nearest to ``point``."""

    if isinstance(entity, Face):
        surface = BRep_Tool.Surface_s(entity.wrapped)
        projector = GeomAPI_ProjectPointOnSurf(point.to_pnt(), surface)
        if projector.NbPoints() == 0:
            return [0.5, 0.5]
        u_value, v_value = projector.LowerDistanceParameters()
        u_min, u_max, v_min, v_max = entity._uv_bounds()
        u = (u_value - u_min) / (u_max - u_min) if u_max != u_min else 0.5
        v = (v_value - v_min) / (v_max - v_min) if v_max != v_min else 0.5
        return [float(np.clip(u, 0, 1)), float(np.clip(v, 0, 1))]
    if isinstance(entity, Edge):
        return [float(np.clip(entity.param_at_point(point), 0, 1))]
    return []


def _entity_point_direction(
    entity: Shape, parameters: Sequence[float] | np.ndarray
) -> tuple[np.ndarray, np.ndarray | None]:
    """Evaluate an entity contact point and its normal/tangent direction."""

    if isinstance(entity, Face):
        point = entity.position_at(parameters[0], parameters[1])
        direction = entity.normal_at(parameters[0], parameters[1])
    elif isinstance(entity, Edge):
        point = entity.position_at(parameters[0])
        direction = entity.tangent_at(parameters[0])
    elif isinstance(entity, Vertex):
        point = entity.center()
        direction = None
    else:  # pragma: no cover - validated by TangentMate
        raise TypeError(type(entity))
    return _vector_tuple(point), (
        None if direction is None else _normalized(_vector_tuple(direction))
    )


def _parameter_candidates(
    entity: Shape, nearest_point: Vector | None = None
) -> list[tuple[float, ...]]:
    """Generate stable contact-parameter starting candidates for an entity."""

    candidates: list[tuple[float, ...]] = []
    if nearest_point is not None:
        candidates.append(tuple(_entity_parameters(entity, nearest_point)))
    samples = np.linspace(0.0, 1.0, 5)
    if isinstance(entity, Face):
        candidates.extend((float(u), float(v)) for u in samples for v in samples)
    elif isinstance(entity, Edge):
        candidates.extend((float(value),) for value in np.linspace(0.0, 1.0, 9))
    else:
        candidates.append(())
    return list(dict.fromkeys(candidates))


def _tangent_alignment_error(
    entity1: Shape,
    direction1: np.ndarray | None,
    entity2: Shape,
    direction2: np.ndarray | None,
    flip_primary: bool,
) -> float:
    """Score how closely two sampled entity directions satisfy tangency."""

    if direction1 is None or direction2 is None:
        return 0.0
    dot = float(np.clip(np.dot(direction1, direction2), -1, 1))
    if isinstance(entity1, Face) and isinstance(entity2, Face):
        target = 1.0 if flip_primary else -1.0
        return 1.0 - target * dot
    if isinstance(entity1, Face) or isinstance(entity2, Face):
        return abs(dot)
    return 1.0 - abs(dot)


class TangentMate(Mate):
    """Keep two selected analytic entities tangent.

    Faces, edges, and vertices are supported.  Face selections reject generic
    Bezier/B-spline surfaces, matching Onshape's swept/analytic-face rule.
    ``propagate=True`` expands a selected face across tangent-continuous
    neighboring faces.
    """

    supports_values = False

    # This geometric mate has no pair of connector objects for Mate.__init__.
    # pylint: disable=super-init-not-called
    def __init__(
        self,
        label: str,
        component1: Shape,
        entity1: Shape,
        component2: Shape,
        entity2: Shape,
        *,
        propagate: bool = True,
        flip_primary: bool = False,
        suppressed: bool = False,
    ):
        if component1 is component2:
            raise ValueError("A tangent mate must connect different components")
        self.label = label
        self.component1 = component1
        self.component2 = component2
        self.propagate = bool(propagate)
        self.flip_primary = bool(flip_primary)
        self.suppressed = bool(suppressed)
        self.values = {}
        self.limits = {}

        for entity in (entity1, entity2):
            if isinstance(entity, Face) and entity.geom_type in (
                GeomType.BEZIER,
                GeomType.BSPLINE,
                GeomType.OFFSET,
                GeomType.OTHER,
            ):
                raise ValueError(
                    "TangentMate supports analytic or swept faces, not generic surfaces"
                )
            if not isinstance(entity, (Face, Edge, Vertex)):
                raise TypeError(
                    "TangentMate selections must be faces, edges, or vertices"
                )

        entities1 = (
            _propagated_entities(component1, entity1) if propagate else [entity1]
        )
        entities2 = (
            _propagated_entities(component2, entity2) if propagate else [entity2]
        )
        self.entities1 = tuple(
            _EntityReference(component1, entity) for entity in entities1
        )
        self.entities2 = tuple(
            _EntityReference(component2, entity) for entity in entities2
        )
        self._active_pair: tuple[_EntityReference, _EntityReference] | None = None
        self._parameter_counts: tuple[int, int] = (0, 0)

    @property
    def components(self) -> tuple[Shape, Shape]:
        return self.component1, self.component2

    def suppress(self, suppressed: bool = True) -> TangentMate:
        self.suppressed = suppressed
        return self

    def prepare_parameters(
        self, poses: Mapping[object, np.ndarray]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Select a propagated entity pair and initialize its contact parameters."""

        located1 = [
            (reference, reference.located(poses)) for reference in self.entities1
        ]
        located2 = [
            (reference, reference.located(poses)) for reference in self.entities2
        ]
        pairs = [
            (
                entity1.distance_to(entity2),
                reference1,
                entity1,
                reference2,
                entity2,
            )
            for reference1, entity1 in located1
            for reference2, entity2 in located2
        ]
        best: (
            tuple[
                float,
                _EntityReference,
                _EntityReference,
                tuple[float, ...],
                tuple[float, ...],
            ]
            | None
        ) = None
        for _, reference1, entity1, reference2, entity2 in pairs:
            _, point1, point2 = entity1.distance_to_with_closest_points(entity2)
            scale = max(
                entity1.bounding_box(optimal=False).diagonal,
                entity2.bounding_box(optimal=False).diagonal,
                1.0,
            )
            candidates1 = _parameter_candidates(entity1, point1)
            candidates2 = _parameter_candidates(entity2, point2)
            evaluated1 = [
                (parameters, *_entity_point_direction(entity1, parameters))
                for parameters in candidates1
            ]
            evaluated2 = [
                (parameters, *_entity_point_direction(entity2, parameters))
                for parameters in candidates2
            ]
            for parameters1, sample1, direction1 in evaluated1:
                for parameters2, sample2, direction2 in evaluated2:
                    score = np.linalg.norm(sample2 - sample1) / scale + 4 * (
                        _tangent_alignment_error(
                            entity1,
                            direction1,
                            entity2,
                            direction2,
                            self.flip_primary,
                        )
                    )
                    candidate = (
                        float(score),
                        reference1,
                        reference2,
                        parameters1,
                        parameters2,
                    )
                    if best is None or candidate[0] < best[0]:
                        best = candidate
        assert best is not None
        _, reference1, reference2, parameters1, parameters2 = best
        self._active_pair = (reference1, reference2)
        self._parameter_counts = (len(parameters1), len(parameters2))
        values = np.asarray((*parameters1, *parameters2), dtype=float)
        return values, np.zeros(len(values)), np.ones(len(values))

    def residual(
        self,
        poses: Mapping[object, np.ndarray],
        length_scale: float,
        parameters: Sequence[float] | np.ndarray | None = None,
    ) -> np.ndarray:
        active_parameters: Sequence[float] | np.ndarray
        if self._active_pair is None or parameters is None:
            active_parameters, _, _ = self.prepare_parameters(poses)
        else:
            active_parameters = parameters
        reference1, reference2 = self._active_pair  # type: ignore[misc]
        count1, count2 = self._parameter_counts
        entity1 = reference1.located(poses)
        entity2 = reference2.located(poses)
        point1, direction1 = _entity_point_direction(
            entity1, active_parameters[:count1]
        )
        point2, direction2 = _entity_point_direction(
            entity2, active_parameters[count1 : count1 + count2]
        )
        residuals = ((point2 - point1) / length_scale).tolist()

        if isinstance(entity1, Face) and isinstance(entity2, Face):
            assert direction1 is not None and direction2 is not None
            target = 1.0 if self.flip_primary else -1.0
            residuals.extend(np.cross(direction1, direction2).tolist())
            residuals.append(float(np.dot(direction1, direction2) - target))
        elif isinstance(entity1, Face) and isinstance(entity2, Edge):
            assert direction1 is not None and direction2 is not None
            residuals.append(float(np.dot(direction1, direction2)))
        elif isinstance(entity1, Edge) and isinstance(entity2, Face):
            assert direction1 is not None and direction2 is not None
            residuals.append(float(np.dot(direction1, direction2)))
        elif isinstance(entity1, Edge) and isinstance(entity2, Edge):
            assert direction1 is not None and direction2 is not None
            residuals.extend(np.cross(direction1, direction2).tolist())

        return np.asarray(residuals, dtype=float)


class WidthMate(Mate):
    """Center one or two tab connectors between two width connectors.

    With one tab connector, the tab may translate in and rotate normally to
    the slot center plane.  With two tab connectors, their locations and XY
    planes remain mirror-symmetric across the slot center plane.
    """

    supports_values = False

    # Width has three or four connectors, so Mate.__init__ does not apply.
    # pylint: disable=super-init-not-called
    def __init__(
        self,
        label: str,
        tabs: RigidJoint | Sequence[RigidJoint],
        widths: Sequence[RigidJoint],
        *,
        suppressed: bool = False,
    ):
        tab_connectors = (tabs,) if isinstance(tabs, RigidJoint) else tuple(tabs)
        width_connectors = tuple(widths)
        if len(tab_connectors) not in (1, 2):
            raise ValueError("WidthMate requires one or two tab connectors")
        if len(width_connectors) != 2:
            raise ValueError("WidthMate requires exactly two width connectors")
        if not all(
            isinstance(connector, RigidJoint)
            for connector in (*tab_connectors, *width_connectors)
        ):
            raise TypeError("WidthMate requires RigidJoint-like connectors")
        tab_components = {id(connector.parent) for connector in tab_connectors}
        width_components = {id(connector.parent) for connector in width_connectors}
        if tab_components.intersection(width_components):
            raise ValueError(
                "Tab and width mate connectors cannot belong to the same component"
            )

        self.label = label
        self.tabs = tab_connectors
        self.widths = width_connectors
        self.suppressed = bool(suppressed)
        self.values = {}
        self.limits = {}

    @property
    def components(self) -> tuple[Shape, ...]:
        result: list[Shape] = []
        for connector in (*self.tabs, *self.widths):
            if not any(connector.parent is component for component in result):
                result.append(connector.parent)  # type: ignore[arg-type]
        return tuple(result)

    def suppress(self, suppressed: bool = True) -> WidthMate:
        self.suppressed = suppressed
        return self

    @staticmethod
    def _frame(connector: RigidJoint, poses: Mapping[object, np.ndarray]) -> np.ndarray:
        return poses[connector.parent] @ _location_matrix(connector.relative_location)

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        width1, width2 = (self._frame(connector, poses) for connector in self.widths)
        center = (width1[:3, 3] + width2[:3, 3]) / 2
        normal = _normalized(width2[:3, 3] - width1[:3, 3])

        if len(self.tabs) == 1:
            tab = self._frame(self.tabs[0], poses)
            tab_normal = tab[:3, 2]
            return np.asarray(
                [
                    float(np.dot(tab[:3, 3] - center, normal)) / length_scale,
                    *(tab_normal - normal).tolist(),
                ]
            )

        tab1, tab2 = (self._frame(connector, poses) for connector in self.tabs)

        def reflect_point(point: np.ndarray) -> np.ndarray:
            return point - 2 * np.dot(point - center, normal) * normal

        def reflect_vector(vector: np.ndarray) -> np.ndarray:
            return vector - 2 * np.dot(vector, normal) * normal

        position_error = (tab2[:3, 3] - reflect_point(tab1[:3, 3])) / length_scale
        normal_error = tab2[:3, 2] - reflect_vector(tab1[:3, 2])
        return np.concatenate((position_error, normal_error))


class GroupMate(Mate):
    """Keep two or more components fixed relative to their initial origins.

    Like Onshape's Group feature, this ignores selected geometry and records
    only the relative component-origin transforms present at construction.
    The resulting group retains six rigid-body degrees of freedom until one
    member is otherwise constrained or fixed.
    """

    supports_values = False

    # Group records component origins rather than connector pairs.
    # pylint: disable=super-init-not-called
    def __init__(
        self,
        label: str,
        components: Iterable[Shape],
        *,
        suppressed: bool = False,
    ):
        component_tuple = tuple(components)
        if len(component_tuple) < 2:
            raise ValueError("GroupMate requires at least two components")
        if not all(isinstance(component, Shape) for component in component_tuple):
            raise TypeError("GroupMate components must be build123d Shapes")
        if len({id(component) for component in component_tuple}) != len(
            component_tuple
        ):
            raise ValueError("GroupMate components must be unique")

        self.label = label
        self._components = component_tuple
        self.suppressed = bool(suppressed)
        self.values = {}
        self.limits = {}
        reference = _location_matrix(component_tuple[0].location)
        self._relative_poses = tuple(
            np.linalg.inv(reference) @ _location_matrix(component.location)
            for component in component_tuple[1:]
        )

    @property
    def components(self) -> tuple[Shape, ...]:
        """Components whose origin transforms are held relative."""

        return self._components

    def suppress(self, suppressed: bool = True) -> GroupMate:
        """Suppress or unsuppress this group without deleting it."""

        self.suppressed = suppressed
        return self

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        """Return errors from the captured component-origin transforms."""

        reference = poses[self._components[0]]
        residuals: list[float] = []
        for component, expected in zip(self._components[1:], self._relative_poses):
            relative = np.linalg.inv(reference) @ poses[component]
            error = relative @ np.linalg.inv(expected)
            residuals.extend((error[:3, 3] / length_scale).tolist())
            residuals.extend(
                SciPyRotation.from_matrix(error[:3, :3]).as_rotvec().tolist()
            )
        return np.asarray(residuals, dtype=float)


class MateRelation:
    """Base class for persistent relationships between mate DOFs."""

    def __init__(self, label: str, *, suppressed: bool = False):
        self.label = label
        self.suppressed = bool(suppressed)
        self._phase: float | None = None

    @property
    def mates(self) -> tuple[Mate, ...]:
        """Mates referenced by this relation."""

        raise NotImplementedError

    def suppress(self, suppressed: bool = True) -> MateRelation:
        """Suppress or unsuppress this relation without deleting it."""

        self.suppressed = suppressed
        return self

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        """Return the normalized coupling error for candidate component poses."""

        raise NotImplementedError

    @staticmethod
    def _require_dof(mate: Mate, dof: MateDOF):
        if dof not in mate.free_dofs:
            raise ValueError(
                f"{type(mate).__name__} does not provide {dof.value} for a relation"
            )


class GearRelation(MateRelation):
    """Relate two rotational mate DOFs by a constant ratio."""

    def __init__(
        self,
        label: str,
        mate1: Mate,
        mate2: Mate,
        ratio: float = 1.0,
        *,
        dof1: MateDOF | str = MateDOF.RZ,
        dof2: MateDOF | str = MateDOF.RZ,
        reverse: bool = False,
        suppressed: bool = False,
    ):
        super().__init__(label, suppressed=suppressed)
        self.mate1, self.mate2 = mate1, mate2
        self.dof1, self.dof2 = MateDOF.coerce(dof1), MateDOF.coerce(dof2)
        self._require_dof(mate1, self.dof1)
        self._require_dof(mate2, self.dof2)
        if self.dof1 not in (MateDOF.RX, MateDOF.RY, MateDOF.RZ) or self.dof2 not in (
            MateDOF.RX,
            MateDOF.RY,
            MateDOF.RZ,
        ):
            raise ValueError("GearRelation requires rotational mate DOFs")
        if ratio <= 0:
            raise ValueError("Gear ratio must be positive")
        self.ratio = float(ratio)
        self.reverse = bool(reverse)

    @property
    def mates(self) -> tuple[Mate, Mate]:
        return self.mate1, self.mate2

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        value1 = self.mate1.coordinate(poses, self.dof1)
        value2 = self.mate2.coordinate(poses, self.dof2)
        sign = 1.0 if self.reverse else -1.0
        expression = value2 - sign * self.ratio * value1
        if self._phase is None:
            self._phase = expression
        return np.asarray([_wrap_radians((expression - self._phase) * pi / 180)])


class RackAndPinionRelation(MateRelation):
    """Relate a rotational mate DOF to linear travel per revolution."""

    def __init__(
        self,
        label: str,
        rotational_mate: Mate,
        linear_mate: Mate,
        travel_per_revolution: float,
        *,
        rotational_dof: MateDOF | str = MateDOF.RZ,
        linear_dof: MateDOF | str = MateDOF.TZ,
        reverse: bool = False,
        suppressed: bool = False,
    ):
        super().__init__(label, suppressed=suppressed)
        self.rotational_mate, self.linear_mate = rotational_mate, linear_mate
        self.rotational_dof = MateDOF.coerce(rotational_dof)
        self.linear_dof = MateDOF.coerce(linear_dof)
        self._require_dof(rotational_mate, self.rotational_dof)
        self._require_dof(linear_mate, self.linear_dof)
        if self.rotational_dof not in (
            MateDOF.RX,
            MateDOF.RY,
            MateDOF.RZ,
        ):
            raise ValueError("RackAndPinionRelation requires a rotational DOF")
        if self.linear_dof not in (MateDOF.TX, MateDOF.TY, MateDOF.TZ):
            raise ValueError("RackAndPinionRelation requires a linear DOF")
        if travel_per_revolution <= 0:
            raise ValueError("Travel per revolution must be positive")
        self.travel_per_revolution = float(travel_per_revolution)
        self.reverse = bool(reverse)

    @property
    def mates(self) -> tuple[Mate, Mate]:
        return self.rotational_mate, self.linear_mate

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        angle = self.rotational_mate.coordinate(poses, self.rotational_dof)
        travel = self.linear_mate.coordinate(poses, self.linear_dof)
        sign = -1.0 if self.reverse else 1.0
        expression = travel - sign * self.travel_per_revolution * angle / 360
        if self._phase is None:
            self._phase = expression
        return np.asarray([(expression - self._phase) / length_scale])


class ScrewRelation(MateRelation):
    """Couple rotation and translation in one cylindrical-style mate."""

    def __init__(
        self,
        label: str,
        mate: Mate,
        travel_per_revolution: float,
        *,
        rotational_dof: MateDOF | str = MateDOF.RZ,
        linear_dof: MateDOF | str = MateDOF.TZ,
        reverse: bool = False,
        suppressed: bool = False,
    ):
        super().__init__(label, suppressed=suppressed)
        self.mate = mate
        self.rotational_dof = MateDOF.coerce(rotational_dof)
        self.linear_dof = MateDOF.coerce(linear_dof)
        self._require_dof(mate, self.rotational_dof)
        self._require_dof(mate, self.linear_dof)
        if travel_per_revolution <= 0:
            raise ValueError("Travel per revolution must be positive")
        self.travel_per_revolution = float(travel_per_revolution)
        self.reverse = bool(reverse)

    @property
    def mates(self) -> tuple[Mate]:
        return (self.mate,)

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        angle = self.mate.coordinate(poses, self.rotational_dof)
        travel = self.mate.coordinate(poses, self.linear_dof)
        sign = -1.0 if self.reverse else 1.0
        expression = travel - sign * self.travel_per_revolution * angle / 360
        if self._phase is None:
            self._phase = expression
        return np.asarray([(expression - self._phase) / length_scale])


class LinearRelation(MateRelation):
    """Relate two linear mate DOFs by a constant ratio."""

    def __init__(
        self,
        label: str,
        mate1: Mate,
        mate2: Mate,
        ratio: float = 1.0,
        *,
        dof1: MateDOF | str = MateDOF.TZ,
        dof2: MateDOF | str = MateDOF.TZ,
        reverse: bool = False,
        suppressed: bool = False,
    ):
        super().__init__(label, suppressed=suppressed)
        self.mate1, self.mate2 = mate1, mate2
        self.dof1, self.dof2 = MateDOF.coerce(dof1), MateDOF.coerce(dof2)
        self._require_dof(mate1, self.dof1)
        self._require_dof(mate2, self.dof2)
        if self.dof1 not in (MateDOF.TX, MateDOF.TY, MateDOF.TZ) or self.dof2 not in (
            MateDOF.TX,
            MateDOF.TY,
            MateDOF.TZ,
        ):
            raise ValueError("LinearRelation requires linear mate DOFs")
        if ratio <= 0:
            raise ValueError("Linear ratio must be positive")
        self.ratio = float(ratio)
        self.reverse = bool(reverse)

    @property
    def mates(self) -> tuple[Mate, Mate]:
        return self.mate1, self.mate2

    def residual(
        self, poses: Mapping[object, np.ndarray], length_scale: float
    ) -> np.ndarray:
        value1 = self.mate1.coordinate(poses, self.dof1)
        value2 = self.mate2.coordinate(poses, self.dof2)
        sign = 1.0 if self.reverse else -1.0
        expression = value2 - sign * self.ratio * value1
        if self._phase is None:
            self._phase = expression
        return np.asarray([(expression - self._phase) / length_scale])


@dataclass(frozen=True)
class MateSolveResult:
    """Summary of an assembly mate solve."""

    success: bool
    cost: float
    max_residual: float
    iterations: int
    degrees_of_freedom: int
    message: str


class Assembly(Compound):
    """A compound whose component positions are governed by persistent mates."""

    def __init__(
        self,
        components: Iterable[Shape] | None = None,
        *,
        label: str = "",
    ):
        component_list = list(components or ())
        labels = [component.label for component in component_list if component.label]
        if len(labels) != len(set(labels)):
            raise ValueError("Assembly component labels must be unique")
        super().__init__(
            obj=component_list,
            label=label,
            children=component_list,
        )
        self.mates: list[Mate] = []
        self.relations: list[MateRelation] = []
        self._fixed_component_ids: set[int] = set()
        self.last_solve: MateSolveResult | None = None

    def __deepcopy__(self, memo) -> Self:
        """Copy geometry, components, mate connections, relations, and grounding."""

        original_components = list(self.children)
        result = super().__deepcopy__(memo)
        copied_components = list(result.children)
        copied_by_original_id = {
            id(original): copied
            for original, copied in zip(original_components, copied_components)
        }
        result._fixed_component_ids = {
            id(copied_by_original_id[original_id])
            for original_id in self._fixed_component_ids
            if original_id in copied_by_original_id
        }
        return result

    @property
    def components(self) -> tuple[Shape, ...]:
        """Direct component instances in this assembly."""

        return tuple(self.children)

    def add(
        self,
        component: Shape,
        *,
        name: str | None = None,
        fixed: bool = False,
    ) -> Shape:
        """Add a component instance to the assembly."""

        if not isinstance(component, Shape):
            raise TypeError("Assembly components must be build123d Shapes")
        if any(component is child for child in self.children):
            raise ValueError("Component is already in this assembly")
        if name is not None:
            component.label = name
        if component.label and any(
            child.label == component.label for child in self.children
        ):
            raise ValueError(f"Duplicate assembly component label {component.label!r}")
        component.parent = self
        if fixed:
            self.ground(component)
        return component

    def component(self, name: str) -> Shape:
        """Find a direct component by label."""

        matches = [component for component in self.children if component.label == name]
        if not matches:
            raise KeyError(name)
        if len(matches) > 1:  # pragma: no cover - protected by add/constructor
            raise KeyError(f"Component label {name!r} is ambiguous")
        return matches[0]

    def ground(self, component: Shape, fixed: bool = True) -> Assembly:
        """Ground or unground a component."""

        self._require_component(component)
        if fixed:
            self._fixed_component_ids.add(id(component))
        else:
            self._fixed_component_ids.discard(id(component))
        return self

    def is_fixed(self, component: Shape) -> bool:
        """Return whether a component is explicitly grounded."""

        return id(component) in self._fixed_component_ids

    def add_mate(self, mate: Mate, *, solve: bool = True) -> Mate:
        """Persist a mate and optionally solve the assembly immediately."""

        if not isinstance(mate, Mate):
            raise TypeError("add_mate expects a Mate")
        if any(existing.label == mate.label for existing in self.mates):
            raise ValueError(f"Duplicate mate label {mate.label!r}")
        for component in mate.components:
            self._require_component(component)
        self.mates.append(mate)
        if solve:
            try:
                self.solve()
            except Exception:
                self.mates.remove(mate)
                raise
        return mate

    def add_relation(
        self, relation: MateRelation, *, solve: bool = True
    ) -> MateRelation:
        """Persist a mate relation and optionally solve immediately."""

        if not isinstance(relation, MateRelation):
            raise TypeError("add_relation expects a MateRelation")
        if any(existing.label == relation.label for existing in self.relations):
            raise ValueError(f"Duplicate relation label {relation.label!r}")
        for mate in relation.mates:
            if mate not in self.mates:
                raise ValueError("Mate relations may reference only assembly mates")
        self.relations.append(relation)
        if solve:
            try:
                self.solve()
            except Exception:
                self.relations.remove(relation)
                raise
        return relation

    def mate(self, label: str) -> Mate:
        """Find a mate by label."""

        return next((mate for mate in self.mates if mate.label == label), None) or (
            _raise_key_error(label)
        )

    def relation(self, label: str) -> MateRelation:
        """Find a mate relation by label."""

        return next(
            (relation for relation in self.relations if relation.label == label), None
        ) or _raise_key_error(label)

    def fastened(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> FastenedMate:
        """Add a persistent Fastened mate."""

        return self.add_mate(  # type: ignore[return-value]
            FastenedMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def revolute(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> RevoluteMate:
        """Add a persistent Revolute mate."""

        return self.add_mate(  # type: ignore[return-value]
            RevoluteMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def slider(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> SliderMate:
        """Add a persistent Slider mate."""

        return self.add_mate(  # type: ignore[return-value]
            SliderMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def planar(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> PlanarMate:
        """Add a persistent Planar mate."""

        return self.add_mate(  # type: ignore[return-value]
            PlanarMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def cylindrical(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> CylindricalMate:
        """Add a persistent Cylindrical mate."""

        return self.add_mate(  # type: ignore[return-value]
            CylindricalMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def pin_slot(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> PinSlotMate:
        """Add a persistent Pin Slot mate."""

        return self.add_mate(  # type: ignore[return-value]
            PinSlotMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def ball(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> BallMate:
        """Add a persistent Ball mate."""

        return self.add_mate(  # type: ignore[return-value]
            BallMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def parallel(
        self,
        label: str,
        connector1: RigidJoint,
        connector2: RigidJoint,
        **kwargs,
    ) -> ParallelMate:
        """Add a persistent Parallel mate."""

        return self.add_mate(  # type: ignore[return-value]
            ParallelMate(label, connector1, connector2, **_mate_kwargs(kwargs)),
            solve=kwargs.pop("solve", True),
        )

    def tangent(self, label: str, *args, **kwargs) -> TangentMate:
        """Add a persistent Tangent mate."""

        solve = kwargs.pop("solve", True)
        return self.add_mate(  # type: ignore[return-value]
            TangentMate(label, *args, **kwargs), solve=solve
        )

    def width(self, label: str, *args, **kwargs) -> WidthMate:
        """Add a persistent Width mate."""

        solve = kwargs.pop("solve", True)
        return self.add_mate(  # type: ignore[return-value]
            WidthMate(label, *args, **kwargs), solve=solve
        )

    def group(
        self,
        label: str,
        components: Iterable[Shape],
        **kwargs,
    ) -> GroupMate:
        """Add a persistent rigid group using the components' current origins."""

        solve = kwargs.pop("solve", True)
        return self.add_mate(  # type: ignore[return-value]
            GroupMate(label, components, **kwargs), solve=solve
        )

    def solve(
        self,
        *,
        tolerance: float = 1e-7,
        max_iterations: int = 2000,
        strict: bool = True,
    ) -> MateSolveResult:
        """Solve all active mates and relations simultaneously.

        Explicitly fixed components remain at their current locations.  When
        none are fixed, the first component is implicitly grounded to remove
        the assembly's six global rigid-body degrees of freedom.
        """

        components = list(self.children)
        if not components:
            result = MateSolveResult(True, 0.0, 0.0, 0, 0, "empty assembly")
            self.last_solve = result
            return result

        active_mates = [mate for mate in self.mates if not mate.suppressed]
        active_relations = [
            relation
            for relation in self.relations
            if not relation.suppressed
            and not any(mate.suppressed for mate in relation.mates)
        ]

        initial_matrices = _PoseMap(
            {
                id(component): _location_matrix(component.location)
                for component in components
            }
        )
        fixed_ids = set(self._fixed_component_ids)
        if not fixed_ids:
            fixed_ids.add(id(components[0]))
        variable_components = [
            component for component in components if id(component) not in fixed_ids
        ]
        component_poses = [
            _matrix_pose(initial_matrices[component])
            for component in variable_components
        ]
        component_vector = (
            np.concatenate(component_poses) if component_poses else np.empty(0)
        )
        pose_variable_count = len(component_vector)
        tangent_parameter_slices: dict[int, slice] = {}
        parameter_values: list[np.ndarray] = []
        parameter_lower: list[np.ndarray] = []
        parameter_upper: list[np.ndarray] = []
        parameter_offset = pose_variable_count
        for mate in active_mates:
            if isinstance(mate, TangentMate):
                values, lower, upper = mate.prepare_parameters(initial_matrices)
                tangent_parameter_slices[id(mate)] = slice(
                    parameter_offset, parameter_offset + len(values)
                )
                parameter_offset += len(values)
                parameter_values.append(values)
                parameter_lower.append(lower)
                parameter_upper.append(upper)
        contact_parameter_count = parameter_offset - pose_variable_count
        initial_vector = np.concatenate((component_vector, *parameter_values))
        lower_bounds = np.concatenate(
            (np.full(pose_variable_count, -np.inf), *parameter_lower)
        )
        upper_bounds = np.concatenate(
            (np.full(pose_variable_count, np.inf), *parameter_upper)
        )

        diagonals = [
            component.bounding_box(optimal=False).diagonal
            for component in components
            if component.bounding_box(optimal=False).diagonal > 1e-12
        ]
        length_scale = float(np.median(diagonals)) if diagonals else 1.0

        def unpack(vector: np.ndarray) -> _PoseMap:
            poses = _PoseMap(initial_matrices)
            for index, component in enumerate(variable_components):
                poses[id(component)] = _pose_matrix(vector[index * 6 : index * 6 + 6])
            return poses

        def primary_residual(vector: np.ndarray) -> np.ndarray:
            poses = unpack(vector)
            residuals = [
                (
                    mate.residual(
                        poses,
                        length_scale,
                        vector[tangent_parameter_slices[id(mate)]],
                    )
                    if isinstance(mate, TangentMate)
                    else mate.residual(poses, length_scale)
                )
                for mate in active_mates
            ]
            residuals.extend(
                relation.residual(poses, length_scale) for relation in active_relations
            )
            return np.concatenate(residuals) if residuals else np.empty(0, dtype=float)

        def objective(vector: np.ndarray) -> np.ndarray:
            primary = primary_residual(vector)
            # Select the solution nearest the current configuration when the
            # system is underconstrained, without materially weakening mates.
            regularization = 1e-6 * (vector - initial_vector)
            return np.concatenate((primary, regularization))

        if initial_vector.size:
            optimization = least_squares(
                objective,
                initial_vector,
                method="trf",
                bounds=(lower_bounds, upper_bounds),
                xtol=1e-12,
                ftol=1e-12,
                gtol=1e-12,
                max_nfev=max_iterations,
            )
            solved_vector = optimization.x
            iterations = optimization.nfev
            message = optimization.message
            jacobian = optimization.jac
        else:
            solved_vector = initial_vector
            iterations = 0
            message = "all components fixed"
            jacobian = np.empty((0, 0))

        final_residual = primary_residual(solved_vector)
        max_residual = (
            float(np.max(np.abs(final_residual))) if final_residual.size else 0.0
        )
        cost = float(np.dot(final_residual, final_residual) / 2)
        primary_jacobian = (
            jacobian[: final_residual.size, :] if jacobian.size else jacobian
        )
        rank = (
            int(np.linalg.matrix_rank(primary_jacobian, tol=1e-6))
            if primary_jacobian.size
            else 0
        )
        physical_rank = max(0, rank - contact_parameter_count)
        degrees_of_freedom = max(0, pose_variable_count - physical_rank)
        success = max_residual <= tolerance
        result = MateSolveResult(
            success,
            cost,
            max_residual,
            iterations,
            degrees_of_freedom,
            str(message),
        )
        self.last_solve = result
        if strict and not success:
            raise MateSolveError(
                "Assembly mates are inconsistent or failed to converge "
                f"(max normalized residual {max_residual:.3g})"
            )

        solved_poses = unpack(solved_vector)
        for component in variable_components:
            component.locate(_matrix_location(solved_poses[component]))
        self._rebuild_compounds()
        return result

    def _require_component(self, component: Shape):
        if not any(component is child for child in self.children):
            raise ValueError("Mate component is not a direct member of this assembly")

    def _rebuild_compounds(self):
        node: Compound | None = self
        while isinstance(node, Compound):
            # pylint: disable=attribute-defined-outside-init
            node.wrapped = _make_topods_compound_from_shapes(
                [child.wrapped for child in node.children]
            )
            node = node.parent


def _mate_kwargs(kwargs: dict) -> dict:
    """Remove Assembly-only convenience options from mate constructor kwargs."""

    return {key: value for key, value in kwargs.items() if key != "solve"}


def _raise_key_error(label: str):
    raise KeyError(label)


__all__ = [
    "Assembly",
    "BallMate",
    "CylindricalMate",
    "FastenedMate",
    "GearRelation",
    "GroupMate",
    "LinearRelation",
    "Mate",
    "MateConnector",
    "MateDOF",
    "MateLimit",
    "MateOffset",
    "MateRelation",
    "MateSolveError",
    "MateSolveResult",
    "ParallelMate",
    "PinSlotMate",
    "PlanarMate",
    "RackAndPinionRelation",
    "RevoluteMate",
    "ScrewRelation",
    "SliderMate",
    "TangentMate",
    "WidthMate",
]
