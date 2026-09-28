"""AP242 and lossless STEP tests for persistent assembly mates."""

from io import BytesIO

import pytest
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPControl import STEPControl_Reader

import build123d.step_kinematics as step_kinematics

from build123d import (
    Assembly,
    BallMate,
    Box,
    CylindricalMate,
    FastenedMate,
    GroupMate,
    Location,
    MateConnector,
    MateLimit,
    MateOffset,
    ParallelMate,
    PinSlotMate,
    PlanarMate,
    RevoluteMate,
    ScrewRelation,
    SliderMate,
    assembly_to_kinematics,
    export_step,
    import_step_assembly,
    read_step_kinematics,
)


def connector_assembly():
    """Create a grounded two-component assembly and two connector frames."""

    base = Box(2, 2, 2)
    base.label = "base"
    moving = Box(1, 1, 1).moved(Location((4, 0, 0)))
    moving.label = "moving"
    assembly = Assembly((base, moving), label="mechanism").ground(base)
    first = MateConnector("first", base, Location((0, 0, 1)))
    second = MateConnector("second", moving, Location((4, 0, 0)))
    return assembly, first, second


@pytest.mark.parametrize(
    ("mate_type", "limits", "entity_name"),
    [
        (FastenedMate, {}, "FULLY_CONSTRAINED_PAIR"),
        (RevoluteMate, {"rz": (-45, 90)}, "REVOLUTE_PAIR_WITH_RANGE"),
        (SliderMate, {"tz": (-2, 4)}, "PRISMATIC_PAIR_WITH_RANGE"),
        (
            PlanarMate,
            {"tx": (-2, 4), "ty": (-3, 5), "rz": (-45, 90)},
            "PLANAR_PAIR_WITH_RANGE",
        ),
        (
            CylindricalMate,
            {"tz": (-2, 4), "rz": (-45, 90)},
            "CYLINDRICAL_PAIR_WITH_RANGE",
        ),
        (
            PinSlotMate,
            {"tx": (-2, 4), "rz": (-45, 90)},
            "LOW_ORDER_KINEMATIC_PAIR_WITH_RANGE",
        ),
        (BallMate, {"swing": (0, 35)}, "SPHERICAL_PAIR"),
        (
            ParallelMate,
            {"tx": (-2, 4), "rz": (-45, 90)},
            "LOW_ORDER_KINEMATIC_PAIR_WITH_RANGE",
        ),
    ],
)
def test_native_ap242_pair_types(tmp_path, mate_type, limits, entity_name):
    """Every connector mate has the closest valid native AP242 pair."""

    assembly, first, second = connector_assembly()
    assembly.add_mate(
        mate_type(
            "test mate",
            first,
            second,
            limits=limits,
            onshape_parameters=[
                {
                    "parameterId": "limitEulerConeAngleMax",
                    "expression": "0.610865238198 rad",
                }
            ],
        ),
        solve=False,
    )
    output = tmp_path / "kinematics.step"

    export_step(assembly, output)
    text = output.read_text()

    assert "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF" in text
    assert f"{entity_name}(" in text
    assert "KINEMATIC_LINK(" in text
    assert "KINEMATIC_JOINT(" in text
    assert "MECHANISM_STATE_REPRESENTATION(" in text
    manifest = read_step_kinematics(text)
    assert manifest is not None
    assert manifest["mates"][0]["onshape"]["parameters"][0] == {
        "parameterId": "limitEulerConeAngleMax",
        "expression": "0.610865238198 rad",
    }

    reader = STEPControl_Reader()
    assert reader.ReadFile(str(output)) == IFSelect_ReturnStatus.IFSelect_RetDone


def test_ball_cone_limit_keeps_onshape_semantics(tmp_path):
    """The Onshape cone parameter stays exact instead of becoming Euler limits."""

    assembly, first, second = connector_assembly()
    assembly.add_mate(
        BallMate(
            "ball",
            first,
            second,
            limits={"swing": MateLimit(0, 27.5)},
            onshape_parameters=[
                {
                    "type": 149,
                    "parameterId": "limitEulerConeAngleMax",
                    "expression": "27.5 deg",
                    "value": 0.479965544298,
                }
            ],
        ),
        solve=False,
    )
    output = tmp_path / "ball.step"

    export_step(assembly, output)
    mate = read_step_kinematics(output.read_bytes())["mates"][0]

    assert mate["onshape"]["values"]["limitEulerConeAngleMax"] == 27.5
    assert mate["onshape"]["parameters"][0]["expression"] == "27.5 deg"
    assert "conical swing limit" in mate["ap242"]["extensionReasons"][0]


def test_pair_placements_include_offset_and_axis_alignment(tmp_path):
    """Native pair frames incorporate offset, flip, and secondary reorientation."""

    assembly, first, second = connector_assembly()
    mate = RevoluteMate(
        "offset hinge",
        first,
        second,
        offset=MateOffset((0, 0, 3), (10, 20, 30)),
        flip_primary=True,
        reorient_secondary=3,
    )
    assembly.add_mate(mate, solve=False)
    output = tmp_path / "offset.step"

    export_step(assembly, output)
    stored = read_step_kinematics(output.read_bytes())["mates"][0]

    assert (
        stored["connectors"][1]["relativeTransform"] != stored["ap242"]["placements"][1]
    )
    assert stored["offset"]["translation"] == [0, 0, 3]
    assert stored["offset"]["rotation"] == [10, 20, 30]
    assert stored["flipPrimary"] is True
    assert stored["reorientSecondary"] == 3


def test_group_mate_expands_to_rigid_pairs(tmp_path):
    """Each additional Group member is connected by a native rigid pair."""

    components = []
    for index in range(3):
        component = Box(1, 1, 1).moved(Location((index * 2, 0, 0)))
        component.label = f"part {index}"
        components.append(component)
    assembly = Assembly(components, label="group mechanism")
    assembly.add_mate(GroupMate("group", components), solve=False)
    output = tmp_path / "group.step"

    export_step(assembly, output)
    text = output.read_text()

    assert text.count("FULLY_CONSTRAINED_PAIR(") == 2
    assert read_step_kinematics(text)["mates"][0]["relativeTransforms"]


def test_lossless_round_trip_restores_relation_and_raw_parameters(tmp_path):
    """build123d rehydrates mate intent that generic AP242 cannot represent."""

    assembly, first, second = connector_assembly()
    mate = CylindricalMate(
        "cylinder",
        first,
        second,
        limits={"tz": (-5, 8), "rz": (-180, 180)},
        onshape_parameters=[
            {"parameterId": "limitsEnabled", "value": True},
            {"parameterId": "limitZMin", "expression": "-0.5 cm"},
        ],
    )
    mate.set_value("tz", 2)
    mate.set_value("rz", 30)
    assembly.add_mate(mate, solve=False)
    relation = ScrewRelation(
        "lead",
        mate,
        1.25,
        reverse=True,
        onshape_parameters=[
            {"parameterId": "relationType", "value": "SCREW"},
            {"parameterId": "pitch", "expression": "1.25 mm"},
        ],
    )
    relation._phase = 0.125
    assembly.add_relation(relation, solve=False)
    output = tmp_path / "roundtrip.step"

    export_step(assembly, output)
    restored = import_step_assembly(output)

    assert isinstance(restored, Assembly)
    assert restored.label == assembly.label
    assert restored.is_fixed(restored.component("base"))
    assert isinstance(restored.mate("cylinder"), CylindricalMate)
    restored_mate = restored.mate("cylinder")
    assert restored_mate.values == mate.values
    assert restored_mate.limits == mate.limits
    assert restored_mate.onshape_parameters == mate.onshape_parameters
    restored_relation = restored.relation("lead")
    assert isinstance(restored_relation, ScrewRelation)
    assert restored_relation.travel_per_revolution == 1.25
    assert restored_relation.reverse is True
    assert restored_relation._phase == 0.125
    assert restored_relation.onshape_parameters == relation.onshape_parameters


def test_bytes_io_and_opt_out():
    """Kinematics support works in memory and remains explicitly optional."""

    assembly, first, second = connector_assembly()
    assembly.add_mate(RevoluteMate("hinge", first, second), solve=False)
    stream = BytesIO()

    export_step(assembly, stream)

    assert read_step_kinematics(stream.getvalue()) is not None
    assert b"REVOLUTE_PAIR_WITH_RANGE" in stream.getvalue()

    without_kinematics = BytesIO()
    export_step(assembly, without_kinematics, write_kinematics=False)
    assert read_step_kinematics(without_kinematics.getvalue()) is None
    assert b"KINEMATIC_LINK" not in without_kinematics.getvalue()


def test_binary_file_handle_supports_kinematics(tmp_path):
    """Kinematics post-processing supports generic writable binary streams."""

    assembly, first, second = connector_assembly()
    assembly.add_mate(RevoluteMate("hinge", first, second), solve=False)
    output = tmp_path / "stream.step"

    with output.open("wb") as stream:
        export_step(assembly, stream)

    data = output.read_bytes()
    assert read_step_kinematics(data) is not None
    assert b"REVOLUTE_PAIR_WITH_RANGE" in data


def test_payload_decompression_is_bounded(monkeypatch):
    """Compressed metadata cannot expand beyond the configured size limit."""

    monkeypatch.setattr(step_kinematics, "MAX_KINEMATICS_PAYLOAD_BYTES", 128)
    payload = step_kinematics.encode_kinematics_payload(
        {"$schema": step_kinematics.MANIFEST_SCHEMA, "padding": "x" * 1024}
    )

    with pytest.raises(ValueError, match="exceeds size limit"):
        step_kinematics.decode_kinematics_payload(payload)


def test_manifest_records_relation_loss_boundary():
    """The manifest makes every standard-versus-extension boundary explicit."""

    assembly, first, second = connector_assembly()
    mate = CylindricalMate("cylinder", first, second)
    assembly.add_mate(mate, solve=False)
    assembly.add_relation(ScrewRelation("lead", mate, 2), solve=False)

    record = assembly_to_kinematics(assembly)["relations"][0]

    assert record["ap242"]["pairType"] is None
    assert record["ap242"]["extensionReasons"]
