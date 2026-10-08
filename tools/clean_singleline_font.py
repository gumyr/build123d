"""
Build the single-line font build123d bundles.

build123d ships "Relief SingleLine Clean", a rebuild of the open-source Relief
SingleLine font (https://github.com/isdat-type/Relief-SingleLine, SIL Open
Font License 1.1). The font's own TrueType export has to encode open strokes
in closed contours, and does so with conventions the kernel then has to undo:
a loop ends 2 units short of its start, a sharp corner is a 4-unit flat, a
stem end carries a 2-unit tick, and whole-number coordinates leave joints that
should be smooth kinked by a degree or two. Outlining such strokes piece by
piece is what made single-line text fragile.

This script reads the designers' source instead - the UFO, where every stroke
is already an open or closed path of cubic curves - undoes the conventions it
still carries, and writes a CFF-flavoured OpenType font:

    * ticks (contours of 6 units or less) are left out
    * a stroke that ends within 3 units of its own start is closed
    * a flat of 6 units or less between two lines becomes the corner itself
    * a joint the designers marked smooth, or that turns under 10 degrees,
      is made exactly smooth

The font is written on a grid 16 times finer than the source (16,000 units to
the em), because the kernel's font reader rounds coordinates to whole units,
and loops are written to end on a curve, because the reader drops a final
line that returns to the start. Four glyphs the UFO leaves empty are built as
mirror images of their siblings, as the UFO itself builds the down-left arrow.
Any character the CAD TTF maps and the UFO does not is taken from the TTF.

Usage, from the repository root with the upstream project unpacked somewhere:

    python tools/clean_singleline_font.py <Relief-SingleLine.ufo> \\
        src/build123d/data/fonts/reliefsinglelineclean/ReliefSingleLineClean-Regular.otf \\
        [<ReliefSingleLineCAD-Regular.ttf>]

Needs fontTools and numpy only.

license:

    Copyright 2025 Gumyr

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

from __future__ import annotations

import argparse
import collections
import math
from dataclasses import dataclass

import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import AbstractPointPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib import UFOReader

FAMILY = "Relief SingleLine Clean"
VERSION = "Version 1.000"
NODE_TOL = 3.0  # font units: ends this close to each other meet
STUB = 6.0  # a contour or line no longer than this is a convention, not a stroke
CORNER_DEG = 10.0  # a joint that turns more than this is a corner
GRID = 16  # the font is written this many times finer than the source

# Glyphs the UFO leaves empty, as a mirror image of one it has: (base glyph,
# component transform in UFO terms). The UFO itself defines the down-left
# arrow as the up-right one flipped both ways with these same offsets.
MIRRORED = {
    "guillemotright": ("guillemotleft", (-1, 0, 0, 1, 540, 0)),
    "uni2196": ("uni2197", (-1, 0, 0, 1, 746, 0)),  # up-left from up-right
    "uni2198": ("uni2197", (1, 0, 0, -1, 0, 630)),  # down-right from up-right
    "uni27F2": ("uni27F3", (-1, 0, 0, 1, 860, 0)),  # anticlockwise from clockwise
}


# --------------------------------------------------------------------------
# pieces: a stroke is a chain of these
# --------------------------------------------------------------------------


@dataclass
class Piece:
    """One segment of a stroke as Bezier poles, in the direction it is drawn;
    a line is the two-pole case"""

    poles: np.ndarray

    @property
    def is_line(self) -> bool:
        return len(self.poles) == 2

    @property
    def start(self) -> np.ndarray:
        return self.poles[0]

    @start.setter
    def start(self, value: np.ndarray) -> None:
        self.poles[0] = value

    @property
    def end(self) -> np.ndarray:
        return self.poles[-1]

    @end.setter
    def end(self, value: np.ndarray) -> None:
        self.poles[-1] = value

    @property
    def length(self) -> float:
        """Length, by chords for a curve; close enough to tell a stub from a stroke"""
        if self.is_line:
            return float(np.linalg.norm(self.end - self.start))
        points = [self.at(t) for t in np.linspace(0.0, 1.0, 17)]
        return float(sum(np.linalg.norm(b - a) for a, b in zip(points, points[1:])))

    def at(self, t: float) -> np.ndarray:
        """The point at parameter t, by de Casteljau"""
        points = [pole.astype(float) for pole in self.poles]
        while len(points) > 1:
            points = [(1 - t) * a + t * b for a, b in zip(points, points[1:])]
        return points[0]

    def direction(self, at_end: bool) -> np.ndarray:
        """Unit direction of travel at one end"""
        ordered = self.poles[::-1] if at_end else self.poles
        for other in ordered[1:]:
            along = other - ordered[0]
            if np.linalg.norm(along) > 1e-9:
                along = along / np.linalg.norm(along)
                return -along if at_end else along
        raise ValueError("piece has no length")


def turn_between(before: Piece, after: Piece) -> float:
    """The angle, in degrees, the stroke turns through where two pieces meet"""
    cosine = float(before.direction(True) @ after.direction(False))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def weld(before: Piece, after: Piece) -> float:
    """Make two curved pieces meet at one point with one tangent: their shared
    point moves onto the line between the poles either side of it. Returns
    how far it moved."""
    joint = (before.end + after.start) / 2
    a, b = before.poles[-2], after.poles[1]
    span = b - a
    t = float((joint - a) @ span / (span @ span))
    moved = a + min(0.95, max(0.05, t)) * span
    shift = max(np.linalg.norm(moved - before.end), np.linalg.norm(moved - after.start))
    before.end = moved
    after.start = moved
    return float(shift)


def line_meeting(first: Piece, second: Piece) -> np.ndarray | None:
    """Where the lines through two line pieces meet, or None if parallel"""
    d1, d2 = first.end - first.start, second.end - second.start
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < 1e-9:
        return None
    gap = second.start - first.start
    t = (gap[0] * d2[1] - gap[1] * d2[0]) / cross
    return first.start + t * d1


# --------------------------------------------------------------------------
# reading the source
# --------------------------------------------------------------------------


class Collector(AbstractPointPen):
    """Gathers a glyph's contours and components as the source has them"""

    def __init__(self) -> None:
        self.contours: list[list[tuple]] = []
        self.components: list[tuple[str, tuple]] = []

    def beginPath(self, identifier=None, **kwargs):
        self.contours.append([])

    def endPath(self):
        pass

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        self.contours[-1].append((pt, segmentType, smooth))

    def addComponent(self, baseGlyphName, transformation, identifier=None, **kwargs):
        self.components.append((baseGlyphName, transformation))


def source_contours(glyph_set, name: str, seen=()) -> list[list[tuple]]:
    """A UFO glyph's contours with its components resolved, each contour a
    list of (point, segment type or None for a control point, smooth)"""
    collector = Collector()
    glyph_set[name].drawPoints(collector)
    contours = list(collector.contours)
    if not contours and not collector.components and name in MIRRORED:
        collector.components.append(MIRRORED[name])
    for base, matrix in collector.components:
        if base in seen or base not in glyph_set:
            continue
        transform = Transform(*matrix)
        for contour in source_contours(glyph_set, base, seen + (name,)):
            contours.append(
                [
                    (transform.transformPoint(pt), kind, smooth)
                    for pt, kind, smooth in contour
                ]
            )
    return contours


def ttf_contours(font: TTFont, name: str) -> list[list[tuple]]:
    """A TTF glyph's contours in the same form, its quadratic pieces raised
    to cubics exactly. The implied closing line of each contour is left out,
    as the kernel leaves it out; a loop is recognised later from its ends."""
    pen = DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    contours: list[list[tuple]] = []
    current: list[tuple] = []
    for operator, args in pen.value:
        if operator == "moveTo":
            current = [(args[0], "move", False)]
        elif operator == "lineTo":
            current.append((args[0], "line", False))
        elif operator == "qCurveTo":
            start = current[-1][0]
            controls, on = list(args[:-1]), args[-1]
            for i, control in enumerate(controls):
                if i + 1 < len(controls):
                    following = controls[i + 1]
                    end = (
                        (control[0] + following[0]) / 2,
                        (control[1] + following[1]) / 2,
                    )
                else:
                    end = on
                c1 = (
                    start[0] + 2 / 3 * (control[0] - start[0]),
                    start[1] + 2 / 3 * (control[1] - start[1]),
                )
                c2 = (
                    end[0] + 2 / 3 * (control[0] - end[0]),
                    end[1] + 2 / 3 * (control[1] - end[1]),
                )
                current.append((c1, None, False))
                current.append((c2, None, False))
                # not marked smooth: a TTF carries no such flag, so a joint is
                # smooth only if it measures so
                current.append((end, "curve", False))
                start = end
        elif operator == "closePath":
            contours.append(current)
            current = []
    if current:
        contours.append(current)
    return contours


def to_pieces(contour: list[tuple]) -> tuple[list[Piece], list[bool], bool]:
    """Pieces of a contour, whether the joint after each is marked smooth, and
    whether the source has the contour closed"""
    is_open = contour[0][1] == "move"
    points = list(contour)
    if not is_open:
        first = next(i for i, p in enumerate(points) if p[1])
        points = points[first:] + points[: first + 1]
    pieces: list[Piece] = []
    smooth: list[bool] = []
    pending = [points[0][0]]
    for pt, kind, is_smooth in points[1:]:
        pending.append(pt)
        if kind is None:
            continue
        if kind not in ("line", "curve") or len(pending) not in (2, 4):
            raise ValueError(f"unexpected segment {kind} with {len(pending)} points")
        pieces.append(Piece(np.array(pending, dtype=float)))
        smooth.append(is_smooth)
        pending = [pt]
    return pieces, smooth, not is_open


# --------------------------------------------------------------------------
# cleaning
# --------------------------------------------------------------------------


def clean(
    contour: list[tuple], notes: collections.Counter
) -> tuple[list[Piece], bool] | None:
    """One cleaned stroke as its pieces and whether it is a closed loop, or
    None for a contour that is a convention rather than a stroke"""
    xs = [p[0][0] for p in contour]
    ys = [p[0][1] for p in contour]
    if max(max(xs) - min(xs), max(ys) - min(ys)) <= STUB:
        notes["ticks left out"] += 1
        return None
    pieces, smooth, closed = to_pieces(contour)
    length = sum(piece.length for piece in pieces)

    # a stroke that comes back to its own start is a loop
    gap = float(np.linalg.norm(pieces[-1].end - pieces[0].start))
    if not closed and gap <= NODE_TOL and length > 10 * NODE_TOL:
        last, first = pieces[-1], pieces[0]
        if (
            not last.is_line
            and not first.is_line
            and turn_between(last, first) <= CORNER_DEG
        ):
            weld(last, first)
            smooth[-1] = True
        else:
            last.end = first.start.copy()
            smooth[-1] = False
        closed = True
        notes["loops closed"] += 1

    # corner flats between two lines
    index = 0
    while index < len(pieces) and len(pieces) >= 3:
        flat = pieces[index]
        inside = closed or 0 < index < len(pieces) - 1
        before = pieces[index - 1]
        after = pieces[(index + 1) % len(pieces)]
        if (
            inside
            and flat.is_line
            and flat.length <= STUB
            and turn_between(before, flat) > CORNER_DEG
            and turn_between(flat, after) > CORNER_DEG
        ):
            corner = (
                line_meeting(before, after)
                if before.is_line and after.is_line
                else None
            )
            middle = (flat.start + flat.end) / 2
            if corner is not None and np.linalg.norm(corner - middle) <= 3 * STUB:
                before.end = corner
                after.start = corner.copy()
                del pieces[index]
                del smooth[index]
                smooth[index - 1] = False
                notes["corner flats removed"] += 1
                continue
            notes["corner flats kept"] += 1
        index += 1

    # joints that are meant to be smooth
    joints = list(range(len(pieces) - 1)) + ([len(pieces) - 1] if closed else [])
    for index in joints:
        before, after = pieces[index], pieces[(index + 1) % len(pieces)]
        turn = turn_between(before, after)
        if before.is_line and after.is_line:
            continue
        if not (smooth[index] or turn < CORNER_DEG) or turn < 1e-9:
            continue
        if not before.is_line and not after.is_line:
            weld(before, after)
        else:
            # swing the curve's pole next to the joint onto the line
            line, curve = (before, after) if before.is_line else (after, before)
            along = line.direction(True)
            joint = line.end if before.is_line else line.start
            handle = 1 if before.is_line else -2
            reach = np.linalg.norm(curve.poles[handle] - joint)
            curve.poles[handle] = joint + along * (reach if before.is_line else -reach)
        notes["joints made exactly smooth"] += 1
        notes["largest kink removed, hundredths of a degree"] = max(
            notes["largest kink removed, hundredths of a degree"], int(turn * 100)
        )
    return pieces, closed


# --------------------------------------------------------------------------
# writing the font
# --------------------------------------------------------------------------


def draw(strokes: list[tuple[list[Piece], bool]], pen) -> None:
    """Draw the strokes of a glyph on a segment pen, scaled to the fine grid"""
    for pieces, closed in strokes:
        if closed and pieces[-1].is_line:
            # The reader drops the last point of a contour when it repeats the
            # first, which turns a final line into the implied closing segment,
            # and the kernel discards that segment for a single-stroke font.
            # So a loop is written to end on a curve, or its last line as one.
            curved = [i for i, piece in enumerate(pieces) if not piece.is_line]
            if curved:
                pieces = pieces[curved[-1] + 1 :] + pieces[: curved[-1] + 1]
            else:
                last = pieces[-1]
                thirds = [
                    last.start + (last.end - last.start) * t
                    for t in (0, 1 / 3, 2 / 3, 1)
                ]
                pieces = pieces[:-1] + [Piece(np.array(thirds))]
        pen.moveTo(tuple(pieces[0].start * GRID))
        for piece in pieces:
            if piece.is_line:
                pen.lineTo(tuple(piece.end * GRID))
            else:
                pen.curveTo(*(tuple(p * GRID) for p in piece.poles[1:]))
        # every subpath of a CFF glyph is closed when it is read; a loop ends on
        # its own start, an open stroke gets the implied line back to it
        pen.closePath() if closed else pen.endPath()


def build(ufo: str, out: str, fallback: str | None = None) -> collections.Counter:
    """Build the font and return the counts of what was done"""
    reader = UFOReader(ufo)
    glyph_set = reader.getGlyphSet()
    info = type("Info", (), {})()
    reader.readInfo(info)
    notes: collections.Counter = collections.Counter()
    ttf = TTFont(fallback) if fallback else None

    names = set(glyph_set.keys())
    ufo_codes: set[int] = set()
    for name in names:
        glyph = glyph_set[name]
        glyph.drawPoints(Collector())  # reads the unicodes
        ufo_codes.update(getattr(glyph, "unicodes", None) or [])
    # characters the TTF maps that no UFO glyph does, whatever the glyph names
    ttf_only: dict[str, int] = {}
    if ttf is not None:
        for code, name in ttf.getBestCmap().items():
            if code not in ufo_codes and name not in names:
                ttf_only[name] = code
        names |= set(ttf_only)
    order = [".notdef"] + sorted(name for name in names if name != ".notdef")
    cmap: dict[int, str] = {}
    charstrings = {}
    metrics = {}
    for name in order:
        strokes = []
        width = 0
        contours: list[list[tuple]] = []
        if name in glyph_set:
            glyph = glyph_set[name]
            glyph.drawPoints(Collector())  # reads width and unicodes
            width = getattr(glyph, "width", 0) or 0
            for code in getattr(glyph, "unicodes", None) or []:
                cmap.setdefault(code, name)
            contours = source_contours(glyph_set, name)
            if not contours and ttf is not None and name in ttf.getGlyphSet():
                contours = ttf_contours(ttf, name)
                if contours:
                    notes["glyphs taken from the TTF"] += 1
                    if not width:
                        width = ttf["hmtx"][name][0]
        elif name in ttf_only and ttf is not None:
            contours = ttf_contours(ttf, name)
            width = ttf["hmtx"][name][0]
            cmap.setdefault(ttf_only[name], name)
            notes["glyphs taken from the TTF"] += 1
        for contour in contours:
            cleaned = clean(contour, notes)
            if cleaned:
                strokes.append(cleaned)
                notes["strokes"] += 1
                notes["closed strokes"] += int(cleaned[1])
                notes["pieces"] += len(cleaned[0])
        pen = T2CharStringPen(width * GRID, None)
        draw(strokes, pen)
        charstrings[name] = pen.getCharString()
        bounds = BoundsPen(None)
        recording = RecordingPen()
        draw(strokes, recording)
        recording.replay(bounds)
        metrics[name] = (
            int(width * GRID),
            int(round(bounds.bounds[0])) if bounds.bounds else 0,
        )
        notes["glyphs"] += 1
        notes["glyphs with strokes"] += int(bool(strokes))

    units = int(getattr(info, "unitsPerEm", 1000)) * GRID
    builder = FontBuilder(unitsPerEm=units, isTTF=False)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap(cmap)
    post_name = FAMILY.replace(" ", "") + "-Regular"
    builder.setupCFF(
        post_name,
        {"FullName": FAMILY, "FontMatrix": [1 / units, 0, 0, 1 / units, 0, 0]},
        charstrings,
        {},
    )
    builder.setupHorizontalMetrics(metrics)
    ascender = int(getattr(info, "ascender", 800) or 800) * GRID
    descender = int(getattr(info, "descender", -200) or -200) * GRID
    builder.setupHorizontalHeader(ascent=ascender, descent=descender)
    builder.setupNameTable(
        {
            "familyName": FAMILY,
            "styleName": "Regular",
            "fullName": FAMILY,
            "psName": post_name,
            "version": VERSION,
            "uniqueFontIdentifier": f"{post_name};build123d",
            "copyright": getattr(info, "copyright", "") or "",
            "licenseDescription": getattr(info, "openTypeNameLicense", "") or "",
            "licenseInfoURL": getattr(info, "openTypeNameLicenseURL", "") or "",
        }
    )
    builder.setupOS2(sTypoAscender=ascender, sTypoDescender=descender)
    builder.setupPost()
    builder.save(out)
    notes["characters mapped"] = len(cmap)
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ufo", help="upstream sources/Relief-SingleLine.ufo")
    parser.add_argument("out", help="the .otf to write")
    parser.add_argument(
        "ttf",
        nargs="?",
        help="upstream ReliefSingleLineCAD-Regular.ttf, for glyphs the UFO lacks",
    )
    arguments = parser.parse_args()
    notes = build(arguments.ufo, arguments.out, arguments.ttf)
    print(f"wrote {arguments.out}")
    for key, value in notes.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    main()
