"""
build123d imports

name: test_color.py
by:   Gumyr
date: January 22, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import colorsys
import copy
import math

import numpy as np
import pytest
from OCP.Quantity import Quantity_ColorRGBA

from build123d.geometry import Color


# Overloads
@pytest.mark.parametrize(
    "color, expected",
    [
        pytest.param(Color("blue"), (0, 0, 1, 1), id="name"),
        pytest.param(Color("blue", alpha=0.5), (0, 0, 1, 0.5), id="name + kw alpha"),
        pytest.param(Color("blue", 0.5), (0, 0, 1, 0.5), id="name + alpha"),
    ],
)
def test_overload_name(color, expected):
    np.testing.assert_allclose(tuple(color), expected, 1e-5)


@pytest.mark.parametrize(
    "color, expected",
    [
        pytest.param(Color(0.0, 1.0, 0.0), (0, 1, 0, 1), id="rgb"),
        pytest.param(Color(1.0, 1.0, 0.0, 0.5), (1, 1, 0, 0.5), id="rgba"),
        pytest.param(
            Color(1.0, 1.0, 0.0, alpha=0.5), (1, 1, 0, 0.5), id="rgb + kw alpha"
        ),
        pytest.param(
            Color(red=0.1, green=0.2, blue=0.3, alpha=0.5),
            (0.1, 0.2, 0.3, 0.5),
            id="kw rgba",
        ),
    ],
)
def test_overload_rgba(color, expected):
    np.testing.assert_allclose(tuple(color), expected, 1e-5)


@pytest.mark.parametrize(
    "color, expected",
    [
        pytest.param(
            Color(0x996692), (0x99 / 0xFF, 0x66 / 0xFF, 0x92 / 0xFF, 1), id="color_code"
        ),
        pytest.param(
            Color(0x006692, 0x80),
            (0, 0x66 / 0xFF, 0x92 / 0xFF, 0x80 / 0xFF),
            id="color_code + alpha",
        ),
        pytest.param(
            Color(0x006692, alpha=0x80),
            (0, 102 / 255, 146 / 255, 128 / 255),
            id="color_code + kw alpha",
        ),
        pytest.param(
            Color(color_code=0x996692, alpha=0xCC),
            (153 / 255, 102 / 255, 146 / 255, 204 / 255),
            id="kw color_code + alpha",
        ),
    ],
)
def test_overload_hex(color, expected):
    np.testing.assert_allclose(tuple(color), expected, 1e-5)


@pytest.mark.parametrize(
    "color, expected",
    [
        pytest.param(Color((0.1,)), (0.1, 1.0, 1.0, 1.0), id="tuple r"),
        pytest.param(Color((0.1, 0.2)), (0.1, 0.2, 1.0, 1.0), id="tuple rg"),
        pytest.param(Color((0.1, 0.2, 0.3)), (0.1, 0.2, 0.3, 1.0), id="tuple rgb"),
        pytest.param(
            Color((0.1, 0.2, 0.3, 0.4)), (0.1, 0.2, 0.3, 0.4), id="tuple rbga"
        ),
        pytest.param(Color((0.1, 0.2, 0.3, 0.4)), (0.1, 0.2, 0.3, 0.4), id="kw tuple"),
    ],
)
def test_overload_tuple(color, expected):
    np.testing.assert_allclose(tuple(color), expected, 1e-5)


# ColorLikes
@pytest.mark.parametrize(
    "color_like",
    [
        pytest.param(Quantity_ColorRGBA(1, 0, 0, 1), id="Quantity_ColorRGBA"),
        pytest.param("red", id="name str"),
        pytest.param("red ", id="name str whitespace"),
        pytest.param(("red",), id="tuple name str"),
        pytest.param(("red", 1), id="tuple name str + alpha"),
        pytest.param("#ff0000", id="hex str rgb 24bit"),
        pytest.param(" #ff0000 ", id="hex str rgb 24bit whitespace"),
        pytest.param(("#ff0000",), id="tuple hex str rgb 24bit"),
        pytest.param(("#ff0000", 1), id="tuple hex str rgb 24bit + alpha"),
        pytest.param("#ff0000ff", id="hex str rgba 24bit"),
        pytest.param(" #ff0000ff ", id="hex str rgba 24bit whitespace"),
        pytest.param(("#ff0000ff",), id="tuple hex str rgba 24bit"),
        pytest.param(
            ("#ff0000ff", 0.6), id="tuple hex str rgba 24bit + alpha (not used)"
        ),
        pytest.param("#f00", id="hex str rgb 12bit"),
        pytest.param(" #f00 ", id="hex str rgb 12bit whitespace"),
        pytest.param(("#f00",), id="tuple hex str rgb 12bit"),
        pytest.param(("#f00", 1), id="tuple hex str rgb 12bit + alpha"),
        pytest.param("#f00f", id="hex str rgba 12bit"),
        pytest.param(" #f00f ", id="hex str rgba 12bit whitespace"),
        pytest.param(("#f00f",), id="tuple hex str rgba 12bit"),
        pytest.param(("#f00f", 0.6), id="tuple hex str rgba 12bit + alpha (not used)"),
        pytest.param(0xFF0000, id="hex int"),
        pytest.param((0xFF0000), id="tuple hex int"),
        pytest.param((0xFF0000, 0xFF), id="tuple hex int + alpha"),
        pytest.param((1, 0, 0), id="tuple rgb int"),
        pytest.param((1, 0, 0, 1), id="tuple rgba int"),
        pytest.param((1.0, 0.0, 0.0), id="tuple rgb float"),
        pytest.param((1.0, 0.0, 0.0, 1.0), id="tuple rgba float"),
    ],
)
def test_color_likes(color_like):
    expected = (1, 0, 0, 1)
    np.testing.assert_allclose(tuple(Color(color_like)), expected, 1e-5)
    np.testing.assert_allclose(tuple(Color(color_like=color_like)), expected, 1e-5)


@pytest.mark.parametrize(
    "color_like, expected",
    [
        pytest.param(Color(), (1, 1, 1, 1), id="empty Color()"),
        pytest.param(1.0, (1, 1, 1, 1), id="r float"),
        pytest.param((1.0,), (1, 1, 1, 1), id="tuple r float"),
        pytest.param((1.0, 0.0), (1, 0, 1, 1), id="tuple rg float"),
    ],
)
def test_color_likes_incomplete(color_like, expected):
    np.testing.assert_allclose(tuple(Color(color_like)), expected, 1e-5)
    np.testing.assert_allclose(tuple(Color(color_like=color_like)), expected, 1e-5)


@pytest.mark.parametrize(
    "color_like",
    [
        pytest.param(Quantity_ColorRGBA(1, 0, 0, 0.6), id="Quantity_ColorRGBA"),
        pytest.param(("red", 0.6), id="tuple name str + alpha"),
        pytest.param(("#ff0000", 0.6), id="tuple hex str rgb 24bit + alpha"),
        pytest.param(("#ff000099"), id="tuple hex str rgba 24bit"),
        pytest.param(("#f00", 0.6), id="tuple hex str rgb 12bit + alpha"),
        pytest.param(("#f009"), id="tuple hex str rgba 12bit"),
        pytest.param((0xFF0000, 153), id="tuple hex int + alpha int"),
        pytest.param((1.0, 0.0, 0.0, 0.6), id="tuple rbga float"),
    ],
)
def test_color_likes_alpha(color_like):
    expected = (1, 0, 0, 0.6)
    np.testing.assert_allclose(tuple(Color(color_like)), expected, 1e-5)
    np.testing.assert_allclose(tuple(Color(color_like=color_like)), expected, 1e-5)


# Exceptions
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("build123d", id="invalid color name"),
        pytest.param("#ffg", id="invalid rgb 12bit"),
        pytest.param("#fffg", id="invalid rgba 12bit"),
        pytest.param("#fffgg", id="invalid rgb 24bit"),
        pytest.param("#fff00gg", id="invalid rgba 24bit"),
        pytest.param("#ff", id="short rgb 12bit"),
        pytest.param("#fffff", id="short rgb 24bit"),
        pytest.param("#fffffff", id="short rgba 24bit"),
        pytest.param("#fffffffff", id="long rgba 24bit"),
    ],
)
def test_exceptions_color_name(name):
    with pytest.raises(Exception):
        Color(name)


@pytest.mark.parametrize(
    "color_type",
    [
        pytest.param(
            (
                dict(
                    {"name": "red", "alpha": 1},
                )
            ),
            id="dict arg",
        ),
        pytest.param(("red", "blue"), id="str + str"),
        pytest.param((1.0, "blue"), id="float + str order"),
        pytest.param((1, "blue"), id="int + str order"),
    ],
)
def test_exceptions_color_type(color_type):
    with pytest.raises(Exception):
        Color(*color_type)


# Methods
def test_rgba_wrapped():
    c = Color(1.0, 1.0, 0.0, 0.5)
    assert c.wrapped.GetRGB().Red() == 1.0
    assert c.wrapped.GetRGB().Green() == 1.0
    assert c.wrapped.GetRGB().Blue() == 0.0
    assert c.wrapped.Alpha() == 0.5


def test_copy():
    c = Color(0.1, 0.2, 0.3, alpha=0.4)
    c_copy = copy.copy(c)
    np.testing.assert_allclose(tuple(c_copy), (0.1, 0.2, 0.3, 0.4), rtol=1e-5)


def test_str_repr_is():
    c = Color(1, 0, 0)
    assert str(c) == "Color: (1.0, 0.0, 0.0, 1.0) is 'RED'"
    assert repr(c) == "Color(1.0, 0.0, 0.0, 1.0)"


def test_str_repr_near():
    c = Color(1, 0.5, 0)
    assert str(c) == "Color: (1.0, 0.5, 0.0, 1.0) near 'DARKORANGE1'"
    assert repr(c) == "Color(1.0, 0.5, 0.0, 1.0)"


class TestColorCategoricalSet:
    def test_returns_expected_number_of_colors(self):
        colors = Color.categorical_set(5)
        assert len(colors) == 5
        assert all(isinstance(c, Color) for c in colors)

    def test_colors_are_evenly_spaced_in_hue(self):
        count = 8
        colors = Color.categorical_set(count)
        hues = [colorsys.rgb_to_hls(*tuple(c)[:3])[0] for c in colors]
        diffs = [(hues[(i + 1) % count] - hues[i]) % 1.0 for i in range(count)]
        avg_diff = sum(diffs) / len(diffs)
        assert all(math.isclose(d, avg_diff, rel_tol=1e-2) for d in diffs)

    def test_starting_hue_as_float(self):
        (r, g, b, _) = tuple(Color.categorical_set(1, starting_hue=0.25)[0])
        h = colorsys.rgb_to_hls(r, g, b)[0]
        assert math.isclose(h, 0.25, rel_tol=0.05)

    def test_starting_hue_as_int_hex(self):
        # Blue (0x0000FF) should be valid and return a Color
        c = Color.categorical_set(1, starting_hue=0x0000FF)[0]
        assert isinstance(c, Color)

    def test_starting_hue_invalid_type(self):
        with pytest.raises(TypeError):
            Color.categorical_set(3, starting_hue="invalid")

    def test_starting_hue_out_of_range(self):
        with pytest.raises(ValueError):
            Color.categorical_set(3, starting_hue=1.5)
        with pytest.raises(ValueError):
            Color.categorical_set(3, starting_hue=-0.1)

    def test_starting_hue_negative_int(self):
        with pytest.raises(ValueError):
            Color.categorical_set(3, starting_hue=-1)

    def test_constant_alpha_applied(self):
        colors = Color.categorical_set(3, alpha=0.7)
        for c in colors:
            (_, _, _, a) = tuple(c)
            assert math.isclose(a, 0.7, rel_tol=1e-6)

    def test_iterable_alpha_applied(self):
        alphas = (0.1, 0.5, 0.9)
        colors = Color.categorical_set(3, alpha=alphas)
        for a, c in zip(alphas, colors):
            (_, _, _, returned_alpha) = tuple(c)
            assert math.isclose(a, returned_alpha, rel_tol=1e-6)

    def test_iterable_alpha_length_mismatch(self):
        with pytest.raises(ValueError):
            Color.categorical_set(4, alpha=[0.5, 0.7])

    def test_hues_wrap_around(self):
        colors = Color.categorical_set(10, starting_hue=0.95)
        hues = [colorsys.rgb_to_hls(*tuple(c)[:3])[0] for c in colors]
        assert all(0.0 <= h <= 1.0 for h in hues)

    def test_alpha_defaults_to_one(self):
        colors = Color.categorical_set(4)
        for c in colors:
            (_, _, _, a) = tuple(c)
            assert math.isclose(a, 1.0, rel_tol=1e-6)
