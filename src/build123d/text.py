"""
build123d font and text objects

name: text.py
by:   jwagenet
date: July 28th 2025

desc:
    This python module contains font and text objects.

"""

import glob
import os
import platform
import sys
from dataclasses import dataclass

from fontTools.ttLib import TTFont, ttCollection  # type:ignore
from OCP.Font import (
    Font_FA_Bold,
    Font_FA_BoldItalic,
    Font_FA_Italic,
    Font_FA_Regular,
    Font_FontMgr,
    Font_SystemFont,
)
from OCP.TCollection import TCollection_AsciiString
from OCP.TColStd import TColStd_SequenceOfHAsciiString

from build123d.build_enums import FontStyle


FONT_ASPECT = {
    FontStyle.REGULAR: Font_FA_Regular,
    FontStyle.BOLD: Font_FA_Bold,
    FontStyle.ITALIC: Font_FA_Italic,
    FontStyle.BOLDITALIC: Font_FA_BoldItalic,
}


@dataclass(frozen=True)
class FontInfo:
    """Representation for registered font.

    Not immediately compatible with Font_SystemFont, which only contains a single
    style/aspect.
    """

    name: str
    styles: tuple[FontStyle, ...]

    def __repr__(self) -> str:
        style_names = tuple(s.name for s in self.styles)
        return f"Font(name={self.name!r}, styles={style_names})"


class FontManager:
    """Wrap OCP Font_FontMgr"""

    bundled_path = "data/fonts"
    bundled_fonts = [
        (
            "Relief SingleLine CAD",
            "reliefsingleline/ReliefSingleLineCAD-Regular.ttf",
            True,
        )
    ]

    def __init__(self):
        """Initialize FontManager

        Bundled fonts are added to global OCP instance if they haven't already
        """
        # Should clarify if this is necessary
        if sys.platform.startswith("linux"):
            os.environ["FONTCONFIG_FILE"] = "/etc/fonts/fonts.conf"
            os.environ["FONTCONFIG_PATH"] = "/etc/fonts/"

        self.manager = Font_FontMgr.GetInstance_s()

        # Check if OCP manager is already initialized. "singleline" alias is canary
        aliases = TColStd_SequenceOfHAsciiString()
        self.manager.GetAllAliases(aliases)
        aliases = [aliases.Value(i).ToCString() for i in range(1, aliases.Length() + 1)]

        if "singleline" not in aliases:
            if platform.system() == "Windows": # pragma: no cover
                # OCCT doesnt add user fonts on Windows
                self.register_system_fonts()

            working_path = os.path.dirname(os.path.abspath(__file__))
            for font in self.bundled_fonts:
                font_path = os.path.normpath(
                    os.path.join(working_path, self.bundled_path, font[1])
                )
                self.register_font(font_path, single_stroke=font[2])

            self.manager.AddFontAlias(
                TCollection_AsciiString("singleline"),
                TCollection_AsciiString("Relief SingleLine CAD"),
            )

    def available_fonts(self) -> list[FontInfo]:
        """Get list of available fonts by name and available styles (also called aspects)"""

        font_aspects = {
            "REGULAR": Font_FA_Regular,
            "BOLD": Font_FA_Bold,
            "BOLDITALIC": Font_FA_BoldItalic,
            "ITALIC": Font_FA_Italic,
        }

        font_list = []
        for f in self.manager.GetAvailableFonts():
            avail_aspects = tuple(
                FontStyle[n] for n, a in font_aspects.items() if f.HasFontAspect(a)
            )
            font_list.append(FontInfo(f.FontName().ToCString(), avail_aspects))

        font_list.sort(key=lambda x: x.name)

        return font_list

    def check_font(self, path: str) -> Font_SystemFont | None:
        """Check if font exists at path and return system font"""
        return self.manager.CheckFont(path)

    def find_font(self, name: str, style: FontStyle) -> Font_SystemFont:
        """Find font in FontManager library by name and style"""
        return self.manager.FindFont(TCollection_AsciiString(name), FONT_ASPECT[style])

    def register_font(
        self, path: str, override: bool = False, single_stroke=False
    ) -> list[str]:
        """Register all font faces in a font file and return font face names."""
        _, ext = os.path.splitext(path)
        if ext.strip(".") == "ttc": # pragma: no cover
            fonts = ttCollection.TTCollection(path)
        else:
            fonts = [TTFont(path)]

        font_faces = []
        for font in fonts:
            fonts = self._get_font_faces(font, path)
            for f in fonts:
                font_faces.append(f.FontName().ToCString())
                f.SetSingleStrokeFont(single_stroke)
                self.manager.RegisterFont(f, override)

        return font_faces

    def register_folder(
        self, path: str, override: bool = False, single_stroke=False
    ) -> list[str]:
        """Register all fonts in a folder"""
        exts = ["ttf", "otf", "ttc"]
        font_faces = []
        for ext in exts:
            search = os.path.join(os.path.normpath(path), "*" + ext)
            results = glob.glob(search)
            for result in results:
                font_faces += self.register_font(result, override, single_stroke)

        return list(set(font_faces))

    def register_system_fonts(self):
        """Runner to (re)inititalize the OCCT FontMgr font list since user folder is
        missing on Windows and some fonts may not be imported correctly."""

        if platform.system() == "Windows": # pragma: no cover
            user = os.getlogin()
            paths = [
                "C:/Windows/Fonts",
                f"C:/Users/{user}/AppData/Local/Microsoft/Windows/Fonts",
            ]
        elif platform.system() == "Darwin": # pragma: no cover
            # macOS
            paths = ["/System/Library/Fonts", "/Library/Fonts"]
        else:
            paths = [
                "/system/fonts", # Android
                "/usr/share/fonts",
                "/usr/local/share/fonts",
            ]

        for path in paths:
            self.register_folder(path)

    def _get_font_faces(self, ft_font: TTFont, path: str) -> list[Font_SystemFont]: # pragma: no cover
        """Extract font info from font files and return list of font object."""

        family, sub, preferred = "", "", ""
        for record in ft_font["name"].names:
            try:
                value = record.toUnicode()
            except:
                continue

            if record.nameID == 1 and family == "":
                family = value
            elif record.nameID == 2 and sub == "":
                sub = value
            elif record.nameID == 16 and preferred == "":
                preferred = value

        family = preferred if preferred != "" else family

        if "fvar" in ft_font:
            sub_ids = [i.subfamilyNameID for i in ft_font["fvar"].instances]
            subfamilies = []
            for record in ft_font["name"].names:
                if record.nameID in sub_ids:
                    subfamilies.append(record.toUnicode())

        else:
            subfamilies = [sub]

        # Replicate OCCT font aspect substitution rules, but make them correct
        # - OCCT treats "Oblique" as "Italic", which seems fine
        # - OCCT treats "Book" as "Regular", which is wrong
        aspects = ["Regular", "Bold", "Italic", "Oblique"]
        fonts: list[Font_SystemFont] = []
        for i, subfamily in enumerate(subfamilies):
            labels = subfamily.split()
            matches = {aspect for aspect in aspects if aspect in labels}

            if "Bold" in matches:
                labels = [
                    label
                    for label in labels
                    if label not in ("Bold", "Italic", "Oblique")
                ]
                if "Italic" in matches or "Oblique" in matches:
                    aspect = Font_FA_BoldItalic
                else:
                    aspect = Font_FA_Bold
            elif "Italic" in matches or "Oblique" in matches:
                labels = [
                    label for label in labels if label not in ("Italic", "Oblique")
                ]
                aspect = Font_FA_Italic
            else:
                labels = [] if "Regular" in matches else labels
                aspect = Font_FA_Regular

            subfamily = " ".join(labels)
            font_name = " ".join([family, subfamily]) if subfamily != "" else family
            font_name = font_name.strip()

            ocp_font = Font_SystemFont(TCollection_AsciiString(font_name))
            ocp_font.SetFontPath(aspect, TCollection_AsciiString(path), i << 16)
            try:
                # Some fonts have bad unicode characters in their name and I couldn't
                # figure out how to fix them. Skipping these fonts for now
                ocp_font.SetSingleStrokeFont(
                    ocp_font.FontKey().ToCString().startswith("olf ")
                )
            except UnicodeDecodeError:
                return fonts

            fonts.append(ocp_font)

        return fonts


available_fonts = FontManager().available_fonts
