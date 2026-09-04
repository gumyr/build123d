"""
Sheet Metal Utilities

name: sheet_utils.py
by:   Gumyr
date: September 3rd 2026

desc:
    This module defines shared sheet-metal parameters and calculations.

license:

    Copyright 2026 Gumyr

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

from dataclasses import dataclass

from build123d.build_enums import SheetSurface

__all__ = ["SheetMetalParameters"]

MIN_BEND_RADIUS = 1e-3


@dataclass(frozen=True)
class SheetMetalParameters:
    """Parameters relating a reference shell to its physical material.

    Args:
        thickness: Sheet material thickness.
        bend_radius: Default physical inside bend radius. When omitted, the
            sheet thickness is used.
        k_factor: Neutral-axis position from the locally concave material
            surface, from 0 to 1. Defaults to 0.5.
        sheet_surface: Reference surface represented by the shell. Defaults to
            ``SheetSurface.INSIDE``.
    """

    thickness: float
    bend_radius: float | None = None
    k_factor: float = 0.5
    sheet_surface: SheetSurface = SheetSurface.INSIDE

    def __post_init__(self):
        """Validate sheet-metal parameters."""
        if self.thickness <= 0:
            raise ValueError("thickness must be positive")
        if self.bend_radius is not None and self.bend_radius < 0:
            raise ValueError("bend_radius can't be negative")
        if not 0.0 <= self.k_factor <= 1.0:
            raise ValueError("k_factor must be between 0 and 1")
        if not isinstance(self.sheet_surface, SheetSurface):
            raise TypeError("sheet_surface must be a SheetSurface")

    @property
    def resolved_bend_radius(self) -> float:
        """Default inside bend radius, using thickness when unspecified."""
        return self.thickness if self.bend_radius is None else self.bend_radius


def material_offsets(parameters: SheetMetalParameters) -> tuple[float, float]:
    """Return signed inside and outside offsets from a reference shell."""
    thickness = parameters.thickness
    if parameters.sheet_surface == SheetSurface.INSIDE:
        return 0.0, -thickness
    if parameters.sheet_surface == SheetSurface.OUTSIDE:
        return thickness, 0.0
    if parameters.sheet_surface == SheetSurface.MID:
        return thickness / 2, -thickness / 2
    return (
        parameters.k_factor * thickness,
        -(1 - parameters.k_factor) * thickness,
    )


def reference_radius(
    inside_radius: float,
    parameters: SheetMetalParameters,
    bend_angle: float,
) -> float:
    """Convert a physical inside radius to a reference-surface radius."""
    thickness = parameters.thickness
    if parameters.sheet_surface == SheetSurface.MID:
        offset = thickness / 2
    elif parameters.sheet_surface == SheetSurface.NEUTRAL:
        offset = (
            parameters.k_factor if bend_angle > 0 else 1 - parameters.k_factor
        ) * thickness
    elif parameters.sheet_surface == SheetSurface.INSIDE:
        offset = 0 if bend_angle > 0 else thickness
    else:
        offset = thickness if bend_angle > 0 else 0
    return max(inside_radius + offset, MIN_BEND_RADIUS)


def neutral_radius(
    source_radius: float,
    parameters: SheetMetalParameters,
    positive_bend: bool,
) -> float:
    """Return the neutral radius corresponding to a cylindrical reference face."""
    thickness = parameters.thickness
    k_factor = parameters.k_factor
    if parameters.sheet_surface == SheetSurface.NEUTRAL:
        normal_offset = 0.0
    elif parameters.sheet_surface == SheetSurface.MID:
        normal_offset = (0.5 - k_factor) * thickness
    elif parameters.sheet_surface == SheetSurface.INSIDE:
        normal_offset = -k_factor * thickness
    else:
        normal_offset = (1 - k_factor) * thickness

    # A positive bend's oriented normal points toward the cylinder axis, so a
    # signed normal offset changes its radius in the opposite direction.
    radial_offset = (-1 if positive_bend else 1) * normal_offset
    radius = source_radius + radial_offset
    if radius <= 0:
        raise ValueError("Sheet parameters produce a non-positive neutral radius")
    return radius
