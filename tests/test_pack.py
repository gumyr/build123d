"""
build123d Pack tests

name: build_pack.py
by:   fischman
date: November 9th 2023

desc: Unit tests for the build123d pack module
"""

import operator
import random
import unittest
from functools import reduce

from build123d import *


class TestPack(unittest.TestCase):
    """Tests for the pack helper."""

    def test_simple(self):
        """Test pack with hand-picked data against expected output."""
        packed = pack([Box(10, 2, 1), Box(1, 5, 1), Box(1, 5, 1)], padding=1)
        self.assertEqual(
            # Nothing magically interesting here, and other packings
            # would also be fine, but this shows that padding is
            # working, as is the preference towards square(ish)
            # output.
            "[bbox: 0.0 <= x <= 10.0, 0.0 <= y <= 2.0, -0.5 <= z <= 0.5,"
            " bbox: 0.0 <= x <= 1.0, 3.0 <= y <= 8.0, -0.5 <= z <= 0.5,"
            " bbox: 2.0 <= x <= 3.0, 3.0 <= y <= 8.0, -0.5 <= z <= 0.5]",
            str([p.bounding_box() for p in packed]),
        )

    def test_random_boxes(self):
        """Test pack with larger (and randomized) inputs."""
        random.seed(123456)
        # 50 is an arbitrary number that is large enough to exercise
        # different aspects of the packer while still completing quickly.
        test_boxes = [
            Box(random.randint(1, 20), random.randint(1, 20), 1) for _ in range(50)
        ]
        # Not raising in this call shows successfull non-overlap.
        packed = pack(test_boxes, 1)
        self.assertEqual(
            "bbox: 0.0 <= x <= 94.0, 0.0 <= y <= 86.0, -0.5 <= z <= 0.5",
            str((Part() + packed).bounding_box()),
        )

    def test_random_slots(self):
        """Test pack for 2D objects."""
        random.seed(123456)
        # 50 is an arbitrary number that is large enough to exercise
        # different aspects of the packer while still completing quickly.
        inputs = [
            SlotOverall(random.randint(1, 20), random.randint(1, 20)) for _ in range(50)
        ]
        # Not raising in this call shows successfull non-overlap.
        packed = pack(inputs, 1)
        self.assertEqual(
            "bbox: 0.0 <= x <= 124.0, 0.0 <= y <= 105.0, 0.0 <= z <= 0.0",
            str((Sketch() + packed).bounding_box()),
        )


if __name__ == "__main__":
    unittest.main()
