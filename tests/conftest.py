"""Shared pytest configuration for the build123d test suite."""

import pytest


@pytest.fixture(autouse=True)
def _tmp_path_on_test_instance(request, tmp_path):
    """Expose pytest's per-test ``tmp_path`` to unittest.TestCase methods.

    Tests that write files use ``self.tmp_path`` so that each test gets its own
    directory. Writing fixed file names into the working directory races when the
    suite runs in parallel (pytest-xdist) and litters the repository.
    """
    if request.instance is not None:
        request.instance.tmp_path = tmp_path
