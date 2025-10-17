import pytest
from build123d import *
import functools
import sys

def expected_to_fail(test_func):
    """
    A pytest decorator for tests that are expected to fail.

    - If the test fails as expected, it's marked as 'xfailed'.
    - If the test passes unexpectedly, it prints a GitHub Actions
      warning and is marked as 'skipped' to prevent it from being
      reported as a pass.
    """
    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        try:
            # Attempt to run the decorated test function
            test_func(*args, **kwargs)
        except Exception:
            # SUCCESS: The test raised an exception, as expected.
            # We use pytest.xfail to mark it as an "expected failure".
            pytest.xfail("This test failed as expected.")
        else:
            # FAILURE: The test completed without raising an exception.
            # This is the unexpected outcome.
            test_name = test_func.__name__
            filename = test_func.__code__.co_filename
            lineno = test_func.__code__.co_firstlineno

            # Print a warning in the specific format GitHub Actions recognizes.
            # ::warning file={name},line={line}::{message}
            warning_message = (
                f"::warning file={filename},line={lineno},title=Unexpected Pass::{test_name} passed but was expected to fail"
            )
            print(warning_message, file=sys.stdout)

            # Use pytest.skip to ensure the test is NOT reported as a "pass".
            pytest.skip("This test passed but was expected to fail.")

    return wrapper

@expected_to_fail
def test_known_occt_bug_sphere_boolean():
    """
    This test is expected to fail. If that changes then a github warning message will be generated.

    This test is for a known bug in OCCT < 7.9 that was supposedly fixed in later releases.
    """
    sphere = Solid.make_sphere(4).rotate(Axis.Z, 45)
    box = Solid.make_box(10, 10, 10).located(Location((0, 0, -5)))
    c = box.cut(sphere)
    assert c.is_valid is False


@expected_to_fail
def TMP_test_known_occt_bug_sphere_boolean():
    """
    This test is expected to fail. If that changes then a github warning message will be generated.

    This test is for a known bug in OCCT < 7.9 that was supposedly fixed in later releases.
    """
    sphere = Solid.make_sphere(4).rotate(Axis.Z, -45)
    box = Solid.make_box(10, 10, 10).located(Location((0, 0, -5)))
    c = box.cut(sphere)
    assert c.is_valid is False # should fail this assertion
