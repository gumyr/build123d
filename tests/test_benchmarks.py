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
    with open(ttt_dir / name, "r", encoding="utf-8") as f:
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
