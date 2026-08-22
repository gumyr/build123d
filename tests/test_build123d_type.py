from typing import get_type_hints

import pytest

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Compound,
    Curve,
    Edge,
    Face,
    Location,
    Part,
    Plane,
    Shape,
    ShapeList,
    Shell,
    Sketch,
    Solid,
    Vector,
    Vertex,
    Wire,
    full_round,
)


@pytest.mark.parametrize(
    "cls",
    [
        Shape,
        Vertex,
        Edge,
        Wire,
        Face,
        Shell,
        Solid,
        Compound,
        Curve,
        Sketch,
        Part,
        Axis,
        Plane,
        Location,
        Vector,
        ShapeList,
        BuildPart,
        BuildSketch,
        BuildLine,
    ],
)
def test_build123d_type(cls):
    assert cls.build123d_type == cls.__name__


def test_full_round_return_type():
    assert get_type_hints(full_round)["return"] is Sketch
