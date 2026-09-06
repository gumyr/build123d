"""
Material Tests

name: test_materials.py
by:   Bernhard Walter
date: April 9th 2026

desc: Test build123d's material integration (bd_materials.FinishedMaterial) —
      mass/volume, material properties, glTF export, and visualisation.

license:

    Copyright 2026 Bernhard Walter

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

import json
import math
import os
import unittest

from bd_materials import (
    FinishedMaterial,
    canonical_name,
    finishes,
    metals,
    plastics,
    wood,
)
from bd_materials.core import Range
from OCP.Message import Message_ProgressRange
from OCP.RWGltf import RWGltf_CafReader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_VisMaterialPBR

from build123d.build_constants import G_PER_LB
from build123d.build_enums import Unit
from build123d.exporters3d import export_gltf
from build123d.objects_part import Box, Sphere
from build123d.topology import Compound

#
# mass/volume calculation
#

# Read densities straight from bd_materials (kg/m^3) so the tests track the
# library's own data rather than hard-coded numbers.
BRASS = metals.brass()
WALNUT = wood.walnut()
BRASS_DENSITY = BRASS.material.density  # kg/m^3
WALNUT_DENSITY = WALNUT.material.density  # kg/m^3

# Geometry: In build123d and OCCT volume is unit-agnostic.
BOX_VOLUME = 10 * 20 * 30  # 6000
SPHERE_VOLUME = 4 / 3 * math.pi * 10**3  # ~4188.79


# Independent unit conversion for verifying compute_mass.
# bd_materials density is kg/m^3.  We convert volume and density independently
# to the target unit system, then multiply — deliberately using a different
# route than compute_mass (explicit m-per-unit / kg-per-unit) so the test is a
# genuine cross-check, not a mirror of the implementation.
#
# (MM, G):  volume mm^3, density kg/m^3 → g/mm^3, mass = vol_mm3 * dens
# (M, KG):  volume m^3,  density kg/m^3,           mass = vol_m3  * dens
# (IN, LB): volume in^3, density kg/m^3 → lb/in^3, mass = vol_in3 * dens
def expected_mass(
    volume: float, density_kg_m3: float, length_unit: str, mass_unit: str
) -> float:
    """Compute expected mass from volume and density.

    OCCT is unit-agnostic: Box(10,20,30).volume == 6000 always.
    The interpretation depends on length_unit:
      - MM: volume is 6000 mm^3
      - M:  volume is 6000 m^3
      - IN: volume is 6000 in^3

    Density from bd_materials is always kg/m^3.  We convert it to
    mass_unit/length_unit^3.
    """
    # meters per one length_unit
    m_per_unit = {"mm": 0.001, "m": 1.0, "in": 0.0254}[length_unit]
    # kilograms per one mass_unit
    kg_per_unit = {"g": 0.001, "kg": 1.0, "lb": G_PER_LB / 1000}[mass_unit]

    # density in mass_unit / length_unit^3
    density = density_kg_m3 * (m_per_unit**3) / kg_per_unit
    return volume * density


class TestMaterialMass(unittest.TestCase):
    """Test mass and volume calculations with materials and unit conversions."""

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = metals.brass()

        self.sphere = Sphere(10)
        self.sphere.material = wood.walnut()

    def test_invalid_type_tuple(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = (1, 2, 3)

    def test_no_material_raises(self):
        """Mass without an assigned material raises (density missing)."""
        box = Box(10, 20, 30)
        with self.assertRaises(ValueError):
            _ = box.mass()

    def test_volume_mm(self):
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME, 6)

    def test_mass_g(self):
        """Default units (MM, G): mass in grams."""
        self.assertAlmostEqual(
            self.box.mass(),
            expected_mass(BOX_VOLUME, BRASS_DENSITY, "mm", "g"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass(),
            expected_mass(SPHERE_VOLUME, WALNUT_DENSITY, "mm", "g"),
            6,
        )

    def test_mass_kg(self):
        """Units (M, KG): mass in kilograms."""
        self.assertAlmostEqual(
            self.box.mass(Unit.KG, Unit.M),
            expected_mass(BOX_VOLUME, BRASS_DENSITY, "m", "kg"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass(Unit.KG, Unit.M),
            expected_mass(SPHERE_VOLUME, WALNUT_DENSITY, "m", "kg"),
            6,
        )

    def test_mass_lb(self):
        """Units (IN, LB): mass in pounds."""
        self.assertAlmostEqual(
            self.box.mass(Unit.LB, Unit.IN),
            expected_mass(BOX_VOLUME, BRASS_DENSITY, "in", "lb"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass(Unit.LB, Unit.IN),
            expected_mass(SPHERE_VOLUME, WALNUT_DENSITY, "in", "lb"),
            6,
        )

    def test_shell(self):
        # A manifold (closed) Shell reports its enclosed volume, so its mass
        # equals that of the solid it bounds.
        shell = self.box.shell()
        shell.material = metals.brass()
        self.assertAlmostEqual(
            shell.mass(),
            expected_mass(BOX_VOLUME, BRASS_DENSITY, "mm", "g"),
            6,
        )

    def test_finish_does_not_change_mass(self):
        """Applying a finish leaves the density (and thus mass) unchanged."""
        box = Box(10, 20, 30)
        box.material = metals.brass(finish=finishes.brushed())
        self.assertAlmostEqual(
            box.mass(),
            expected_mass(BOX_VOLUME, BRASS_DENSITY, "mm", "g"),
            6,
        )

    def test_custom_density(self):
        """A custom density scales the mass proportionally."""
        box = Box(10, 20, 30)
        box.material = metals.custom_metal("myalloy", 1234.0)
        self.assertAlmostEqual(
            box.mass(),
            expected_mass(BOX_VOLUME, 1234.0, "mm", "g"),
            6,
        )

    def test_density_zero(self):
        box = Box(1, 1, 1)
        box.material = metals.brass(density=0.0)
        with self.assertWarns(UserWarning):
            mass = box.mass()
        self.assertAlmostEqual(mass, 0.0, 6)


class TestMaterialProperties(unittest.TestCase):
    """Test that FinishedMaterial exposes bd_materials mechanical/thermal/pbr data."""

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = metals.brass()

        self.sphere = Sphere(10)
        self.sphere.material = wood.walnut()

    def test_metal_density(self):
        self.assertEqual(self.box.material.material.density, BRASS_DENSITY)

    def test_metal_mechanical_ranges(self):
        mat = self.box.material.material
        self.assertIsInstance(mat.tensile_strength, Range)
        self.assertLessEqual(mat.tensile_strength.min, mat.tensile_strength.max)
        self.assertIsInstance(mat.modulus_of_elasticity, Range)
        self.assertLessEqual(
            mat.modulus_of_elasticity.min, mat.modulus_of_elasticity.max
        )

    def test_metal_melt_temperature(self):
        mat = self.box.material.material
        self.assertIsInstance(mat.melting_temperature, Range)
        self.assertLessEqual(mat.melting_temperature.min, mat.melting_temperature.max)

    def test_wood_density(self):
        self.assertEqual(self.sphere.material.material.density, WALNUT_DENSITY)

    def test_plastic_properties(self):
        box = Box(1, 1, 1)
        box.material = plastics.pc()
        mat = box.material.material
        self.assertEqual(mat.density, 1200)
        self.assertIsInstance(mat.glass_transition_temperature, Range)

    def test_pbr_values(self):
        pbr = self.box.material.pbr
        self.assertEqual(len(pbr.values.color), 3)
        self.assertEqual(pbr.values.metalness, 1.0)
        self.assertEqual(pbr.values.roughness, 0.0)

    def test_custom_density_exposed(self):
        box = Box(1, 1, 1)
        box.material = metals.custom_metal("myalloy", 1234.0)
        self.assertEqual(box.material.material.density, 1234.0)
        self.assertEqual(box.material.material.name, "myalloy")


class TestMaterialByName(unittest.TestCase):
    """Assigning a material by name, resolved through bd_materials.resolve."""

    def test_name_gives_finished_material(self):
        box = Box(10, 20, 30)
        box.material = "brass"
        self.assertIsInstance(box.material, FinishedMaterial)
        self.assertEqual(canonical_name(box.material), "Brass_C360_HALF_HARD")

    def test_name_matches_factory(self):
        """A name and its factory produce the same material."""
        by_name = Box(10, 20, 30)
        by_name.material = "brass"
        by_factory = Box(10, 20, 30)
        by_factory.material = metals.brass()

        self.assertEqual(
            canonical_name(by_name.material), canonical_name(by_factory.material)
        )
        self.assertEqual(
            by_name.material.material.density, by_factory.material.material.density
        )
        self.assertAlmostEqual(by_name.mass(), by_factory.mass(), 6)

    def test_name_is_normalized(self):
        """Case, spaces and hyphens are all accepted."""
        for name in (
            "brass",
            "Brass",
            "BRASS",
            "brass_c360_half_hard",
            "Brass-C360-half hard",
        ):
            with self.subTest(name=name):
                box = Box(1, 1, 1)
                box.material = name
                self.assertEqual(canonical_name(box.material), "Brass_C360_HALF_HARD")

    def test_name_by_family_and_grade(self):
        """A family name and a specific grade both resolve."""
        family = Box(1, 1, 1)
        family.material = "walnut"
        self.assertEqual(canonical_name(family.material), "Hardwood_WALNUT")

        grade = Box(1, 1, 1)
        grade.material = "alu_g6061_t6"
        self.assertEqual(canonical_name(grade.material), "Alu_G6061_T6")

    def test_each_assignment_is_a_fresh_instance(self):
        """Per-part changes must not leak between shapes sharing a name."""
        first = Box(1, 1, 1)
        first.material = "brass"
        second = Box(1, 1, 1)
        second.material = "brass"

        self.assertIsNot(first.material, second.material)
        first.material.scale = (2.0, 2.0)
        self.assertEqual(second.material.scale, (1.0, 1.0))

    def test_name_sets_color(self):
        """The setter applies the resolved material's PBR color."""
        box = Box(1, 1, 1)
        box.material = "brass"
        expected = box.material.pbr.interpolate_color()
        self.assertIsNotNone(box.color)
        for channel, value in zip(tuple(box.color), expected):
            self.assertAlmostEqual(channel, value, 6)

    def test_unknown_name_raises(self):
        box = Box(1, 1, 1)
        with self.assertRaises(ValueError):
            box.material = "unobtainium"


def read_gltf(path: str) -> TDocStd_Document:
    """Read a .gltf or .glb back into an XCAF document with OCCT's own reader.

    Handles both the JSON and the binary container, so the tests need no glTF
    library and no hand-rolled .glb parsing.
    """
    doc = TDocStd_Document(TCollection_ExtendedString("gltf"))
    reader = RWGltf_CafReader()
    reader.SetDocument(doc)
    if not reader.Perform(TCollection_AsciiString(path), Message_ProgressRange()):
        raise RuntimeError(f"failed to read {path}")
    return doc


def gltf_shape_names(doc: TDocStd_Document) -> list[str]:
    """Names of the free shapes (the glTF nodes) in an XCAF document."""
    labels = TDF_LabelSequence()
    XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetFreeShapes(labels)
    names = []
    for i in range(1, labels.Length() + 1):
        name = TDataStd_Name()
        if labels.Value(i).FindAttribute(TDataStd_Name.GetID_s(), name):
            names.append(name.Get().ToExtString())
    return names


def srgb_to_linear(channel: float) -> float:
    """Convert one sRGB channel to linear (the standard sRGB EOTF).

    ``PbrValues.color`` is stored sRGB-encoded, while the glTF spec requires
    ``baseColorFactor`` in linear space.  Spelled out here rather than imported
    from threejs_materials so the test cross-checks the conversion instead of
    mirroring it.
    """
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def gltf_pbr_materials(doc: TDocStd_Document) -> list[XCAFDoc_VisMaterialPBR]:
    """Metallic-roughness material definitions in an XCAF document."""
    tool = XCAFDoc_DocumentTool.VisMaterialTool_s(doc.Main())
    labels = TDF_LabelSequence()
    tool.GetMaterials(labels)
    return [
        tool.GetMaterial_s(labels.Value(i)).PbrMaterial()
        for i in range(1, labels.Length() + 1)
    ]


class TestMaterialGltfExport(unittest.TestCase):
    """Test glTF export with materials.

    A .gltf is plain JSON, so its contents are asserted directly — that checks
    what was actually written to the file.  A .glb wraps the same JSON in a
    binary container; it is read back with OCCT's reader rather than parsed by
    hand.
    """

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = metals.brass()
        self.box.label = "brass_box"

    def tearDown(self):
        for f in ("test.gltf", "test.bin", "test.glb"):
            if os.path.exists(f):
                os.remove(f)

    def test_export_gltf_ascii(self):
        """Export as .gltf — should produce .gltf (JSON) and .bin (binary)."""
        self.assertTrue(export_gltf(self.box, "test.gltf"))
        self.assertTrue(os.path.exists("test.gltf"))
        self.assertTrue(os.path.exists("test.bin"))

        # Verify it's valid JSON
        with open("test.gltf", "r", encoding="utf-8") as f:
            json.load(f)

        doc = read_gltf("test.gltf")

        # Check that the node is named
        self.assertEqual(gltf_shape_names(doc), ["brass_box"])

        # Verify the material is present and PBR metallic-roughness is set
        materials = gltf_pbr_materials(doc)
        self.assertGreater(len(materials), 0)
        self.assertTrue(materials[0].IsDefined)

    def test_export_glb_binary(self):
        """Export as .glb — should produce single binary file, no .bin."""
        self.assertTrue(export_gltf(self.box, "test.glb", binary=True))
        self.assertTrue(os.path.exists("test.glb"))
        self.assertFalse(os.path.exists("test.bin"))

        # Verify the material is present and PBR metallic-roughness is set
        materials = gltf_pbr_materials(read_gltf("test.glb"))
        self.assertGreater(len(materials), 0)
        self.assertTrue(materials[0].IsDefined)

    def test_gltf_json_pbr_values(self):
        """Verify the PBR material values written into the .gltf JSON itself."""
        export_gltf(self.box, "test.gltf")
        with open("test.gltf", "r", encoding="utf-8") as f:
            gltf = json.load(f)

        self.assertEqual(gltf["nodes"][0]["name"], "brass_box")
        self.assertGreater(len(gltf["materials"]), 0)
        self.assertIn("pbrMetallicRoughness", gltf["materials"][0])

        # glTF omits metallicFactor/roughnessFactor when they equal the spec
        # default of 1.0
        pbr = gltf["materials"][0]["pbrMetallicRoughness"]
        self.assertAlmostEqual(
            pbr.get("metallicFactor", 1.0), BRASS.pbr.values.metalness, 6
        )
        self.assertAlmostEqual(
            pbr.get("roughnessFactor", 1.0), BRASS.pbr.values.roughness, 6
        )

        # baseColorFactor is the material's sRGB color converted to linear
        # space, plus opacity as alpha.  Read straight from the JSON, so it can
        # be compared at full double precision.
        base_color = pbr.get("baseColorFactor")
        self.assertIsNotNone(base_color)
        self.assertEqual(len(base_color), 4)
        for channel, srgb in zip(base_color, BRASS.pbr.values.color):
            self.assertAlmostEqual(channel, srgb_to_linear(srgb), 12)
        self.assertAlmostEqual(base_color[3], 1.0, 12)

    def test_glb_pbr_values(self):
        """Verify injected PBR material values read back from the .glb."""
        export_gltf(self.box, "test.glb", binary=True)
        pbr = gltf_pbr_materials(read_gltf("test.glb"))[0]

        self.assertAlmostEqual(pbr.Metallic, BRASS.pbr.values.metalness, 6)
        self.assertAlmostEqual(pbr.Roughness, BRASS.pbr.values.roughness, 6)

        # BaseColor is the material's sRGB color converted to linear space.
        # OCCT stores it as float32, hence the tolerance.
        rgb = pbr.BaseColor.GetRGB()
        for channel, srgb in zip(
            (rgb.Red(), rgb.Green(), rgb.Blue()), BRASS.pbr.values.color
        ):
            self.assertAlmostEqual(channel, srgb_to_linear(srgb), 6)
        self.assertAlmostEqual(pbr.BaseColor.Alpha(), 1.0, 6)


class TestMaterialTextureTransforms(unittest.TestCase):
    """FinishedMaterial texture scale/rotation and the pbr= override guard."""

    def test_default_transforms(self):
        fm = metals.brass()
        self.assertEqual(fm.scale, (1.0, 1.0))
        self.assertEqual(fm.rotation, 0.0)

    def test_scale_rotation(self):
        fm = FinishedMaterial(metals.brass().material, scale=(2.0, 3.0), rotation=45.0)
        self.assertEqual(fm.scale, (2.0, 3.0))
        self.assertEqual(fm.rotation, 45.0)

    def test_scale_rotation_in_repr(self):
        fm = FinishedMaterial(metals.brass().material, scale=(2.0, 2.0), rotation=30.0)
        r = repr(fm)
        self.assertIn("scale=(2.0, 2.0)", r)
        self.assertIn("rotation=30.0", r)

    def test_pbr_override_excludes_transforms(self):
        """pbr= is a full override and cannot be combined with scale/rotation."""
        with self.assertRaises(ValueError):
            FinishedMaterial(
                metals.brass().material, pbr=metals.brass().pbr, scale=(2.0, 2.0)
            )


class TestAssemblyMass(unittest.TestCase):
    """An assembly sums its children, so each contributes its own material."""

    def setUp(self):
        self.brass_block = Box(10, 10, 10).solid()
        self.brass_block.material = metals.brass()
        self.walnut_block = Box(10, 10, 10).solid()
        self.walnut_block.material = wood.walnut()
        self.expected = self.brass_block.mass() + self.walnut_block.mass()

    def test_children_keep_their_own_materials(self):
        assembly = Compound(
            label="assembly", children=[self.brass_block, self.walnut_block]
        )
        self.assertAlmostEqual(assembly.mass(), self.expected, 6)

    def test_a_child_without_a_material_inherits(self):
        plain = Box(10, 10, 10).solid()
        assembly = Compound(label="assembly", children=[self.brass_block, plain])
        assembly.material = wood.walnut()
        self.assertAlmostEqual(assembly.mass(), self.expected, 6)

    def test_nested_assemblies(self):
        inner = Compound(label="inner", children=[self.walnut_block])
        outer = Compound(label="outer", children=[self.brass_block, inner])
        self.assertAlmostEqual(outer.mass(), self.expected, 6)

    def test_a_compound_without_children_uses_its_own_material(self):
        """Sub-shapes of a plain Compound are topology, not build123d objects,
        so they can only take the Compound's material."""
        compound = Compound([Box(10, 10, 10).solid(), Box(10, 10, 10).solid()])
        compound.material = metals.brass()
        self.assertAlmostEqual(compound.mass(), 2 * self.brass_block.mass(), 6)


class TestMaterialInheritance(unittest.TestCase):
    """A part with no material of its own takes the nearest ancestor's."""

    def test_inherited_from_an_ancestor(self):
        part = Box(1, 1, 1).solid()
        assembly = Compound(label="assembly", children=[part])
        assembly.material = metals.brass()

        self.assertIs(part.material, assembly.material)
        # the walk caches the result so the next lookup is a straight read
        self.assertIsNotNone(part._material)

    def test_own_material_wins_over_the_ancestor(self):
        walnut = wood.walnut()
        part = Box(1, 1, 1).solid()
        part.material = walnut
        assembly = Compound(label="assembly", children=[part])
        assembly.material = metals.brass()

        self.assertIs(part.material, walnut)

    def test_no_material_anywhere_in_the_tree(self):
        part = Box(1, 1, 1).solid()
        Compound(label="assembly", children=[part])
        self.assertIsNone(part.material)


if __name__ == "__main__":
    unittest.main()
