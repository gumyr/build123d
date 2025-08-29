import pytest
import sys
from build123d import *
from pathlib import Path

from unittest.mock import Mock
mock_module = Mock()
mock_module.show = Mock()
mock_module.show_object = Mock()
mock_module.show_all = Mock()
sys.modules["ocp_vscode"] = mock_module

_ = pytest.importorskip("pytest_benchmark")


def _read_docs_ttt_code(name):
    checkout_dir = Path(__file__).parent.parent
    ttt_dir = checkout_dir / "docs/assets/ttt"
    name = "ttt-" + name + ".py"
    with open(ttt_dir / name, "r") as f:
        return f.read()


def test_ppp_0101(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0101"))
    benchmark(model)


def test_ppp_0102(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0102"))
    benchmark(model)


def test_ppp_0103(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0103"))
    benchmark(model)


def test_ppp_0104(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0104"))
    benchmark(model)


def test_ppp_0105(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0105"))
    benchmark(model)


def test_ppp_0106(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0106"))
    benchmark(model)


def test_ppp_0107(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0107"))
    benchmark(model)


def test_ppp_0108(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0108"))
    benchmark(model)


def test_ppp_0109(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0109"))
    benchmark(model)


def test_ppp_0110(benchmark):
    def model():
        exec(_read_docs_ttt_code("ppp0110"))
    benchmark(model)


def test_ttt_23_02_02(benchmark):
    def model():
        exec(_read_docs_ttt_code("23-02-02-sm_hanger"))
    benchmark(model)

def test_ttt_23_T_24(benchmark):
    def model():
        exec(_read_docs_ttt_code("23-t-24-curved_support"))
    benchmark(model)

def test_ttt_24_SPO_06(benchmark):
    def model():
        exec(_read_docs_ttt_code("24-SPO-06-Buffer_Stand"))
    benchmark(model)



@pytest.mark.parametrize("test_input", [100, 1000, 10000, 100000])
def test_mesher_benchmark(benchmark, test_input):
    # in the 100_000 case test should take on the order of 0.2 seconds
    # but usually less than 1 second
    def test_create_3mf_mesh(i):
        vertices = [(float(i), 0.0, 0.0) for i in range(i)]
        triangles = [[i, i + 1, i + 2] for i in range(0, i - 3, 3)]
        mesher = Mesher()._create_3mf_mesh(vertices, triangles)
        assert len(mesher[0]) == i
        assert len(mesher[1]) == int(i / 3)

    benchmark(test_create_3mf_mesh, test_input)



def test_ttt_23_02_02_SYNTHETIC(benchmark):
    def model():
        """
        Creation of a complex sheet metal part

        name: ttt_sm_hanger.py
        by:   Gumyr
        date: July 17, 2023

        desc:
            This example implements the sheet metal part described in Too Tall Toby's
            sm_hanger CAD challenge.

            Notably, a BuildLine/Curve object is filleted by providing all the vertices
            and allowing the fillet operation filter out the end vertices. The
            make_brake_formed operation is used both in Algebra and Builder mode to
            create a sheet metal part from just an outline and some dimensions.
            license:

            Copyright 2023 Gumyr

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
        densa = 7800 / 1e6  # carbon steel density g/mm^3
        sheet_thickness = 4 * MM

        # Create the main body from a side profile
        with BuildPart() as side:
            d = Vector(1, 0, 0).rotate(Axis.Y, 60)
            with BuildLine(Plane.XZ) as side_line:
                l1 = Line((0, 65), (170 / 2, 65))
                l2 = PolarLine(
                    l1 @ 1, length=65, direction=d, length_mode=LengthMode.VERTICAL
                )
                l3 = Line(l2 @ 1, (170 / 2, 0))
                fillet(side_line.vertices(), 7)
            make_brake_formed(
                thickness=sheet_thickness,
                station_widths=[40, 40, 40, 112.52 / 2, 112.52 / 2, 112.52 / 2],
                side=Side.RIGHT,
            )
            fe = side.edges().filter_by(Axis.Z).group_by(Axis.Z)[0].sort_by(Axis.Y)[-1]
            fillet(fe, radius=7)

        # Create the "wings" at the top
        with BuildPart() as wing:
            with BuildLine(Plane.YZ) as wing_line:
                l1 = Line((0, 65), (80 / 2 + 1.526 * sheet_thickness, 65))
                PolarLine(
                    l1 @ 1, 20.371288916, direction=Vector(0, 1, 0).rotate(Axis.X, -75)
                )
                fillet(wing_line.vertices(), 7)
            make_brake_formed(
                thickness=sheet_thickness,
                station_widths=110 / 2,
                side=Side.RIGHT,
            )
            bottom_edge = wing.edges().group_by(Axis.X)[-1].sort_by(Axis.Z)[0]
            fillet(bottom_edge, radius=7)

        # Create the tab at the top in Algebra mode
        tab_line = Plane.XZ * Polyline(
            (20, 65 - sheet_thickness), (56 / 2, 65 - sheet_thickness), (56 / 2, 88)
        )
        tab_line = fillet(tab_line.vertices(), 7)
        tab = make_brake_formed(sheet_thickness, 8, tab_line, Side.RIGHT)
        tab = fillet(
            tab.edges().filter_by(Axis.X).group_by(Axis.Z)[-1].sort_by(Axis.Y)[-1], 5
        )
        tab -= Pos((0, 0, 80)) * Rot(0, 90, 0) * Hole(5, 100)

        # Combine the parts together
        with BuildPart() as sm_hanger:
            add([side.part, wing.part])
            mirror(about=Plane.XZ)
            with BuildSketch(Plane.XY.offset(65)) as h1:
                with Locations((20, 0)):
                    Rectangle(30, 30, align=(Align.MIN, Align.CENTER))
                    fillet(h1.vertices().group_by(Axis.X)[-1], 7)
                SlotCenterPoint((154, 0), (154 / 2, 0), 20)
            extrude(amount=-40, mode=Mode.SUBTRACT)
            with BuildSketch() as h2:
                SlotCenterPoint((206, 0), (206 / 2, 0), 20)
            extrude(amount=40, mode=Mode.SUBTRACT)
            add(tab)
            mirror(about=Plane.YZ)
            mirror(about=Plane.XZ)
            faces()
            faces().edges()
            faces().edges().vertices()
            edges()
            vertices()
            faces().filter_by(GeomType.CYLINDER)
            faces().filter_by(GeomType.CYLINDER).edges()
            faces().filter_by(GeomType.CYLINDER).vertices()
            faces().filter_by(GeomType.CYLINDER).edges().vertices()
            

        # print(f"Mass: {sm_hanger.part.volume*7800*1e-6:0.1f} g")
        assert sm_hanger.part.volume * densa == pytest.approx(1028, 10)

    benchmark(model)