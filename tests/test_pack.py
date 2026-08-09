"""
build123d Pack tests

name: build_pack.py
by:   fischman
date: November 9th 2023

desc: Unit tests for the build123d pack module
"""

import random
import unittest

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
        # Not raising in this call shows successful non-overlap.
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
        widths = [random.randint(2, 20) for _ in range(50)]
        heights = [random.randint(1, width - 1) for width in widths]
        inputs = [SlotOverall(width, height) for width, height in zip(widths, heights)]
        # Not raising in this call shows successful non-overlap.
        packed = pack(inputs, 1)
        bb = (Sketch() + packed).bounding_box()
        self.assertEqual(bb.min, Vector(0, 0, 0))
        self.assertEqual(bb.max, Vector(70, 63, 0))


if __name__ == "__main__":
    unittest.main()
