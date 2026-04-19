"""
Material Tests

name: test_materials.py
by:   Bernhard Walter
date: April 9th 2026

desc: Test the build123d Material class — mass/volume, properties, and glTF export.

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

import pymat
from pygltflib import GLTF2
from threejs_materials import PbrProperties

from build123d.build_enums import Unit
from build123d.build_constants import G_PER_LB
from build123d.exporters3d import export_gltf
from build123d.geometry import Material, set_units
from build123d.objects_part import Box, Sphere
from build123d import Color

BRASS = getattr(pymat, "brass")

# Read brass properties from pymat directly
BRASS_DENSITY_G_CM3 = BRASS.properties.mechanical.density
BRASS_YOUNGS_MODULUS = BRASS.properties.mechanical.youngs_modulus
BRASS_MELTING_POINT = BRASS.properties.thermal.melting_point
BRASS_PBR_BASE_COLOR = BRASS.properties.pbr.base_color
BRASS_PBR_METALLIC = BRASS.properties.pbr.metallic
BRASS_PBR_ROUGHNESS = BRASS.properties.pbr.roughness
BRASS_PBR_IOR = BRASS.properties.pbr.ior

WOOD_DENSITY_G_CM3 = 0.65  # g/cm^3 — custom, not from pymat

# Geometry: build123d models in mm
BOX_VOLUME_MM3 = 10 * 20 * 30  # 6000 mm^3
SPHERE_VOLUME_MM3 = 4 / 3 * math.pi * 10**3  # ~4188.79 mm^3

# Independent unit conversions for verifying compute_mass
# pymat density is g/cm^3.  We convert volume and density independently
# to the target unit system, then multiply.
#
# (MM, G):  volume mm^3, density g/cm^3 → g/mm^3 (÷1000), mass = vol_mm3 * dens_g_mm3
# (M, KG):  volume m^3, density kg/m^3 (×1000), mass = vol_m3 * dens_kg_m3
# (IN, LB): volume in^3, density lb/in^3, mass = vol_in3 * dens_lb_in3


def expected_mass(
    volume: float, density_g_cm3: float, length_unit: str, mass_unit: str
) -> float:
    """Compute expected mass from volume and density.

    OCCT is unit-agnostic: Box(10,20,30).volume == 6000 always.
    The interpretation depends on length_unit:
      - MM: volume is 6000 mm^3
      - M:  volume is 6000 m^3
      - IN: volume is 6000 in^3

    Density from pymat is always g/cm^3.  We convert it to mass_unit/length_unit^3.
    """
    # cm per one length_unit
    cm_per_unit = {"mm": 0.1, "m": 100, "in": 2.54}[length_unit]
    # grams per one mass_unit
    g_per_unit = {"g": 1, "kg": 1000, "lb": G_PER_LB}[mass_unit]

    # density in mass_unit / length_unit^3
    density = density_g_cm3 * (cm_per_unit**3) / g_per_unit
    return volume * density


class TestMaterialMass(unittest.TestCase):
    """Test mass and volume calculations with materials and unit conversions."""

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = Material(BRASS)

        self.sphere = Sphere(10)
        self.sphere.material = Material.create("wood", density=WOOD_DENSITY_G_CM3)

    def tearDown(self):
        set_units(Unit.MM, Unit.G)

    def test_string_material(self):
        box = Box(10, 20, 30)
        box.material = "brass"
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_string_material_class(self):
        box = Box(10, 20, 30)
        box.material = Material("brass")
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_invalid_name(self):
        box = Box(10, 20, 30)
        with self.assertRaises(ValueError):
            box.material = Material("does not exist")

    def test_invalid_type(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = Material(False)

    def test_volume_mm(self):
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME_MM3, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME_MM3, 6)

    def test_mass_g(self):
        """Default units (MM, G): mass in grams."""
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME_MM3, WOOD_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_mass_kg(self):
        """Units (M, KG): mass in kilograms."""
        set_units(Unit.M, Unit.KG)
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "m", "kg"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME_MM3, WOOD_DENSITY_G_CM3, "m", "kg"),
            6,
        )

    def test_mass_lb(self):
        """Units (IN, LB): mass in pounds."""
        set_units(Unit.IN, Unit.LB)
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "in", "lb"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME_MM3, WOOD_DENSITY_G_CM3, "in", "lb"),
            6,
        )

    def test_volume_unchanged_by_units(self):
        """Volume is always in mm^3 regardless of unit settings."""
        set_units(Unit.M, Unit.KG)
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME_MM3, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME_MM3, 6)

        set_units(Unit.IN, Unit.LB)
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME_MM3, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME_MM3, 6)

    def test_shell(self):
        shell = self.box.shell()
        shell.material = "brass"
        self.assertAlmostEqual(
            shell.mass,
            expected_mass(BOX_VOLUME_MM3, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )


class TestMaterialProperties(unittest.TestCase):
    """Test that Material properties correctly expose pymat and threejs_materials
    data.
    """

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = Material(
            BRASS,
            pbr=PbrProperties.create(
                id="test_brass",
                ior=1.5,
                color=(0.88, 0.78, 0.5),
                metalness=1.0,
                roughness=0.25,
            ),
        )

        self.sphere = Sphere(10)
        self.sphere.material = Material.create("wood", density=WOOD_DENSITY_G_CM3)

    def test_invalid(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = Material(BRASS, pbr="not valid")

    def test_default_fallback_string(self):
        box = Box(10, 20, 30)
        with self.assertWarns(UserWarning):
            box.material = "does not exist"
        self.assertEqual(box.material._material.name, "PLA (Polylactic Acid)")

    def test_default_fallback_unknown(self):
        box = Box(10, 20, 30)
        with self.assertWarns(UserWarning):
            box.material = (1, 2, 3)
        self.assertEqual(box.material._material.name, "PLA (Polylactic Acid)")

    def test_pbr_properties(self):
        box = Box(10, 20, 30)
        box.material = getattr(pymat, "brass")
        self.assertAlmostEqual(box.material.mechanical.density, BRASS_DENSITY_G_CM3, 6)

    def test_brass_mechanical(self):
        mat = self.box.material
        self.assertAlmostEqual(mat.mechanical.density, BRASS_DENSITY_G_CM3, 6)
        self.assertAlmostEqual(mat.mechanical.youngs_modulus, BRASS_YOUNGS_MODULUS, 6)
        self.assertAlmostEqual(mat.pbr.values.ior, 1.5, 6)
        self.assertAlmostEqual(mat.pbr.values.color[0], 0.88)

    def test_brass_thermal(self):
        mat = self.box.material
        self.assertAlmostEqual(mat.thermal.melting_point, BRASS_MELTING_POINT, 6)

    def test_brass_pbr_derived(self):
        """PBR properties should be derived from pymat when no explicit pbr is given."""
        pbr = self.box.material.pbr
        self.assertAlmostEqual(pbr.values.metalness, BRASS_PBR_METALLIC, 6)
        self.assertAlmostEqual(pbr.values.roughness, BRASS_PBR_ROUGHNESS, 6)
        self.assertAlmostEqual(pbr.values.ior, BRASS_PBR_IOR, 6)
        for i, expected in enumerate(BRASS_PBR_BASE_COLOR[:3]):
            self.assertAlmostEqual(pbr.values.color[i], expected, 6)

    def test_custom_material_density(self):
        mat = self.sphere.material
        self.assertAlmostEqual(mat.mechanical.density, WOOD_DENSITY_G_CM3, 6)

    def test_overwrite(self):
        b = Box(1, 1, 1)
        b.material = Material("pla", color=(1.0, 0.5, 0.25), density=10)
        self.assertAlmostEqual(b.material.mechanical.density, 10, 6)
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.5, 0.25], 6)

    def test_pc_all(self):
        b = Box(1, 1, 1)
        b.material = "pc"

        self.assertAlmostEqual(b.material.mechanical.density, 1.2, 6)
        self.assertEqual(b.material.thermal.melting_point, 267)
        self.assertAlmostEqual(b.material.optical.refractive_index, 1.58, 6)
        self.assertEqual(b.material.manufacturing.print_nozzle_temp, 260)
        self.assertEqual(b.material.sourcing.cost_per_kg_unit, "USD/kg")
        self.assertEqual(b.material.electrical.conductivity_unit, "S/m")
        self.assertTrue(b.material.compliance.food_safe)
        self.assertEqual(b.material.custom, {})

    def test_density_zero(self):
        b = Box(1, 1, 1)
        b.material = Material.create("test", density=0.0)
        with self.assertWarns(UserWarning):
            mass = b.mass
        self.assertAlmostEqual(mass, 0.0, 6)

    def test_color(self):
        b = Box(1, 1, 1)

        b.material = Material.create("test", density=0.0, color="red")
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.0, 0.0])

        b.material = Material.create("test", density=0.0, color="green")
        self.assertListEqual(b.material.pbr.values.color, [0.0, 0.5019608, 0.0])

        b.material = Material.create("test", density=0.0, color=(1.0, 0.5, 0.25))
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.5, 0.25])

        b.material = Material.create("test", density=0.0, color=Color((1.0, 0.5, 0.25)))
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.5, 0.25])

        b.material = Material.create(
            "test", density=0.0, color=Color((1.0, 0.5, 0.25, 0.5))
        )
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.5, 0.25])


class TestMaterialGltfExport(unittest.TestCase):
    """Test glTF export with materials."""

    def setUp(self):
        self.box = Box(10, 20, 30)
        self.box.material = Material(BRASS)
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
        with open("test.gltf", "r") as f:
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
        self.assertTrue(export_gltf(self.box, "test.glb"))
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
        export_gltf(self.box, "test.glb")
        gltf = GLTF2.load("test.glb")

        mat = gltf.materials[0]
        pbr = mat.pbrMetallicRoughness
        self.assertAlmostEqual(pbr.metallicFactor, BRASS_PBR_METALLIC, 6)
        self.assertAlmostEqual(pbr.roughnessFactor, BRASS_PBR_ROUGHNESS, 6)

        # Base color should reflect brass color
        base_color = pbr.baseColorFactor
        self.assertIsNotNone(base_color)
        for i, expected in enumerate(BRASS_PBR_BASE_COLOR[:3]):
            self.assertAlmostEqual(base_color[i], expected, 6)


if __name__ == "__main__":
    unittest.main()
