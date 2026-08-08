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
