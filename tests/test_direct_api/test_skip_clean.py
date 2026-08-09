"""
build123d imports

name: test_skip_clean.py
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

import unittest

from build123d.topology import SkipClean


class TestSkipClean(unittest.TestCase):
    def setUp(self):
        # Ensure the class variable is in its default state before each test
        SkipClean.clean = True

    def test_context_manager_sets_clean_false(self):
        # Verify `clean` is initially True
        self.assertTrue(SkipClean.clean)

        # Use the context manager
        with SkipClean():
            # Within the context, `clean` should be False
            self.assertFalse(SkipClean.clean)

        # After exiting the context, `clean` should revert to True
        self.assertTrue(SkipClean.clean)

    def test_exception_handling_does_not_affect_clean(self):
        # Verify `clean` is initially True
        self.assertTrue(SkipClean.clean)

        # Use the context manager and raise an exception
        try:
            with SkipClean():
                self.assertFalse(SkipClean.clean)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Ensure `clean` is restored to True after an exception
        self.assertTrue(SkipClean.clean)


if __name__ == "__main__":
    unittest.main()
