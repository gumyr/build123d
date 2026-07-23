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

from bd_materials import FinishedMaterial, finishes, metals, plastics, wood
from bd_materials.core import Range
from pygltflib import GLTF2

from build123d.build_constants import G_PER_LB
from build123d.build_enums import Unit
from build123d.exporters3d import export_gltf
from build123d.objects_part import Box, Sphere

#
# mass/volume calculation
#

# Read densities straight from bd_materials (kg/m^3) so the tests track the
# library's own data rather than hard-coded numbers.
BRASS = metals.brass()
WALNUT = wood.walnut()
BRASS_DENSITY = BRASS.material.density  # kg/m^3
WALNUT_DENSITY = WALNUT.material.density  # kg/m^3

# Geometry: build123d models in mm; OCCT volume is unit-agnostic.
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

    def test_invalid_type_str(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = "brass"

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

    def test_metal_thermal(self):
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


class TestMaterialGltfExport(unittest.TestCase):
    """Test glTF export with materials."""

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
            gltf_json = json.loads(f.read())

        # Check that the node is named
        self.assertEqual(gltf_json["nodes"][0]["name"], "brass_box")

        # Load via pygltflib and verify material is present
        gltf = GLTF2.load("test.gltf")
        self.assertGreater(len(gltf.materials), 0)

        # Verify PBR metallic-roughness is set
        mat = gltf.materials[0]
        self.assertIsNotNone(mat.pbrMetallicRoughness)

    def test_export_glb_binary(self):
        """Export as .glb — should produce single binary file, no .bin."""
        self.assertTrue(export_gltf(self.box, "test.glb", binary=True))
        self.assertTrue(os.path.exists("test.glb"))
        self.assertFalse(os.path.exists("test.bin"))

        # Load via pygltflib and verify material is present
        gltf = GLTF2.load("test.glb")
        self.assertGreater(len(gltf.materials), 0)

        # Verify PBR metallic-roughness is set
        mat = gltf.materials[0]
        self.assertIsNotNone(mat.pbrMetallicRoughness)

    def test_gltf_pbr_values(self):
        """Verify injected PBR material values in the glTF output."""
        export_gltf(self.box, "test.glb", binary=True)
        gltf = GLTF2.load("test.glb")

        mat = gltf.materials[0]
        pbr = mat.pbrMetallicRoughness
        self.assertAlmostEqual(pbr.metallicFactor, BRASS.pbr.values.metalness, 6)
        self.assertAlmostEqual(pbr.roughnessFactor, BRASS.pbr.values.roughness, 6)

        # baseColorFactor is the scalar multiplier; with a color texture present,
        # the glTF spec allows it to differ from the bd_materials scalar.
        base_color = pbr.baseColorFactor
        self.assertIsNotNone(base_color)
        self.assertEqual(len(base_color), 4)


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


if __name__ == "__main__":
    unittest.main()
