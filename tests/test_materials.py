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

import io
import json
import math
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pymat
from mat_vis_client import MatVisClient
import pytest
from PIL import Image
from pygltflib import GLTF2

from build123d.build_enums import Unit
from build123d.build_constants import G_PER_LB
from build123d.exporters3d import export_gltf
from build123d.geometry import Material, VisProperties, set_units
from build123d.objects_part import Box, Sphere
from build123d import Color

# ── Offline mat-vis mock ─────────────────────────────────────────
# Distinct RGB colors for each (source, material_id) used in tests.
# The color texture drives the interpolated color via align_color().
_FAKE_COLORS = {
    ("ambientcg", "Metal008"): (180, 170, 130),  # brass polished
    ("ambientcg", "Metal012"): (160, 160, 170),  # stainless brushed
    ("ambientcg", "Metal032"): (120, 130, 140),  # brushed steel
    ("ambientcg", "Metal049A"): (200, 200, 195),  # aluminum smooth
    ("ambientcg", "Metal049B"): (150, 150, 155),  # stainless dirty
    ("ambientcg", "Metal055A"): (190, 190, 190),  # aluminum machined
    ("ambientcg", "Wood095"): (180, 140, 100),  # wood
}
_DEFAULT_COLOR = (200, 200, 200)

_MOCK_MANIFEST = {
    "schema_version": 3,
    "release_tag": "v2026.04.0",
    "sources": {
        "ambientcg": {
            "catalog": "ambientcg.json",
            "tiers": {"1k": {"complete": True}},
        },
    },
}


def _make_png(rgb: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (4, 4), color=rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_PNG_CACHE: dict[tuple[str, str], bytes] = {
    key: _make_png(color) for key, color in _FAKE_COLORS.items()
}
_DEFAULT_PNG = _make_png(_DEFAULT_COLOR)


@pytest.fixture(autouse=True)
def offline_mat_vis(tmp_path):
    """Replace the mat-vis-client singleton with an offline mock.

    Pre-populates the manifest cache and returns per-material tiny PNGs
    so no network access is needed.
    """
    cache_dir = tmp_path / "mat-vis-cache"
    client = MatVisClient(tag="v2026.04.0", cache_dir=cache_dir)

    manifest_path = cache_dir / "v2026.04.0" / ".manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_MOCK_MANIFEST))

    def _get_png(source, material_id):
        return _PNG_CACHE.get((source, material_id), _DEFAULT_PNG)

    def fake_fetch_texture(source, material_id, _channel, **_kwargs):
        return _get_png(source, material_id)

    def fake_fetch_all_textures(source, material_id, **_kwargs):
        png = _get_png(source, material_id)
        return {"color": png, "normal": _DEFAULT_PNG, "roughness": _DEFAULT_PNG}

    client.fetch_texture = fake_fetch_texture
    client.fetch_all_textures = fake_fetch_all_textures

    with (
        patch("mat_vis_client._client", client),
        patch("mat_vis_client.get_client", return_value=client),
        patch("pymat.vis._shared_client", return_value=client),
    ):
        yield client


# ── Helpers ──────────────────────────────────────────────────────


#
# mass/volume calculation
#
BRASS = pymat["brass"]

# Read brass properties from pymat directly
BRASS_DENSITY_G_CM3 = BRASS.properties.mechanical.density
BRASS_YOUNGS_MODULUS = BRASS.properties.mechanical.youngs_modulus
BRASS_MELTING_POINT = BRASS.properties.thermal.melting_point
BRASS_PBR_BASE_COLOR = BRASS.vis.base_color
BRASS_PBR_METALLIC = BRASS.vis.metallic
BRASS_PBR_ROUGHNESS = BRASS.vis.roughness

WOOD_DENSITY_G_CM3 = 0.65  # g/cm^3 — custom, not from pymat

# Geometry: build123d models in mm
BOX_VOLUME = 10 * 20 * 30  # 6000
SPHERE_VOLUME = 4 / 3 * math.pi * 10**3  # ~4188.79


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
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_string_material_class(self):
        box = Box(10, 20, 30)
        box.material = Material("brass")
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_invalid_name(self):
        box = Box(10, 20, 30)
        with self.assertRaises(KeyError):
            box.material = Material("does not exist")

    def test_invalid_type(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = Material(False)

    def test_volume_mm(self):
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME, 6)

    def test_mass_g(self):
        """Default units (MM, G): mass in grams."""
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME, WOOD_DENSITY_G_CM3, "mm", "g"),
            6,
        )

    def test_mass_kg(self):
        """Units (M, KG): mass in kilograms."""
        set_units(Unit.M, Unit.KG)
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "m", "kg"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME, WOOD_DENSITY_G_CM3, "m", "kg"),
            6,
        )

    def test_mass_lb(self):
        """Units (IN, LB): mass in pounds."""
        set_units(Unit.IN, Unit.LB)
        self.assertAlmostEqual(
            self.box.mass,
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "in", "lb"),
            6,
        )
        self.assertAlmostEqual(
            self.sphere.mass,
            expected_mass(SPHERE_VOLUME, WOOD_DENSITY_G_CM3, "in", "lb"),
            6,
        )

    def test_volume_unchanged_by_units(self):
        """Volume value is independent of unit settings."""
        set_units(Unit.M, Unit.KG)
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME, 6)

        set_units(Unit.IN, Unit.LB)
        self.assertAlmostEqual(self.box.volume, BOX_VOLUME, 6)
        self.assertAlmostEqual(self.sphere.volume, SPHERE_VOLUME, 6)

    def test_shell(self):
        shell = self.box.shell()
        shell.material = "brass"
        self.assertAlmostEqual(
            shell.mass,
            expected_mass(BOX_VOLUME, BRASS_DENSITY_G_CM3, "mm", "g"),
            6,
        )


class TestMaterialProperties(unittest.TestCase):
    """Test that Material properties correctly expose pymat and threejs_materials
    data.
    """

    def setUp(self):
        # use existing py-materials material with custom visualisation properties
        self.box = Box(10, 20, 30)
        self.box.material = Material(
            BRASS, vis=VisProperties.from_ambientcg("Metal012")
        )

        # create new py-materials material
        self.sphere = Sphere(10)
        self.sphere.material = Material.create("wood", density=WOOD_DENSITY_G_CM3)

    def test_no_vis(self):
        """Material without vis source still produces pbr from pymat scalars."""
        self.assertIsNone(self.sphere.material._material.vis.source)
        self.assertIsNotNone(self.sphere.material.pbr)

    def test_invalid(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = Material.create("test", 0.5, vis="not valid")

    def test_default_fallback_string(self):
        box = Box(10, 20, 30)
        with self.assertRaises(KeyError):
            box.material = "does not exist"

    def test_default_fallback_unknown(self):
        box = Box(10, 20, 30)
        with self.assertRaises(TypeError):
            box.material = (1, 2, 3)

    def test_pbr_properties(self):
        box = Box(10, 20, 30)
        box.material = getattr(pymat, "brass")
        self.assertAlmostEqual(box.material.mechanical.density, BRASS_DENSITY_G_CM3, 6)

    def test_brass_mechanical(self):
        mat = self.box.material
        self.assertAlmostEqual(mat.mechanical.density, BRASS_DENSITY_G_CM3, 6)
        self.assertAlmostEqual(mat.mechanical.youngs_modulus, BRASS_YOUNGS_MODULUS, 6)
        self.assertIsNotNone(mat.pbr.values.color)

    def test_brass_thermal(self):
        mat = self.box.material
        self.assertAlmostEqual(mat.thermal.melting_point, BRASS_MELTING_POINT, 6)

    def test_brass_pbr_derived(self):
        pbr = self.box.material.pbr
        self.assertEqual(self.box.material.vis.source, "ambientcg")
        self.assertEqual(self.box.material.vis.material_id, "Metal012")
        # ior defaults to 1.5 in PbrProperties.from_pymat regardless of source.
        self.assertAlmostEqual(pbr.values.ior, 1.5, 6)
        self.assertIsNotNone(pbr.values.color)
        self.assertEqual(len(pbr.values.color), 3)

    def test_custom_material_density(self):
        mat = self.sphere.material
        self.assertAlmostEqual(mat.mechanical.density, WOOD_DENSITY_G_CM3, 6)

    def test_override(self):
        b = Box(1, 1, 1)
        b.material = Material("pla", color=(1.0, 0.5, 0.25))
        self.assertAlmostEqual(b.material.mechanical.density, 1.25, 6)
        # color= takes sRGB; PbrOverrides.color is sRGB-stored — passthrough.
        self.assertAlmostEqual(b.material.pbr.values.color[0], 1.0, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[1], 0.5, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[2], 0.25, 4)

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
        b.material = Material.create("test", 0.0)
        with self.assertWarns(UserWarning):
            mass = b.mass
        self.assertAlmostEqual(mass, 0.0, 6)

    def test_color(self):
        b = Box(1, 1, 1)

        b.material = Material(BRASS, color="red")
        self.assertListEqual(b.material.pbr.values.color, [1.0, 0.0, 0.0])

        b.material = Material(BRASS, color="green")
        # CSS "green" = #008000 = sRGB 0/128/0; stored as sRGB byte ratios.
        self.assertAlmostEqual(b.material.pbr.values.color[0], 0.0, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[1], 0.5019608, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[2], 0.0, 4)

        # Numeric tuple is passed through as sRGB (no gamma conversion).
        b.material = Material(BRASS, color=(1.0, 0.5, 0.25))
        self.assertAlmostEqual(b.material.pbr.values.color[0], 1.0, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[1], 0.5, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[2], 0.25, 4)

        b.material = Material(BRASS, color=Color((1.0, 0.5, 0.25, 1.0)))
        self.assertAlmostEqual(b.material.pbr.values.color[0], 1.0, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[1], 0.5, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[2], 0.25, 4)

        # Alpha on Color is dropped by color= (RGB-only).
        b.material = Material(BRASS, color=Color((1.0, 0.5, 0.25, 0.5)))
        self.assertAlmostEqual(b.material.pbr.values.color[0], 1.0, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[1], 0.5, 4)
        self.assertAlmostEqual(b.material.pbr.values.color[2], 0.25, 4)


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

        # baseColorFactor is the scalar multiplier; with a color texture
        # present, the glTF spec allows it to differ from the pymat scalar
        base_color = pbr.baseColorFactor
        self.assertIsNotNone(base_color)
        self.assertEqual(len(base_color), 4)


#
# Visualisation tests
#


def _color_str(color):
    return "".join([f"{int(round(c*255)):02x}" for c in tuple(color)])


class TestMaterialVisualisation(unittest.TestCase):
    """Test material visualisation: pymat finishes, vis_source/vis_name, PBR, color."""

    def _make(self, name):
        obj = Sphere(10)
        obj.label = name
        return obj

    def tearDown(self):
        Material.auto_set_color = False

    def test_pymat_string_no_auto_color(self):
        """Overload 1: Material assigned via string, auto_set_color=False."""
        Material.auto_set_color = False
        sb = self._make("test1")
        sb.material = "stainless"

        self.assertIsNone(sb.color)
        self.assertEqual(sb.material.mechanical.density, 8.0)
        # No finish kwarg given → vis.finish reflects pymat's default ("brushed").
        self.assertEqual(sb.material.vis.finish, "brushed")
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Metal012")

    def test_pymat_object_auto_color(self):
        """Overload 1: Material assigned via pymat object, auto_set_color=True."""
        Material.auto_set_color = True
        sb = self._make("test2")
        sb.material = pymat.aluminum

        self.assertEqual(_color_str(sb.color), "c8c8c3ff")  # from mock texture
        self.assertEqual(sb.material.mechanical.density, 2.7)
        # No finish kwarg given → vis.finish reflects pymat's default ("smooth").
        self.assertEqual(sb.material.vis.finish, "smooth")
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Metal049A")

    def test_pymat_string_with_finish(self):
        """Overload 1: Material string with explicit finish."""
        Material.auto_set_color = False
        sb = self._make("test3")
        sb.material = Material("stainless", finish="dirty")

        self.assertIsNone(sb.color)
        self.assertEqual(sb.material.mechanical.density, 8.0)
        self.assertEqual(sb.material.vis.finish, "dirty")
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Metal049B")

    def test_pymat_object_with_finish(self):
        """Overload 1: pymat object with explicit finish."""
        Material.auto_set_color = True
        sb = self._make("test4")
        sb.material = Material(pymat.aluminum, finish="machined")

        self.assertEqual(_color_str(sb.color), "bebebeff")
        self.assertEqual(sb.material.mechanical.density, 2.7)
        self.assertEqual(sb.material.vis.finish, "machined")
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Metal055A")

    def test_pymat_string_with_vis_override(self):
        """Overload 2: existing material with vis= replacing visualization."""
        Material.auto_set_color = True
        sb = self._make("test5")
        sb.material = Material("aluminum", vis=VisProperties.from_ambientcg("Metal032"))

        self.assertEqual(_color_str(sb.color), "78828cff")  # from mock texture
        self.assertEqual(sb.material.mechanical.density, 2.7)
        # vis= fully replaces visualization; the supplied vis carries source/id.
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Metal032")

    def test_custom_material_with_vis(self):
        """Overload 2: new material (name+density) with vis= replacing visualization."""
        Material.auto_set_color = True
        sb = self._make("test6")
        sb.material = Material.create(
            "wood", 0.45, vis=VisProperties.from_ambientcg("Wood095")
        )

        self.assertEqual(_color_str(sb.color), "b48c64ff")  # from mock texture
        self.assertEqual(sb.material.mechanical.density, 0.45)
        self.assertEqual(sb.material.vis.source, "ambientcg")
        self.assertEqual(sb.material.vis.material_id, "Wood095")
        self.assertIsNotNone(sb.material.pbr.values.color)
        self.assertEqual(sb.material.pbr.values.metalness, 0.0)
        self.assertEqual(sb.material.pbr.values.roughness, 0.5)
        self.assertEqual(sb.material.pbr.values.ior, 1.5)
        self.assertEqual(sb.material.pbr.values.transmission, 0.0)


class TestMaterialPbrCache(unittest.TestCase):
    """Material.pbr memoizes resolve() in Material._pbr_cache."""

    def setUp(self):
        Material._pbr_cache.clear()

    def tearDown(self):
        Material._pbr_cache.clear()

    def test_repeated_access_same_object(self):
        """Same Material returns the same PbrProperties on repeated .pbr access."""
        m = Material("brass")
        first = m.pbr
        self.assertIs(m.pbr, first)
        self.assertEqual(len(Material._pbr_cache), 1)

    def test_distinct_materials_share_cache(self):
        """Two Materials with equal vis fingerprints share one cache entry."""
        a = Material("brass")
        b = Material("brass")
        self.assertIs(a.pbr, b.pbr)
        self.assertEqual(len(Material._pbr_cache), 1)

    def test_override_creates_distinct_entry(self):
        """A vis override changes the cache key."""
        base = Material("brass")
        red = Material("brass", color="red")
        self.assertIsNot(base.pbr, red.pbr)
        self.assertEqual(len(Material._pbr_cache), 2)

    def test_finish_creates_distinct_entry(self):
        """Different pymat finish changes the cache key."""
        smooth = Material("aluminum", finish="smooth")
        machined = Material("aluminum", finish="machined")
        self.assertIsNot(smooth.pbr, machined.pbr)
        self.assertEqual(len(Material._pbr_cache), 2)

    def test_external_vis_cached(self):
        """VisProperties.from_ambientcg path is cached too."""
        a = Material(BRASS, vis=VisProperties.from_ambientcg("Metal012"))
        b = Material(BRASS, vis=VisProperties.from_ambientcg("Metal012"))
        self.assertIs(a.pbr, b.pbr)

    def test_cache_clear_forces_resolve(self):
        """Clearing the cache produces a freshly resolved object."""
        m = Material("brass")
        first = m.pbr
        Material._pbr_cache.clear()
        self.assertIsNot(m.pbr, first)


GLTF_PATH = (
    Path(__file__).parent / "assets" / "plywood-material" / "plywood_cube.gltf"
)
GLTF_MATERIAL_NAME = "Light Natural Plywood"


class TestVisPropertiesGltf(unittest.TestCase):
    """GLTF path of VisProperties: __init__ branch, factories, resolve, cache key."""

    def test_list_gltf_materials(self):
        names = VisProperties.list_gltf_materials(GLTF_PATH)
        self.assertIn(GLTF_MATERIAL_NAME, names)

    def test_list_gltf_materials_str_path(self):
        names = VisProperties.list_gltf_materials(str(GLTF_PATH))
        self.assertIn(GLTF_MATERIAL_NAME, names)

    def test_list_gltf_materials_missing(self):
        with self.assertRaises(ValueError):
            VisProperties.list_gltf_materials("/no/such/file.gltf")

    def test_list_gltf_materials_bad_extension(self):
        with self.assertRaises(ValueError):
            VisProperties.list_gltf_materials(__file__)

    def test_from_gltf(self):
        vis = VisProperties.from_gltf(GLTF_PATH, GLTF_MATERIAL_NAME)
        self.assertEqual(vis.source, "gltf")
        self.assertEqual(vis.material_id, GLTF_MATERIAL_NAME)
        # __init__ gltf branch: use_pymat forced off, tier forced to None.
        self.assertFalse(vis._use_pymat)
        self.assertIsNone(vis._tier)

    def test_from_gltf_missing(self):
        with self.assertRaises(ValueError):
            VisProperties.from_gltf("/no/such/file.glb", "x")

    def test_from_gltf_bad_extension(self):
        with self.assertRaises(ValueError):
            VisProperties.from_gltf(__file__, "x")

    def test_from_gltf_resolve(self):
        vis = VisProperties.from_gltf(GLTF_PATH, GLTF_MATERIAL_NAME)
        pbr = vis.resolve()
        self.assertIsNotNone(pbr)
        self.assertTrue(pbr.normalize_uvs)

    def test_gltf_cache_key(self):
        a = VisProperties.from_gltf(GLTF_PATH, GLTF_MATERIAL_NAME)
        b = VisProperties.from_gltf(GLTF_PATH, GLTF_MATERIAL_NAME)
        self.assertEqual(a.pbr_cache_key(), b.pbr_cache_key())
        self.assertEqual(a.pbr_cache_key()[0], "gltf")


class TestVisPropertiesFactories(unittest.TestCase):
    """Construction-only tests for the non-ambientcg factories."""

    def test_from_gpuopen_pymat(self):
        vis = VisProperties.from_gpuopen("Brass Satin")
        self.assertEqual(vis.source, "gpuopen")
        self.assertEqual(vis.material_id, "Brass Satin")
        self.assertTrue(vis._use_pymat)

    def test_from_gpuopen_threejs(self):
        vis = VisProperties.from_gpuopen("Brass Satin", use_pymat=False)
        self.assertEqual(vis.source, "gpuopen")
        self.assertFalse(vis._use_pymat)

    def test_from_polyhaven_pymat(self):
        vis = VisProperties.from_polyhaven("rough_plaster")
        self.assertEqual(vis.source, "polyhaven")
        self.assertEqual(vis.material_id, "rough_plaster")
        self.assertEqual(vis._tier, "1k")
        self.assertTrue(vis._use_pymat)

    def test_from_polyhaven_threejs(self):
        vis = VisProperties.from_polyhaven("rough_plaster", use_pymat=False)
        self.assertEqual(vis.source, "polyhaven")
        self.assertFalse(vis._use_pymat)

    def test_from_physicallybased_threejs(self):
        # physicallybased defaults to use_pymat=False, tier=None (no textures).
        vis = VisProperties.from_physicallybased("Aluminum")
        self.assertEqual(vis.source, "physicallybased")
        self.assertEqual(vis.material_id, "Aluminum")
        self.assertFalse(vis._use_pymat)
        self.assertIsNone(vis._tier)

    def test_from_physicallybased_pymat(self):
        vis = VisProperties.from_physicallybased("Aluminum", use_pymat=True)
        self.assertEqual(vis.source, "physicallybased")
        self.assertTrue(vis._use_pymat)
        self.assertIsNone(vis._tier)


class TestVisPropertiesTextureTransforms(unittest.TestCase):
    """texture_scale and texture_rotation override + resolve application."""

    def test_override_texture_scale(self):
        base = VisProperties.from_ambientcg("Metal012")
        scaled = base.override(texture_scale=(2.0, 3.0))
        self.assertEqual(scaled._texture_scale, (2.0, 3.0))
        # original is untouched
        self.assertIsNone(base._texture_scale)

    def test_override_texture_rotation(self):
        base = VisProperties.from_ambientcg("Metal012")
        rotated = base.override(texture_rotation=45.0)
        self.assertEqual(rotated._texture_rotation, 45.0)
        self.assertIsNone(base._texture_rotation)

    def test_override_both(self):
        base = VisProperties.from_ambientcg("Metal012")
        v = base.override(texture_scale=(2.0, 2.0), texture_rotation=30.0)
        self.assertEqual(v._texture_scale, (2.0, 2.0))
        self.assertEqual(v._texture_rotation, 30.0)

    def test_resolve_applies_scale(self):
        vis = VisProperties.from_ambientcg("Metal012").override(
            texture_scale=(2.0, 2.0)
        )
        pbr = vis.resolve()
        self.assertIsNotNone(pbr)

    def test_resolve_applies_rotation_only(self):
        # Rotation-only path: covers the (1.0, 1.0) fallback branch.
        vis = VisProperties.from_ambientcg("Metal012").override(texture_rotation=90.0)
        pbr = vis.resolve()
        self.assertIsNotNone(pbr)

    def test_resolve_applies_scale_and_rotation(self):
        vis = VisProperties.from_ambientcg("Metal012").override(
            texture_scale=(2.0, 2.0), texture_rotation=45.0
        )
        pbr = vis.resolve()
        self.assertIsNotNone(pbr)

    def test_cache_key_includes_rotation(self):
        a = VisProperties.from_ambientcg("Metal012").override(texture_rotation=10.0)
        b = VisProperties.from_ambientcg("Metal012").override(texture_rotation=20.0)
        self.assertNotEqual(a.pbr_cache_key(), b.pbr_cache_key())


class TestVisPropertiesRepr(unittest.TestCase):
    """__repr__ output for all branches."""

    def test_repr_basic(self):
        s = repr(VisProperties.from_ambientcg("Metal012"))
        self.assertIn("source=ambientcg", s)
        self.assertIn("'Metal012'", s)
        self.assertIn("tier='1k'", s)
        self.assertIn("use_pymat=True", s)

    def test_repr_gltf(self):
        s = repr(VisProperties.from_gltf(GLTF_PATH, GLTF_MATERIAL_NAME))
        self.assertIn("source=gltf", s)
        self.assertIn("path=", s)
        self.assertNotIn("tier=", s)

    def test_repr_with_overrides(self):
        vis = VisProperties.from_ambientcg("Metal012").override(roughness=0.3)
        self.assertIn("overrides=", repr(vis))

    def test_repr_with_texture_scale(self):
        vis = VisProperties.from_ambientcg("Metal012").override(texture_scale=(2, 2))
        self.assertIn("texture_scale=(2, 2)", repr(vis))

    def test_repr_with_texture_rotation(self):
        vis = VisProperties.from_ambientcg("Metal012").override(texture_rotation=45.0)
        self.assertIn("texture_rotation=45.0", repr(vis))


if __name__ == "__main__":
    unittest.main()
