"""

name: packed_boxes.py
by:   fischman
date: November 9th 2023

desc: Demo packing a bunch of boxes in 2D.

"""
import functools
import operator
import random
import build123d as bd

random.seed(123456)
test_boxes = [bd.Box(random.randint(1, 20), random.randint(1, 20), random.randint(1, 5))
              for _ in range(50)]
packed = bd.pack(test_boxes, 3)
