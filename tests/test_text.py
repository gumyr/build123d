"""
build123d Font and Text Utilities tests

name: test_text.py
by:   jwagenet
date: July 28th 2025

desc: Unit tests for the build123d font and text module
"""

import unittest
from pathlib import Path

from OCP.TCollection import TCollection_AsciiString

from build123d import available_fonts, FontStyle
from build123d.text import FONT_ASPECT, FontInfo, FontManager


class TestFontManager(unittest.TestCase):
    """Tests for FontManager."""

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

    def test_register_system_fonts(self):
        """Expected to register at least as many fonts from before.
        May find more on Windows
        """
        manager = FontManager()
        available_before = manager.available_fonts()

        manager.manager.RemoveFontAlias(
            TCollection_AsciiString("singleline"),
            TCollection_AsciiString("Relief SingleLine CAD"),
        )
        manager.manager.ClearFontDataBase()
        manager.register_system_fonts()

        # add bundled fonts back in
        manager.__init__()

        available_after = manager.available_fonts()
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


if __name__ == "__main__":
    unittest.main()