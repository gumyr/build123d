"""
Lossless build123d assembly metadata and AP242 kinematics encoding.

AP242 has native entities for common low-order pairs, ranges, and mechanism
states, but it cannot represent every Onshape feature-level detail.  STEP files
therefore contain both:

* standard AP242 kinematics for faithfully representable motion; and
* a versioned build123d payload in an ISO 10303-21 comment for exact round trips.

The comment is deliberately supplemental.  AP242 readers that do not know
build123d still see the standard mechanism, links, joints, pairs, placements,
and ranges.
"""

from __future__ import annotations

import base64
import json
import re
import zlib
from copy import deepcopy
from math import inf, pi
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import numpy as np

from build123d.assembly import (
    Assembly,
    BallMate,
    CylindricalMate,
    FastenedMate,
    GearRelation,
    GroupMate,
    LinearRelation,
    Mate,
    MateConnector,
    MateDOF,
    MateOffset,
    ParallelMate,
    PinSlotMate,
    PlanarMate,
    RackAndPinionRelation,
    RevoluteMate,
    ScrewRelation,
    SliderMate,
    TangentMate,
    WidthMate,
    _PoseMap,
    _location_matrix,
    _matrix_location,
)
from build123d.joints import RigidJoint
from build123d.topology import Edge, Face, Shape, Vertex

if TYPE_CHECKING:
    from build123d.assembly import MateRelation


MANIFEST_SCHEMA = "https://build123d.org/schemas/assembly-kinematics/1"
_PAYLOAD_PREFIX = "build123d:assembly-kinematics:1:"
_PAYLOAD_PATTERN = re.compile(
    rb"/\*\s*" + re.escape(_PAYLOAD_PREFIX.encode()) + rb"([A-Za-z0-9+/=]+)\s*\*/"
)

_ONSHAPE_MATE_TYPES: dict[type[Mate], str] = {
    FastenedMate: "FASTENED",
    SliderMate: "SLIDER",
    CylindricalMate: "CYLINDRICAL",
    RevoluteMate: "REVOLUTE",
    PinSlotMate: "PIN_SLOT",
    PlanarMate: "PLANAR",
    BallMate: "BALL",
    ParallelMate: "PARALLEL",
    TangentMate: "TANGENT",
    WidthMate: "WIDTH",
    GroupMate: "GROUP",
}

_AP242_PAIR_TYPES: dict[type[Mate], str | None] = {
    FastenedMate: "FULLY_CONSTRAINED_PAIR",
    RevoluteMate: "REVOLUTE_PAIR_WITH_RANGE",
    SliderMate: "PRISMATIC_PAIR_WITH_RANGE",
    PlanarMate: "PLANAR_PAIR_WITH_RANGE",
    CylindricalMate: "CYLINDRICAL_PAIR_WITH_RANGE",
    PinSlotMate: "LOW_ORDER_KINEMATIC_PAIR_WITH_RANGE",
    BallMate: "SPHERICAL_PAIR",
    ParallelMate: "LOW_ORDER_KINEMATIC_PAIR_WITH_RANGE",
    TangentMate: None,
    WidthMate: None,
    GroupMate: "FULLY_CONSTRAINED_PAIR",
}

_AP242_EXTENSION_REASONS: dict[type[Mate], tuple[str, ...]] = {
    PinSlotMate: ("AP242 has no Pin Slot feature identity; generic DOFs are used",),
    BallMate: (
        "Onshape's conical swing limit is not equivalent to AP242 yaw/pitch/roll ranges",
    ),
    ParallelMate: ("AP242 has no Parallel feature identity; generic DOFs are used",),
    TangentMate: ("propagated face/edge/vertex selections are not one AP242 pair",),
    WidthMate: ("multi-component centering/symmetry has no AP242 pair",),
    GroupMate: ("the rigid pairs do not retain Onshape Group feature identity",),
}

_RELATION_AP242: dict[type[MateRelation], tuple[str | None, tuple[str, ...]]] = {
    GearRelation: (
        None,
        (
            "AP242 GEAR_PAIR requires both pitch radii, while Onshape stores only "
            "a ratio",
        ),
    ),
    RackAndPinionRelation: (
        None,
        (
            "the Onshape relation references two existing mate coordinates rather "
            "than one adjacent-link AP242 RACK_AND_PINION_PAIR",
        ),
    ),
    ScrewRelation: (
        None,
        (
            "the Onshape relation couples coordinates of an existing mate and "
            "retains reverse and phase separately",
        ),
    ),
    LinearRelation: (
        None,
        ("AP242 has no general linear-to-linear mate-coordinate coupling pair",),
    ),
}


def _matrix_list(location) -> list[list[float]]:
    return _location_matrix(location).tolist()


def _finite_or_none(value: float) -> float | None:
    return None if value in (-inf, inf) else float(value)


def _component_index(assembly: Assembly, component: Shape) -> int:
    return next(
        index
        for index, candidate in enumerate(assembly.components)
        if candidate is component
    )


def _connector_record(assembly: Assembly, connector: RigidJoint) -> dict[str, Any]:
    return {
        "label": connector.label,
        "component": _component_index(assembly, connector.parent),
        "relativeTransform": _matrix_list(connector.relative_location),
    }


def _entity_record(component: Shape, entity: Shape) -> dict[str, Any]:
    entity_type, candidates = (
        ("FACE", component.faces())
        if isinstance(entity, Face)
        else (
            ("EDGE", component.edges())
            if isinstance(entity, Edge)
            else (
                ("VERTEX", component.vertices())
                if isinstance(entity, Vertex)
                else (None, ())
            )
        )
    )
    if entity_type is None:
        raise TypeError("Mate entity must be a face, edge, or vertex")
    index = next(
        (
            candidate_index
            for candidate_index, candidate in enumerate(candidates)
            if candidate.is_same(entity)
        ),
        None,
    )
    if index is None:
        raise ValueError("Mate entity is not part of its owning component")
    return {"type": entity_type, "index": index}


def _onshape_limit_parameter_id(dof: MateDOF, bound: str) -> str:
    axis = dof.value[-1].upper()
    if dof in (MateDOF.TX, MateDOF.TY, MateDOF.TZ):
        return f"limit{axis}{bound}"
    if dof in (MateDOF.RX, MateDOF.RY, MateDOF.RZ):
        return f"limitAxial{axis}{bound}"
    if dof == MateDOF.SWING and bound == "Max":
        return "limitEulerConeAngleMax"
    return f"build123d:{dof.value}:{bound.lower()}"


def _canonical_onshape_values(mate: Mate) -> dict[str, Any]:
    """Return stable Onshape API parameter IDs without discarding raw records."""

    values: dict[str, Any] = {
        "mateType": _ONSHAPE_MATE_TYPES[type(mate)],
        "limitsEnabled": bool(mate.limits),
    }
    if hasattr(mate, "flip_primary"):
        values["primaryAxisAlignment"] = not bool(mate.flip_primary)
    if hasattr(mate, "reorient_secondary"):
        values["secondaryAxisAlignment"] = (
            "PLUS_X",
            "PLUS_Y",
            "MINUS_X",
            "MINUS_Y",
        )[mate.reorient_secondary]
    for dof, limit in mate.limits.items():
        minimum = _finite_or_none(limit.minimum)
        maximum = _finite_or_none(limit.maximum)
        if minimum is not None and dof != MateDOF.SWING:
            values[_onshape_limit_parameter_id(dof, "Min")] = minimum
        if maximum is not None:
            values[_onshape_limit_parameter_id(dof, "Max")] = maximum
    return values


def _base_mate_record(assembly: Assembly, mate: Mate) -> dict[str, Any]:
    poses = _PoseMap(
        {
            id(component): _location_matrix(component.location)
            for component in assembly.components
        }
    )
    return {
        "type": type(mate).__name__,
        "label": mate.label,
        "suppressed": mate.suppressed,
        "limits": {
            dof.value: {
                "minimum": _finite_or_none(limit.minimum),
                "maximum": _finite_or_none(limit.maximum),
            }
            for dof, limit in mate.limits.items()
        },
        "values": {dof.value: value for dof, value in mate.values.items()},
        "currentValues": {
            dof.value: mate.coordinate(poses, dof)
            for dof in mate.free_dofs
            if not isinstance(mate, (TangentMate, WidthMate, GroupMate))
        },
        "onshape": {
            "values": _canonical_onshape_values(mate),
            "parameters": deepcopy(mate.onshape_parameters),
        },
        "ap242": {
            "pairType": _AP242_PAIR_TYPES[type(mate)],
            "extensionReasons": list(_AP242_EXTENSION_REASONS.get(type(mate), ())),
        },
    }


def _mate_record(assembly: Assembly, mate: Mate) -> dict[str, Any]:
    record = _base_mate_record(assembly, mate)
    if isinstance(mate, TangentMate):
        record.update(
            {
                "components": [
                    _component_index(assembly, mate.component1),
                    _component_index(assembly, mate.component2),
                ],
                "entities": [
                    [
                        _entity_record(reference.component, reference.entity)
                        for reference in mate.entities1
                    ],
                    [
                        _entity_record(reference.component, reference.entity)
                        for reference in mate.entities2
                    ],
                ],
                "propagate": mate.propagate,
                "flipPrimary": mate.flip_primary,
            }
        )
    elif isinstance(mate, WidthMate):
        record.update(
            {
                "tabs": [
                    _connector_record(assembly, connector) for connector in mate.tabs
                ],
                "widths": [
                    _connector_record(assembly, connector) for connector in mate.widths
                ],
            }
        )
    elif isinstance(mate, GroupMate):
        record.update(
            {
                "components": [
                    _component_index(assembly, component)
                    for component in mate.components
                ],
                "relativeTransforms": [
                    matrix.tolist() for matrix in mate._relative_poses
                ],
            }
        )
    else:
        first_transform = _location_matrix(mate.connector1.relative_location)
        second_transform = _location_matrix(mate.connector2.relative_location)
        effective_second_transform = second_transform @ _inverse(
            mate._alignment_matrix()
        )
        record.update(
            {
                "connectors": [
                    _connector_record(assembly, mate.connector1),
                    _connector_record(assembly, mate.connector2),
                ],
                "offset": {
                    "translation": list(mate.offset.translation),
                    "rotation": list(mate.offset.rotation),
                },
                "flipPrimary": mate.flip_primary,
                "reorientSecondary": mate.reorient_secondary,
            }
        )
        # The standard pair placements include Onshape's offset and axis
        # alignment.  Raw connector frames and options remain separately
        # available in the lossless manifest.
        record["ap242"]["placements"] = [
            first_transform.tolist(),
            effective_second_transform.tolist(),
        ]
    return record


def _relation_record(
    mate_indices: Mapping[int, int], relation: MateRelation
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": type(relation).__name__,
        "label": relation.label,
        "suppressed": relation.suppressed,
        "phase": relation._phase,
        "mates": [mate_indices[id(mate)] for mate in relation.mates],
        "onshape": {"parameters": deepcopy(relation.onshape_parameters)},
        "ap242": {
            "pairType": _RELATION_AP242[type(relation)][0],
            "extensionReasons": list(_RELATION_AP242[type(relation)][1]),
        },
    }
    if isinstance(relation, (GearRelation, LinearRelation)):
        record.update(
            {
                "ratio": relation.ratio,
                "reverse": relation.reverse,
                "dofs": [relation.dof1.value, relation.dof2.value],
            }
        )
    elif isinstance(relation, RackAndPinionRelation):
        record.update(
            {
                "travelPerRevolution": relation.travel_per_revolution,
                "reverse": relation.reverse,
                "dofs": [
                    relation.rotational_dof.value,
                    relation.linear_dof.value,
                ],
            }
        )
    elif isinstance(relation, ScrewRelation):
        record.update(
            {
                "travelPerRevolution": relation.travel_per_revolution,
                "reverse": relation.reverse,
                "dofs": [
                    relation.rotational_dof.value,
                    relation.linear_dof.value,
                ],
            }
        )
    return record


def assembly_to_kinematics(assembly: Assembly) -> dict[str, Any]:
    """Serialize every assembly constraint field into a versioned manifest."""

    mate_indices = {id(mate): index for index, mate in enumerate(assembly.mates)}
    return {
        "$schema": MANIFEST_SCHEMA,
        "label": assembly.label,
        "units": {"length": "model-unit", "angle": "degree"},
        "components": [
            {
                "label": component.label,
                "fixed": assembly.is_fixed(component),
                "transform": _matrix_list(component.location),
            }
            for component in assembly.components
        ],
        "mates": [_mate_record(assembly, mate) for mate in assembly.mates],
        "relations": [
            _relation_record(mate_indices, relation) for relation in assembly.relations
        ],
    }


def encode_kinematics_payload(manifest: Mapping[str, Any]) -> str:
    """Encode a deterministic, compressed payload safe for a STEP comment."""

    data = json.dumps(
        manifest,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return base64.b64encode(zlib.compress(data, level=9)).decode()


def decode_kinematics_payload(payload: str | bytes) -> dict[str, Any]:
    """Decode and validate one build123d STEP kinematics payload."""

    raw = payload.encode() if isinstance(payload, str) else payload
    manifest = json.loads(zlib.decompress(base64.b64decode(raw)))
    if manifest.get("$schema") != MANIFEST_SCHEMA:
        raise ValueError("Unsupported build123d assembly kinematics schema")
    return manifest


def read_step_kinematics(step: str | bytes) -> dict[str, Any] | None:
    """Read the lossless mate payload from STEP text or bytes."""

    data = step.encode() if isinstance(step, str) else step
    match = _PAYLOAD_PATTERN.search(data)
    return decode_kinematics_payload(match.group(1)) if match else None


def _limit_value(value: float | None, fallback: float) -> float:
    return fallback if value is None else float(value)


def _limits_from_record(
    record: Mapping[str, Any],
) -> dict[MateDOF, tuple[float, float]]:
    return {
        MateDOF(dof): (
            _limit_value(bounds["minimum"], -inf),
            _limit_value(bounds["maximum"], inf),
        )
        for dof, bounds in record["limits"].items()
    }


def _connector_from_record(
    record: Mapping[str, Any], components: Sequence[Shape]
) -> MateConnector:
    component = components[int(record["component"])]
    relative = _matrix_location(_as_matrix(record["relativeTransform"]))
    return MateConnector(
        str(record["label"]),
        component,  # type: ignore[arg-type]
        component.location * relative,
    )


def _entity_from_record(component: Shape, record: Mapping[str, Any]) -> Shape:
    candidates = {
        "FACE": component.faces,
        "EDGE": component.edges,
        "VERTEX": component.vertices,
    }[str(record["type"])]()
    try:
        return candidates[int(record["index"])]
    except IndexError as error:
        raise ValueError(
            "STEP topology no longer matches the stored TangentMate selection"
        ) from error


def assembly_from_kinematics(
    manifest: Mapping[str, Any], components: Sequence[Shape]
) -> Assembly:
    """Recreate persistent mates and relations around imported STEP components."""

    component_records = manifest["components"]
    if len(components) != len(component_records):
        raise ValueError(
            "STEP assembly component count does not match its kinematics payload"
        )
    component_list = list(components)
    for component, record in zip(component_list, component_records):
        component.label = str(record["label"])
        component.locate(_matrix_location(_as_matrix(record["transform"])))

    assembly = Assembly(component_list, label=str(manifest["label"]))
    for component, record in zip(component_list, component_records):
        if record["fixed"]:
            assembly.ground(component)

    connector_mates: dict[str, type[Mate]] = {
        mate_type.__name__: mate_type
        for mate_type in (
            FastenedMate,
            RevoluteMate,
            SliderMate,
            PlanarMate,
            CylindricalMate,
            PinSlotMate,
            BallMate,
            ParallelMate,
        )
    }
    restored_mates: list[Mate] = []
    for record in manifest["mates"]:
        mate_type = str(record["type"])
        common = {
            "suppressed": bool(record["suppressed"]),
            "onshape_parameters": record["onshape"]["parameters"],
        }
        if mate_type in connector_mates:
            connector1, connector2 = (
                _connector_from_record(connector, component_list)
                for connector in record["connectors"]
            )
            offset = record["offset"]
            mate = connector_mates[mate_type](
                str(record["label"]),
                connector1,
                connector2,
                offset=MateOffset(
                    tuple(offset["translation"]), tuple(offset["rotation"])
                ),
                limits=_limits_from_record(record),
                flip_primary=bool(record["flipPrimary"]),
                reorient_secondary=int(record["reorientSecondary"]),
                **common,
            )
            for dof, value in record["values"].items():
                mate.set_value(dof, float(value))
        elif mate_type == "TangentMate":
            component1, component2 = (
                component_list[int(index)] for index in record["components"]
            )
            mate = TangentMate(
                str(record["label"]),
                component1,
                _entity_from_record(component1, record["entities"][0][0]),
                component2,
                _entity_from_record(component2, record["entities"][1][0]),
                propagate=bool(record["propagate"]),
                flip_primary=bool(record["flipPrimary"]),
                **common,
            )
        elif mate_type == "WidthMate":
            tabs = [
                _connector_from_record(connector, component_list)
                for connector in record["tabs"]
            ]
            widths = [
                _connector_from_record(connector, component_list)
                for connector in record["widths"]
            ]
            mate = WidthMate(str(record["label"]), tabs, widths, **common)
        elif mate_type == "GroupMate":
            grouped = [component_list[int(index)] for index in record["components"]]
            mate = GroupMate(str(record["label"]), grouped, **common)
            mate._relative_poses = tuple(
                _as_matrix(matrix) for matrix in record["relativeTransforms"]
            )
        else:
            raise ValueError(f"Unsupported stored mate type {mate_type!r}")
        assembly.add_mate(mate, solve=False)
        restored_mates.append(mate)

    relation_types: dict[str, type[MateRelation]] = {
        relation_type.__name__: relation_type
        for relation_type in (
            GearRelation,
            RackAndPinionRelation,
            ScrewRelation,
            LinearRelation,
        )
    }
    for record in manifest["relations"]:
        mate_refs = [restored_mates[int(index)] for index in record["mates"]]
        common = {
            "suppressed": bool(record["suppressed"]),
            "onshape_parameters": record["onshape"]["parameters"],
        }
        relation_type = str(record["type"])
        if relation_type in ("GearRelation", "LinearRelation"):
            relation = relation_types[relation_type](
                str(record["label"]),
                *mate_refs,
                ratio=float(record["ratio"]),
                dof1=record["dofs"][0],
                dof2=record["dofs"][1],
                reverse=bool(record["reverse"]),
                **common,
            )
        elif relation_type == "RackAndPinionRelation":
            relation = RackAndPinionRelation(
                str(record["label"]),
                *mate_refs,
                travel_per_revolution=float(record["travelPerRevolution"]),
                rotational_dof=record["dofs"][0],
                linear_dof=record["dofs"][1],
                reverse=bool(record["reverse"]),
                **common,
            )
        elif relation_type == "ScrewRelation":
            relation = ScrewRelation(
                str(record["label"]),
                mate_refs[0],
                travel_per_revolution=float(record["travelPerRevolution"]),
                rotational_dof=record["dofs"][0],
                linear_dof=record["dofs"][1],
                reverse=bool(record["reverse"]),
                **common,
            )
        else:
            raise ValueError(f"Unsupported stored relation type {relation_type!r}")
        relation._phase = record["phase"]
        assembly.add_relation(relation, solve=False)
    return assembly


def _inverse(matrix):
    """Return the inverse of a homogeneous transform."""
    return np.linalg.inv(matrix)


def _step_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _step_real(value: float) -> str:
    if abs(value) < 1e-15:
        return "0."
    text = f"{value:.15g}"
    return text if any(character in text for character in ".Ee") else text + "."


def _step_optional(value: float | None, *, angular: bool = False) -> str:
    if value is None:
        return "$"
    return _step_real(value * pi / 180 if angular else value)


class _StepEntities:
    def __init__(self, first_id: int):
        self.next_id = first_id
        self.lines: list[str] = []

    def add(self, entity: str) -> int:
        """Append one Part 21 entity and return its numeric identifier."""
        entity_id = self.next_id
        self.next_id += 1
        self.lines.append(f"#{entity_id} = {entity};")
        return entity_id


def _axis_placement(entities: _StepEntities, name: str, matrix) -> int:
    point = entities.add(
        "CARTESIAN_POINT("
        + _step_quote(name + " origin")
        + ",("
        + ",".join(_step_real(float(value)) for value in matrix[:3, 3])
        + "))"
    )
    axis = entities.add(
        "DIRECTION("
        + _step_quote(name + " primary")
        + ",("
        + ",".join(_step_real(float(value)) for value in matrix[:3, 2])
        + "))"
    )
    ref = entities.add(
        "DIRECTION("
        + _step_quote(name + " secondary")
        + ",("
        + ",".join(_step_real(float(value)) for value in matrix[:3, 0])
        + "))"
    )
    return entities.add(
        f"AXIS2_PLACEMENT_3D({_step_quote(name)},#{point},#{axis},#{ref})"
    )


def _range(record: Mapping[str, Any], dof: str) -> tuple[float | None, float | None]:
    limit = record["limits"].get(dof, {})
    return limit.get("minimum"), limit.get("maximum")


def _pair_entity(
    record: Mapping[str, Any],
    joint_id: int,
    first_axis: int,
    second_axis: int,
) -> str | None:
    # Explicit pair branches keep EXPRESS attribute ordering easy to audit.
    # pylint: disable=too-many-return-statements
    pair_type = record["ap242"]["pairType"]
    if pair_type is None:
        return None
    free = {
        "FastenedMate": (),
        "RevoluteMate": ("rz",),
        "SliderMate": ("tz",),
        "PlanarMate": ("tx", "ty", "rz"),
        "CylindricalMate": ("tz", "rz"),
        "PinSlotMate": ("tx", "rz"),
        "BallMate": ("rx", "ry", "rz"),
        "ParallelMate": ("tx", "ty", "tz", "rz"),
    }.get(record["type"])
    if free is None:
        return None
    bools = ",".join(
        ".T." if dof in free else ".F." for dof in ("tx", "ty", "tz", "rx", "ry", "rz")
    )
    common = (
        f"{_step_quote(record['label'])},{_step_quote(record['label'] + ' placement')},"
        f"$,#{first_axis},#{second_axis},#{joint_id},{bools}"
    )
    if record["type"] == "FastenedMate":
        return f"FULLY_CONSTRAINED_PAIR({common})"
    if record["type"] == "RevoluteMate":
        lower, upper = _range(record, "rz")
        return (
            f"REVOLUTE_PAIR_WITH_RANGE({common},"
            f"{_step_optional(lower, angular=True)},"
            f"{_step_optional(upper, angular=True)})"
        )
    if record["type"] == "SliderMate":
        lower, upper = _range(record, "tz")
        return (
            f"PRISMATIC_PAIR_WITH_RANGE({common},"
            f"{_step_optional(lower)},{_step_optional(upper)})"
        )
    if record["type"] == "PlanarMate":
        rz = _range(record, "rz")
        tx = _range(record, "tx")
        ty = _range(record, "ty")
        values = (
            _step_optional(rz[0], angular=True),
            _step_optional(rz[1], angular=True),
            _step_optional(tx[0]),
            _step_optional(tx[1]),
            _step_optional(ty[0]),
            _step_optional(ty[1]),
        )
        return f"PLANAR_PAIR_WITH_RANGE({common},{','.join(values)})"
    if record["type"] == "CylindricalMate":
        tz = _range(record, "tz")
        rz = _range(record, "rz")
        values = (
            _step_optional(tz[0]),
            _step_optional(tz[1]),
            _step_optional(rz[0], angular=True),
            _step_optional(rz[1], angular=True),
        )
        return f"CYLINDRICAL_PAIR_WITH_RANGE({common},{','.join(values)})"
    if record["type"] in ("PinSlotMate", "ParallelMate"):
        values: list[str] = []
        for dof in ("rx", "ry", "rz", "tx", "ty", "tz"):
            lower, upper = _range(record, dof)
            angular = dof.startswith("r")
            values.extend(
                (
                    _step_optional(lower, angular=angular),
                    _step_optional(upper, angular=angular),
                )
            )
        return f"LOW_ORDER_KINEMATIC_PAIR_WITH_RANGE({common},{','.join(values)})"
    if record["type"] == "BallMate":
        return f"SPHERICAL_PAIR({common})"
    return None


def _find_representation_context(step_text: str) -> int:
    matches = re.findall(
        r"#(\d+)\s*=\s*\([^;]*GEOMETRIC_REPRESENTATION_CONTEXT\(3\)[^;]*"
        r"REPRESENTATION_CONTEXT\(",
        step_text,
        flags=re.DOTALL,
    )
    if not matches:
        raise ValueError("STEP file has no 3D representation context")
    return int(matches[-1])


def _step_statements(step_text: str) -> dict[int, str]:
    return {
        int(entity_id): body.strip()
        for entity_id, body in re.findall(
            r"#(\d+)\s*=\s*(.*?);", step_text, flags=re.DOTALL
        )
    }


def _references(statement: str) -> list[int]:
    return [int(value) for value in re.findall(r"#(\d+)", statement)]


def _first_step_string(statement: str) -> str | None:
    match = re.search(r"\(\s*'((?:''|[^'])*)'", statement)
    return match.group(1).replace("''", "'") if match else None


def _product_definition(statements: Mapping[int, str], label: str) -> int | None:
    product = next(
        (
            entity_id
            for entity_id, statement in statements.items()
            if statement.startswith("PRODUCT(")
            and _first_step_string(statement) == label
        ),
        None,
    )
    if product is None:
        return None
    formation = next(
        (
            entity_id
            for entity_id, statement in statements.items()
            if statement.startswith("PRODUCT_DEFINITION_FORMATION(")
            and _references(statement)
            and _references(statement)[-1] == product
        ),
        None,
    )
    if formation is None:
        return None
    return next(
        (
            entity_id
            for entity_id, statement in statements.items()
            if statement.startswith("PRODUCT_DEFINITION(")
            and _references(statement)
            and _references(statement)[0] == formation
        ),
        None,
    )


def _shape_representation(
    statements: Mapping[int, str], product_definition: int
) -> int | None:
    definition_shape = next(
        (
            entity_id
            for entity_id, statement in statements.items()
            if statement.startswith("PRODUCT_DEFINITION_SHAPE(")
            and _references(statement)
            and _references(statement)[-1] == product_definition
        ),
        None,
    )
    if definition_shape is None:
        return None
    return next(
        (
            refs[1]
            for statement in statements.values()
            if statement.startswith("SHAPE_DEFINITION_REPRESENTATION(")
            and len(refs := _references(statement)) >= 2
            and refs[0] == definition_shape
        ),
        None,
    )


def _component_occurrence(
    statements: Mapping[int, str],
    parent_definition: int,
    component_definition: int,
) -> int | None:
    return next(
        (
            entity_id
            for entity_id, statement in statements.items()
            if statement.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE(")
            and len(refs := _references(statement)) >= 2
            and refs[-2:] == [parent_definition, component_definition]
        ),
        None,
    )


def _native_kinematics(step_text: str, manifest: Mapping[str, Any]) -> list[str]:
    ids = [int(value) for value in re.findall(r"#(\d+)\s*=", step_text)]
    entities = _StepEntities(max(ids, default=0) + 1)
    context_id = _find_representation_context(step_text)

    link_ids = [
        entities.add(f"KINEMATIC_LINK({_step_quote(component['label'])})")
        for component in manifest["components"]
    ]
    joint_ids: list[int] = []
    pair_ids: list[int] = []
    pair_value_ids: list[int] = []
    component_placements: dict[int, list[int]] = {
        index: [] for index in range(len(link_ids))
    }

    for record in manifest["mates"]:
        if record["suppressed"] or "connectors" not in record:
            continue
        connector1, connector2 = record["connectors"]
        component1, component2 = connector1["component"], connector2["component"]
        joint_id = entities.add(
            f"KINEMATIC_JOINT({_step_quote(record['label'])},"
            f"#{link_ids[component1]},#{link_ids[component2]})"
        )
        joint_ids.append(joint_id)
        first_placement, second_placement = record["ap242"]["placements"]
        first_axis = _axis_placement(
            entities, record["label"] + " first", _as_matrix(first_placement)
        )
        second_axis = _axis_placement(
            entities,
            record["label"] + " second",
            _as_matrix(second_placement),
        )
        component_placements[component1].append(first_axis)
        component_placements[component2].append(second_axis)
        pair = _pair_entity(record, joint_id, first_axis, second_axis)
        if pair is not None:
            pair_id = entities.add(pair)
            pair_ids.append(pair_id)
            current = record["currentValues"]
            actual_values = []
            for dof in ("tx", "ty", "tz", "rx", "ry", "rz"):
                value = float(current.get(dof, 0.0))
                if dof.startswith("r"):
                    value *= pi / 180
                actual_values.append(_step_real(value))
            pair_value_ids.append(
                entities.add(
                    f"LOW_ORDER_KINEMATIC_PAIR_VALUE("
                    f"{_step_quote(record['label'] + ' state')},"
                    f"#{pair_id},{','.join(actual_values)})"
                )
            )

    identity_matrix = _as_matrix(
        (
            (1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0, 1),
        )
    )
    for record in manifest["mates"]:
        if record["suppressed"] or record["type"] != "GroupMate":
            continue
        reference_component = int(record["components"][0])
        for group_index, (component, expected) in enumerate(
            zip(record["components"][1:], record["relativeTransforms"]), start=1
        ):
            component = int(component)
            pair_label = f"{record['label']} {group_index}"
            joint_id = entities.add(
                f"KINEMATIC_JOINT({_step_quote(pair_label)},"
                f"#{link_ids[reference_component]},#{link_ids[component]})"
            )
            joint_ids.append(joint_id)
            first_axis = _axis_placement(
                entities, pair_label + " first", _as_matrix(expected)
            )
            second_axis = _axis_placement(
                entities, pair_label + " second", identity_matrix
            )
            component_placements[reference_component].append(first_axis)
            component_placements[component].append(second_axis)
            common = (
                f"{_step_quote(pair_label)},"
                f"{_step_quote(pair_label + ' placement')},$,"
                f"#{first_axis},#{second_axis},#{joint_id},"
                ".F.,.F.,.F.,.F.,.F.,.F."
            )
            pair_id = entities.add(f"FULLY_CONSTRAINED_PAIR({common})")
            pair_ids.append(pair_id)
            pair_value_ids.append(
                entities.add(
                    f"LOW_ORDER_KINEMATIC_PAIR_VALUE("
                    f"{_step_quote(pair_label + ' state')},#{pair_id},"
                    "0.,0.,0.,0.,0.,0.)"
                )
            )

    # Tangent and Width constraints do not have a faithful standard pair.
    # Their complete records still remain in the lossless payload.
    if not pair_ids:
        return []

    link_representation_ids = []
    for component_index, link_id in enumerate(link_ids):
        placements = component_placements[component_index]
        if not placements:
            identity = _axis_placement(
                entities,
                manifest["components"][component_index]["label"] + " origin",
                identity_matrix,
            )
            placements = [identity]
        items = ",".join(f"#{placement}" for placement in placements)
        link_representation_ids.append(
            entities.add(
                f"RIGID_LINK_REPRESENTATION("
                f"{_step_quote(manifest['components'][component_index]['label'])},"
                f"({items}),#{context_id},#{link_id})"
            )
        )

    topology_items = ",".join(f"#{entity_id}" for entity_id in (*link_ids, *joint_ids))
    topology = entities.add(
        f"KINEMATIC_TOPOLOGY_STRUCTURE("
        f"{_step_quote(manifest['label'] + ' topology')},"
        f"({topology_items}),#{context_id})"
    )
    mechanism_items = ",".join(f"#{pair_id}" for pair_id in pair_ids)
    mechanism = entities.add(
        f"MECHANISM_REPRESENTATION("
        f"{_step_quote(manifest['label'] + ' mechanism')},"
        f"({mechanism_items}),#{context_id},#{topology})"
    )
    if pair_value_ids:
        state_items = ",".join(f"#{value_id}" for value_id in pair_value_ids)
        entities.add(
            f"MECHANISM_STATE_REPRESENTATION("
            f"{_step_quote(manifest['label'] + ' state')},"
            f"({state_items}),#{context_id},#{mechanism})"
        )
    statements = _step_statements(step_text)
    root_definition = _product_definition(statements, manifest["label"])
    for component_index, component in enumerate(manifest["components"]):
        component_definition = _product_definition(statements, component["label"])
        if component_definition is None:
            continue
        shape_representation = _shape_representation(statements, component_definition)
        if shape_representation is not None:
            association = entities.add(
                f"KINEMATIC_LINK_REPRESENTATION_ASSOCIATION("
                f"{_step_quote(component['label'] + ' geometry')},$,"
                f"#{link_representation_ids[component_index]},"
                f"#{shape_representation})"
            )
        else:
            association = None
        if root_definition is not None and association is not None:
            occurrence = _component_occurrence(
                statements, root_definition, component_definition
            )
            if occurrence is not None:
                relationship = entities.add(
                    f"PRODUCT_DEFINITION_RELATIONSHIP_KINEMATICS("
                    f"{_step_quote(component['label'] + ' occurrence')},$,"
                    f"#{occurrence})"
                )
                entities.add(
                    f"CONTEXT_DEPENDENT_KINEMATIC_LINK_REPRESENTATION("
                    f"#{association},#{relationship})"
                )
    if root_definition is not None and link_representation_ids:
        property_definition = entities.add(
            f"PRODUCT_DEFINITION_KINEMATICS("
            f"{_step_quote(manifest['label'] + ' kinematics')},$,"
            f"#{root_definition})"
        )
        base_index = next(
            (
                index
                for index, component in enumerate(manifest["components"])
                if component["fixed"]
            ),
            0,
        )
        entities.add(
            f"KINEMATIC_PROPERTY_MECHANISM_REPRESENTATION("
            f"#{property_definition},#{mechanism},"
            f"#{link_representation_ids[base_index]})"
        )
    return entities.lines


def _as_matrix(values):
    """Convert serialized nested sequences to a floating-point matrix."""
    return np.asarray(values, dtype=float)


def inject_step_kinematics(step: str | bytes, assembly: Assembly) -> bytes:
    """Inject native AP242 entities and the exact build123d payload."""

    step_text = step.decode() if isinstance(step, bytes) else step
    # APIHeaderSection creates FILE_SCHEMA before STEPCAFControl_Writer copies
    # write.step.schema into the model.  The APD and data are AP242 already;
    # synchronize the early-created header during this physical-file pass.
    step_text = re.sub(
        r"FILE_SCHEMA\s*\(\('[^']*'\)\);",
        "FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF "
        "{1 0 10303 442 1 1 4 }'));",
        step_text,
        count=1,
    )
    manifest = assembly_to_kinematics(assembly)
    native = _native_kinematics(step_text, manifest)
    payload = encode_kinematics_payload(manifest)
    marker = "ENDSEC;\nEND-ISO-10303-21;"
    if marker not in step_text:
        raise ValueError("Invalid STEP physical file")
    insertion = "\n".join(
        (*native, f"/* {_PAYLOAD_PREFIX}{payload} */", "ENDSEC;", "END-ISO-10303-21;")
    )
    return step_text.rsplit(marker, 1)[0].encode() + insertion.encode()


__all__ = [
    "MANIFEST_SCHEMA",
    "assembly_from_kinematics",
    "assembly_to_kinematics",
    "decode_kinematics_payload",
    "encode_kinematics_payload",
    "inject_step_kinematics",
    "read_step_kinematics",
]
