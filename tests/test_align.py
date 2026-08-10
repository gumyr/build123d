import pytest

from build123d.build_enums import Align
from build123d.geometry import Vector, to_align_offset


@pytest.mark.parametrize(
    "x_align,x_expect",
    [
        (Align.MAX, -0.5),
        (Align.CENTER, 0.25),
        (Align.MIN, 1),
        (Align.NONE, 0),
    ],
)
@pytest.mark.parametrize(
    "y_align,y_expect",
    [
        (Align.MAX, -1),
        (Align.CENTER, 0.25),
        (Align.MIN, 1.5),
        (Align.NONE, 0),
    ],
)
@pytest.mark.parametrize(
    "z_align,z_expect",
    [
        (Align.MAX, -1),
        (Align.CENTER, -0.75),
        (Align.MIN, -0.5),
        (Align.NONE, 0),
    ],
)
def test_align(
    x_align,
    x_expect,
    y_align,
    y_expect,
    z_align,
    z_expect,
):
    offset = to_align_offset(
        min_point=(-1, -1.5, 0.5),
        max_point=(0.5, 1.0, 1.0),
        align=(x_align, y_align, z_align),
    )
    assert offset.X == x_expect
    assert offset.Y == y_expect
    assert offset.Z == z_expect


@pytest.mark.parametrize("alignment", Align)
def test_align_single(alignment):
    min_point = (-1, -1.5, 0.5)
    max_point = (0.5, 1, 1)
    expected = to_align_offset(
        min_point=min_point,
        max_point=max_point,
        align=(alignment, alignment, alignment),
    )
    offset = to_align_offset(
        min_point=min_point,
        max_point=max_point,
        align=alignment,
    )
    assert expected == offset


def test_align_center():
    min_point = (-1, -1.5, 0.5)
    max_point = (0.5, 1, 1)
    center = (4, 2, 6)
    offset = to_align_offset(
        min_point=min_point,
        max_point=max_point,
        center=center,
        align=Align.CENTER,
    )
    assert offset == -Vector(center)
