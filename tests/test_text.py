"""
build123d Font and Text Utilities tests

name: test_text.py
by:   jwagenet
date: July 28th 2025

desc: Unit tests for the build123d font and text module
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fontTools.ttLib import TTCollection, TTFont, newTable
from fontTools.ttLib.tables._f_v_a_r import NamedInstance
from OCP.TCollection import TCollection_AsciiString

from build123d import available_fonts, FontStyle
from build123d.text import FONT_ASPECT, FontInfo, FontManager


class TestFontManager(unittest.TestCase):
    """Tests for FontManager."""

    def tearDown(self):
        """Restore font database for subsequent tests in the same worker."""
        manager = FontManager()
        manager.register_system_fonts()
        manager.__init__()
    
    def test_persistence(self):
        """OCP FontMgr expected to persist db over multiple instances"""
        instance1 = FontManager()
        instance1.manager.ClearFontDataBase()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")

        font_name = instance1.bundled_fonts[0][1]
        font_path = (working_path.parent / src_path / instance1.bundled_path / font_name)

        instance1.register_font(str(font_path))

        instance2 = FontManager()
        self.assertEqual(instance1.available_fonts(), instance2.available_fonts())

    def test_register_font(self):
        """Expected to return system font with matching name if it exists"""
        manager = FontManager()
        manager.manager.ClearFontDataBase()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")

        font_name = manager.bundled_fonts[0][1]
        font_path = (working_path.parent / src_path / manager.bundled_path / font_name).resolve()

        font_names = manager.register_font(str(font_path))

        result = manager.find_font(font_names[0], FontStyle.REGULAR)
        self.assertEqual(font_names[0], result.FontName().ToCString())

    def test_register_font_collection_with_ttf_extension(self):
        """A collection stored with a .ttf extension should still register.

        Some system fonts (e.g. Windows ``arplukai.ttf``) contain a TrueType
        Collection despite their extension, so ``register_font`` must not rely on
        the extension alone.
        """
        manager = FontManager()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")
        font_name = manager.bundled_fonts[0][1]
        font_path = (
            working_path.parent / src_path / manager.bundled_path / font_name
        ).resolve()

        # Build a TrueType Collection but save it with a .ttf extension.
        collection = TTCollection()
        collection.fonts = [TTFont(str(font_path))]

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_ttf = Path(tmp_dir) / "collection_as.ttf"
            collection.save(str(fake_ttf))

            font_names = manager.register_font(str(fake_ttf))

        self.assertTrue(font_names)

    def _bundled_font(self, index: int) -> TTFont:
        manager = FontManager()
        font_path = (
            Path(__file__).resolve().parent.parent
            / "src/build123d"
            / manager.bundled_path
            / manager.bundled_fonts[index][1]
        )
        return TTFont(str(font_path))

    def test_font_faces_keep_their_place_in_a_collection(self):
        """Issue #1485: the second font of a collection is face 1, not face 0."""
        manager = FontManager()
        collection = TTCollection()
        collection.fonts = [self._bundled_font(0), self._bundled_font(0)]

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = str(Path(tmp_dir) / "two_fonts.ttc")
            collection.save(path)

            with patch.object(
                manager, "_get_font_faces", wraps=manager._get_font_faces
            ) as get_faces:
                self.assertTrue(manager.register_font(path))
            self.assertEqual(
                [call.args[2] for call in get_faces.call_args_list], [0, 1]
            )

        for face_index in (0, 1):
            (face,) = manager._get_font_faces(
                collection.fonts[face_index], "two_fonts.ttc", face_index
            )
            aspect = next(a for a in FONT_ASPECT.values() if face.HasFontAspect(a))
            self.assertEqual(face.FontFaceId(aspect), face_index)

    def test_font_faces_of_a_variable_font(self):
        """Issue #1485: one face per named instance, numbered from 1 in the
        font's order, however many languages name each instance."""
        font = self._bundled_font(0)
        family = FontManager()._get_font_faces(font, "plain.ttf")[0].FontName()

        names = font["name"]
        for name_id, english, german in (
            (256, "Light", "Leicht"),
            (257, "Black", "Schwarz"),
        ):
            names.setName(german, name_id, 3, 1, 0x407)
            names.setName(english, name_id, 3, 1, 0x409)
        fvar = newTable("fvar")
        fvar.axes = []
        fvar.instances = []
        for name_id in (257, 256):  # listed Black first, then Light
            instance = NamedInstance()
            instance.subfamilyNameID = name_id
            instance.coordinates = {}
            fvar.instances.append(instance)
        font["fvar"] = fvar

        faces = FontManager()._get_font_faces(font, "variable.ttf", 3)
        found = []
        for face in faces:
            aspect = next(a for a in FONT_ASPECT.values() if face.HasFontAspect(a))
            found.append((face.FontName().ToCString(), face.FontFaceId(aspect)))
        base = family.ToCString()
        self.assertEqual(found[0], (base, 3))
        self.assertEqual(len(found), 3)
        self.assertEqual(
            [face_id for _, face_id in found[1:]], [3 | (1 << 16), 3 | (2 << 16)]
        )
        # the first record of each name is used, as for the family name
        self.assertEqual(found[1][0], f"{base} Schwarz")
        self.assertEqual(found[2][0], f"{base} Leicht")

    def test_register_corrupt_font(self):
        """A malformed font is skipped with a warning."""
        manager = FontManager()

        with tempfile.TemporaryDirectory() as tmp_dir:
            corrupt_font = Path(tmp_dir) / "corrupt.ttf"
            corrupt_font.write_bytes(b"not a font")

            with self.assertLogs("build123d", level="WARNING") as logs:
                font_names = manager.register_font(str(corrupt_font))

        self.assertEqual(font_names, [])
        self.assertIn(str(corrupt_font), "".join(logs.output))

    def test_register_missing_font(self):
        """A missing font remains an error rather than being silently skipped."""
        manager = FontManager()

        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_font = Path(tmp_dir) / "missing.ttf"
            with self.assertRaises(FileNotFoundError):
                manager.register_font(str(missing_font))

    def test_register_folder(self):
        """Expected to register fonts in folder"""
        manager = FontManager()
        manager.manager.ClearFontDataBase()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")

        font_name = manager.bundled_fonts[0][0]
        font_file = Path(manager.bundled_fonts[0][1])
        font_folder = font_file.parent

        folder_path = (working_path.parent / src_path / manager.bundled_path / font_folder).resolve()

        font_names = manager.register_folder(str(folder_path))

        result = manager.find_font(font_names[0], FontStyle.REGULAR)
        self.assertEqual(font_name, result.FontName().ToCString())

    def test_register_folder_skips_corrupt_font(self):
        """A corrupt font does not prevent valid fonts from registering."""
        manager = FontManager()
        manager.manager.ClearFontDataBase()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")
        font_name, font_file, _ = manager.bundled_fonts[0]
        font_path = (
            working_path.parent / src_path / manager.bundled_path / font_file
        ).resolve()

        with tempfile.TemporaryDirectory() as tmp_dir:
            font_folder = Path(tmp_dir)
            TTFont(str(font_path)).save(font_folder / "valid.ttf")
            (font_folder / "corrupt.ttf").write_bytes(b"not a font")

            with self.assertLogs("build123d", level="WARNING"):
                font_names = manager.register_folder(str(font_folder))

        self.assertIn(font_name, font_names)

    def test_register_system_fonts(self):
        """Re-registering the system fonts finds them all again.

        The OCCT font manager is a process wide singleton whose content depends
        on what ran before (OCCT's own scan, other tests), so both counts are
        taken from the same reset state.
        """
        manager = FontManager()

        def reset_fonts():
            manager.manager.RemoveFontAlias(
                TCollection_AsciiString("singleline"),
                TCollection_AsciiString("Relief SingleLine CAD"),
            )
            manager.manager.ClearFontDataBase()
            manager.register_system_fonts()
            manager.__init__()  # add bundled fonts back in

        reset_fonts()
        available_before = manager.available_fonts()
        reset_fonts()
        available_after = manager.available_fonts()
        self.assertTrue(available_after)
        self.assertGreaterEqual(len(available_after), len(available_before))

    def test_check_font(self):
        """Expected to return system font with matching path if it exists or None"""
        manager = FontManager()

        working_path = Path(__file__).resolve().parent
        src_path = Path("src/build123d")

        font_name = manager.bundled_fonts[0][1]
        good_path = (working_path.parent / src_path / manager.bundled_path / font_name).resolve()

        good_font = manager.check_font(str(good_path))
        bad_font = manager.check_font(font_name)

        aspect = FONT_ASPECT[FontStyle.REGULAR]

        self.assertEqual(str(good_path), good_font.FontPath(aspect).ToCString())
        self.assertIsNone(bad_font)

    def test_find_font(self):
        """Expected to return font with matching name if it exists"""
        manager = FontManager()

        good_name = manager.bundled_fonts[0][0]
        good_font = manager.find_font(good_name, FontStyle.REGULAR)
        bad_font = manager.find_font("build123d", FontStyle.REGULAR)

        self.assertEqual(good_name, good_font.FontName().ToCString())
        self.assertNotEqual("build123d", bad_font.FontName().ToCString())


class TestFontHelpers(unittest.TestCase):
    """Tests for font helpers."""

    def test_font_info(self):
        """Test expected FontInfo repr."""
        name = "Arial"
        styles = tuple(member for member in FontStyle)
        font = FontInfo(name, styles)

        self.assertEqual(
            repr(font),
            f"Font(name={name!r}, styles={tuple(s.name for s in styles)})",
        )

    def test_available_fonts(self):
        """Test expected output for available fonts."""
        fonts = available_fonts()
        self.assertIsInstance(fonts, list)

        for font in fonts:
            self.assertIsInstance(font, FontInfo)
            self.assertIsInstance(font.name, str)
            self.assertIsInstance(font.styles, tuple)
            for style in font.styles:
                self.assertIsInstance(style, FontStyle)

        names = [font.name for font in fonts]
        self.assertEqual(names, sorted(names))

    def test_available_fonts_initializes_manager_when_called(self):
        """Font discovery should be deferred until the helper is called."""
        expected_fonts = []

        with patch("build123d.text.FontManager") as manager:
            manager.return_value.available_fonts.return_value = expected_fonts

            self.assertIs(available_fonts(), expected_fonts)
            manager.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
