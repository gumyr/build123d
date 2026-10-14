"""
build123d font and text objects

name: text.py
by:   jwagenet
date: July 28th 2025

desc:
    This python module contains font and text objects.

"""

import glob
import logging
import os
import platform
import sys
from dataclasses import dataclass

from fontTools.ttLib import (  # type: ignore
    TTFont,
    TTLibError,
    TTLibFileIsCollectionError,
    ttCollection,
)
from OCP.Font import (
    Font_FA_Bold,
    Font_FA_BoldItalic,
    Font_FA_Italic,
    Font_FA_Regular,
    Font_FontMgr,
    Font_SystemFont,
)
from OCP.TCollection import TCollection_AsciiString
from OCP.collections import Sequence_TCollection_HAsciiString

from build123d.build_enums import FontStyle

logger = logging.getLogger("build123d")

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
    # Relief SingleLine, by the Relief SingleLine Project Authors (OFL 1.1),
    # rebuilt from its source without the conventions its TrueType export
    # needs: every stroke is one open or closed path of cubic curves with
    # true corners and exactly smooth joints, which the kernel offsets and
    # fuses cleanly. tools/clean_singleline_font.py makes it.
    bundled_fonts = [
        (
            "Relief SingleLine Clean",
            "reliefsinglelineclean/ReliefSingleLineClean-Regular.otf",
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
        aliases = Sequence_TCollection_HAsciiString()
        self.manager.GetAllAliases(aliases)
        aliases = [aliases.Value(i).ToCString() for i in range(1, aliases.Length() + 1)]

        if "singleline" not in aliases:
            if platform.system() == "Windows":  # pragma: no cover
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
                TCollection_AsciiString("Relief SingleLine Clean"),
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
        self, path: str, override: bool = False, single_stroke: bool = False
    ) -> list[str]:
        """Register all font faces in a font file and return font face names."""
        _, ext = os.path.splitext(path)
        try:
            if ext.strip(".").lower() == "ttc":  # pragma: no cover
                fonts = ttCollection.TTCollection(path)
            else:
                try:
                    fonts = [TTFont(path)]
                except TTLibFileIsCollectionError:
                    # Some files carry a .ttf extension but actually contain a
                    # TrueType Collection; fall back to loading them as one.
                    fonts = ttCollection.TTCollection(path)

            # FontTools may defer parsing tables until they are accessed, so
            # extract every face before registering any of them. A font's
            # position in its file is what selects it when the text is drawn.
            system_fonts = [
                face
                for face_index, font in enumerate(fonts)
                for face in self._get_font_faces(font, path, face_index)
            ]
        except TTLibError as err:
            logger.warning("Failed to load font file '%s': %s", path, err)
            return []

        font_faces = []
        for font in system_fonts:
            font_faces.append(font.FontName().ToCString())
            font.SetSingleStrokeFont(single_stroke)
            self.manager.RegisterFont(font, override)

        return font_faces

    def register_folder(
        self, path: str, override: bool = False, single_stroke: bool = False
    ) -> list[str]:
        """Register all fonts in a folder"""
        exts = ["ttf", "otf", "ttc"]
        font_faces: list[str] = []
        for ext in exts:
            search = os.path.join(os.path.normpath(path), "*" + ext)
            results = glob.glob(search)
            for result in results:
                if os.path.isfile(result):
                    font_faces += self.register_font(result, override, single_stroke)
        return list(set(font_faces))

    def register_system_fonts(self):
        """Runner to (re)inititalize the OCCT FontMgr font list since user folder is
        missing on Windows and some fonts may not be imported correctly."""

        if platform.system() == "Windows":  # pragma: no cover
            user = os.getlogin()
            paths = [
                "C:/Windows/Fonts",
                f"C:/Users/{user}/AppData/Local/Microsoft/Windows/Fonts",
            ]
        elif platform.system() == "Darwin":  # pragma: no cover
            # macOS
            paths = [
                "/System/Library/Fonts",
                "/System/Library/Fonts/Supplemental",
                "/Library/Fonts",
                "/Library/Fonts/Supplemental",
                os.path.expanduser("~/Library/Fonts"),
            ]
        else:  # Linux / Unix
            base_paths = [
                "/system/fonts",
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts"),
            ]
            paths = [
                root
                for path in base_paths
                if os.path.exists(path)
                for root, _, _ in os.walk(path)
            ]

        for path in paths:
            if os.path.exists(path):
                self.register_folder(path)

    def _get_font_faces(
        self, ft_font: TTFont, path: str, face_index: int = 0
    ) -> list[Font_SystemFont]:  # pragma: no cover
        """Extract font info from font files and return list of font object.

        Args:
            ft_font (TTFont): one font of the file
            path (str): the font file
            face_index (int, optional): position of the font within a font
                collection. Defaults to 0.
        """

        family, sub, preferred = "", "", ""
        for record in ft_font["name"].names:
            try:
                value = record.toUnicode()
            except UnicodeDecodeError:
                continue

            if record.nameID == 1 and family == "":
                family = value
            elif record.nameID == 2 and sub == "":
                sub = value
            elif record.nameID == 16 and preferred == "":
                preferred = value

        family = preferred if preferred != "" else family

        # The font as it stands, then each named instance of a variable font.
        # Instances are numbered from 1, in the order the font lists them; an
        # instance is named by the first readable record of its name, as the
        # family and subfamily are.
        styles = [(0, sub)]
        if "fvar" in ft_font:
            for instance, definition in enumerate(ft_font["fvar"].instances, start=1):
                for record in ft_font["name"].names:
                    if record.nameID != definition.subfamilyNameID:
                        continue
                    try:
                        styles.append((instance, record.toUnicode()))
                    except UnicodeDecodeError:
                        continue
                    break

        # Replicate OCCT font aspect substitution rules, but make them correct
        # - OCCT treats "Oblique" as "Italic", which seems fine
        # - OCCT treats "Book" as "Regular", which is wrong
        aspects = ["Regular", "Bold", "Italic", "Oblique"]
        fonts: list[Font_SystemFont] = []
        for instance, subfamily in styles:
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
            # FreeType takes the font in the low 16 bits and the instance above
            ocp_font.SetFontPath(
                aspect, TCollection_AsciiString(path), face_index | (instance << 16)
            )
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


def available_fonts() -> list[FontInfo]:
    """Get available fonts without initializing the font manager on import."""
    return FontManager().available_fonts()
