"""
build123d imports

name: test_clean_method.py
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
from unittest.mock import patch, MagicMock

from build123d.topology import Solid


class TestCleanMethod(unittest.TestCase):
    def setUp(self):
        # Create a mock object
        self.solid = Solid()
        self.solid.wrapped = MagicMock()  # Simulate a valid `wrapped` object

    @patch("build123d.topology.shape_core.ShapeUpgrade_UnifySameDomain")
    def test_clean_warning_on_exception(self, mock_shape_upgrade):
        # Mock the upgrader
        mock_upgrader = mock_shape_upgrade.return_value
        mock_upgrader.Build.side_effect = Exception("Mocked Build failure")

        # Capture warnings
        with self.assertWarns(Warning) as warn_context:
            self.solid.clean()

        # Assert the warning message
        self.assertIn("Unable to clean", str(warn_context.warning))

        # Verify the upgrader was constructed with the correct arguments
        mock_shape_upgrade.assert_called_once_with(self.solid.wrapped, True, True, True)

        # Verify the Build method was called
        mock_upgrader.Build.assert_called_once()

    def test_clean_with_none_wrapped(self):
        # Set `wrapped` to None to simulate the error condition
        self.solid.wrapped = None

        # Call clean and ensure it returns self
        result = self.solid.clean()
        self.assertIs(result, self.solid)


if __name__ == "__main__":
    unittest.main()
