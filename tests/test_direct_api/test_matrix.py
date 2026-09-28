"""
build123d imports

name: test_matrix.py
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

import copy
import math
import unittest

from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_TrsfForm
from build123d.geometry import Axis, Matrix, Vector


class TestMatrix(unittest.TestCase):
    def test_matrix_creation_and_access(self):
        def matrix_vals(m):
            return [[m[r, c] for c in range(4)] for r in range(4)]

        # default constructor creates a 4x4 identity matrix
        m = Matrix()
        identity = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        self.assertEqual(identity, matrix_vals(m))

        vals4x4 = [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 2.0],
            [0.0, 0.0, 1.0, 3.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        vals4x4_tuple = tuple(tuple(r) for r in vals4x4)

        # test constructor with 16-value input
        m = Matrix(vals4x4)
        self.assertEqual(vals4x4, matrix_vals(m))
        m = Matrix(vals4x4_tuple)
        self.assertEqual(vals4x4, matrix_vals(m))

        # test constructor with 12-value input (the last 4 are an implied
        # [0,0,0,1])
        m = Matrix(vals4x4[:3])
        self.assertEqual(vals4x4, matrix_vals(m))
        m = Matrix(vals4x4_tuple[:3])
        self.assertEqual(vals4x4, matrix_vals(m))

        # Test 16-value input with invalid values for the last 4
        invalid = [
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 2.0],
            [0.0, 0.0, 1.0, 3.0],
            [1.0, 2.0, 3.0, 4.0],
        ]
        with self.assertRaises(ValueError):
            Matrix(invalid)
        # Test input with invalid type
        with self.assertRaises(TypeError):
            Matrix("invalid")
        # Test input with invalid size / nested types
        with self.assertRaises(TypeError):
            Matrix([[1, 2, 3, 4], [1, 2, 3], [1, 2, 3, 4]])
        with self.assertRaises(TypeError):
            Matrix([1, 2, 3])

        # Invalid sub-type
        with self.assertRaises(TypeError):
            Matrix([[1, 2, 3, 4], "abc", [1, 2, 3, 4]])

        # test out-of-bounds access
        m = Matrix()
        with self.assertRaises(IndexError):
            m[0, 4]
        with self.assertRaises(IndexError):
            m[4, 0]
        with self.assertRaises(IndexError):
            m["ab"]

        # test __repr__ methods
        m = Matrix(vals4x4)
        mRepr = "Matrix([[1.0, 0.0, 0.0, 1.0],\n        [0.0, 1.0, 0.0, 2.0],\n        [0.0, 0.0, 1.0, 3.0],\n        [0.0, 0.0, 0.0, 1.0]])"
        self.assertEqual(repr(m), mRepr)
        self.assertEqual(str(eval(repr(m))), mRepr)

    def test_matrix_functionality(self):
        # Test rotate methods
        def matrix_almost_equal(m, target_matrix):
            for r, row in enumerate(target_matrix):
                for c, target_value in enumerate(row):
                    self.assertAlmostEqual(m[r, c], target_value)

        root_3_over_2 = math.sqrt(3) / 2
        m_rotate_x_30 = [
            [1, 0, 0, 0],
            [0, root_3_over_2, -1 / 2, 0],
            [0, 1 / 2, root_3_over_2, 0],
            [0, 0, 0, 1],
        ]
        mx = Matrix()
        mx.rotate(Axis.X, 30)
        matrix_almost_equal(mx, m_rotate_x_30)

        m_rotate_y_30 = [
            [root_3_over_2, 0, 1 / 2, 0],
            [0, 1, 0, 0],
            [-1 / 2, 0, root_3_over_2, 0],
            [0, 0, 0, 1],
        ]
        my = Matrix()
        my.rotate(Axis.Y, 30)
        matrix_almost_equal(my, m_rotate_y_30)

        m_rotate_z_30 = [
            [root_3_over_2, -1 / 2, 0, 0],
            [1 / 2, root_3_over_2, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        mz = Matrix()
        mz.rotate(Axis.Z, 30)
        matrix_almost_equal(mz, m_rotate_z_30)

        # Test matrix multiply vector
        v = Vector(1, 0, 0)
        self.assertAlmostEqual(mz.multiply(v), (root_3_over_2, 1 / 2, 0), 7)

        # The same rotation written as a list must multiply a vector too
        mz_list = Matrix(m_rotate_z_30)
        self.assertAlmostEqual(mz_list.multiply(v), (root_3_over_2, 1 / 2, 0), 7)

        # A list-built matrix rotated afterwards keeps working
        m_list_identity = Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
        m_list_identity.rotate(Axis.Z, 30)
        self.assertAlmostEqual(
            m_list_identity.multiply(v), (root_3_over_2, 1 / 2, 0), 7
        )

        # Test matrix multiply matrix
        m_rotate_xy_30 = [
            [root_3_over_2, 0, 1 / 2, 0],
            [1 / 4, root_3_over_2, -root_3_over_2 / 2, 0],
            [-root_3_over_2 / 2, 1 / 2, 3 / 4, 0],
            [0, 0, 0, 1],
        ]
        mxy = mx.multiply(my)
        matrix_almost_equal(mxy, m_rotate_xy_30)

        # Test matrix inverse
        vals4x4 = [[1, 2, 3, 4], [5, 1, 6, 7], [8, 9, 1, 10], [0, 0, 0, 1]]
        vals4x4_invert = [
            [-53 / 144, 25 / 144, 1 / 16, -53 / 144],
            [43 / 144, -23 / 144, 1 / 16, -101 / 144],
            [37 / 144, 7 / 144, -1 / 16, -107 / 144],
            [0, 0, 0, 1],
        ]
        m = Matrix(vals4x4).inverse()
        matrix_almost_equal(m, vals4x4_invert)

        # Test matrix created from transfer function
        rot_x = gp_Trsf()
        θ = math.pi
        rot_x.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), θ)
        m = Matrix(rot_x)
        rot_x_matrix = [
            [1, 0, 0, 0],
            [0, math.cos(θ), -math.sin(θ), 0],
            [0, math.sin(θ), math.cos(θ), 0],
            [0, 0, 0, 1],
        ]
        matrix_almost_equal(m, rot_x_matrix)

        # Test copy
        m2 = copy.copy(m)
        matrix_almost_equal(m2, rot_x_matrix)
        m3 = copy.deepcopy(m)
        matrix_almost_equal(m3, rot_x_matrix)


class TestMatrixValidation(unittest.TestCase):
    """Rejection paths of the Matrix constructor"""

    def test_unexpected_positional_type(self):
        with self.assertRaisesRegex(TypeError, "unexpected type"):
            Matrix(42)

    def test_unexpected_keyword(self):
        with self.assertRaisesRegex(ValueError, "Unexpected argument"):
            Matrix(nonsense=1)

    def test_elements_must_be_numbers(self):
        rows = [[1, 0, 0, 0], [0, 1, 0, "x"], [0, 0, 1, 0]]
        with self.assertRaisesRegex(TypeError, "Only float or int"):
            Matrix(rows)

    def test_list_translation_multiplies_vector(self):
        translation = Matrix(
            [
                [1, 0, 0, 1],
                [0, 1, 0, 2],
                [0, 0, 1, 3],
                [0, 0, 0, 1],
            ]
        )
        self.assertNotEqual(translation.wrapped.Form(), gp_TrsfForm.gp_Other)
        self.assertAlmostEqual(
            translation.multiply(Vector(10, 20, 30)), (11, 22, 33), 7
        )
        self.assertEqual(translation[0, 0], 1.0)
        self.assertEqual(translation[1, 3], 2.0)

    def test_list_similarity_is_recognised(self):
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
        rotation_scale_mirror = Matrix(
            [
                [-2 * c, 2 * s, 0, 5],
                [2 * s, 2 * c, 0, 0],
                [0, 0, 2, 0],
            ]
        )
        self.assertNotEqual(rotation_scale_mirror.wrapped.Form(), gp_TrsfForm.gp_Other)
        self.assertAlmostEqual(
            rotation_scale_mirror.multiply(Vector(1, 0, 0)), (5 - 2 * c, 2 * s, 0), 7
        )
        # a similarity converts to a gp_Trsf, so it can place a shape
        rotation_scale_mirror.wrapped.Trsf()

    def test_svd_of_rotation_scale_and_mirror(self):
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))

        def reconstruct(matrix):
            left, scales, right = matrix.svd()
            diagonal = Matrix(
                [[scales.X, 0, 0, 0], [0, scales.Y, 0, 0], [0, 0, scales.Z, 0]]
            )
            product = left.multiply(diagonal).multiply(right)
            for r in range(3):
                for col in range(3):
                    self.assertAlmostEqual(product[r, col], matrix[r, col], 9)
            # both factors are proper rotations
            for factor in (left, right):
                self.assertAlmostEqual(
                    factor.multiply(Vector(1, 0, 0))
                    .cross(factor.multiply(Vector(0, 1, 0)))
                    .dot(factor.multiply(Vector(0, 0, 1))),
                    1.0,
                    9,
                )
            return scales

        rotation = Matrix([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0]])
        self.assertAlmostEqual(reconstruct(rotation), (1, 1, 1), 9)

        uniform = Matrix([[2, 0, 0, 5], [0, 2, 0, 0], [0, 0, 2, 0]])
        self.assertAlmostEqual(reconstruct(uniform), (2, 2, 2), 9)

        stretch = Matrix([[3, 0, 0, 0], [0, 1, 0, 0], [0, 0, 2, 0]])
        self.assertAlmostEqual(reconstruct(stretch), (3, 2, 1), 9)

        mirror = Matrix([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
        self.assertAlmostEqual(reconstruct(mirror), (1, 1, -1), 9)

    def test_copies_are_independent_for_any_matrix(self):
        for label, rows in (
            ("rotation", [[0, -1, 0, 1], [1, 0, 0, 2], [0, 0, 1, 3]]),
            ("shear", [[1, 0.5, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]),
            ("stretch", [[2, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0]]),
        ):
            with self.subTest(matrix=label):
                original = Matrix(rows)
                for copied in (copy.copy(original), copy.deepcopy(original)):
                    self.assertIsNot(copied.wrapped, original.wrapped)
                    for r in range(3):
                        for col in range(4):
                            self.assertAlmostEqual(copied[r, col], original[r, col], 9)
                    copied.rotate(Axis.Z, 90)
                    self.assertAlmostEqual(original[0, 0], rows[0][0], 9)

    def test_svd_of_a_planar_transform(self):
        """A map acting only in a plane sorts its zero scale last."""
        planar = Matrix([[0.2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0]])
        left, scales, right = planar.svd()
        self.assertAlmostEqual(scales, (1, 0.2, 0), 9)
        # the in-plane axes have no component across the plane
        self.assertAlmostEqual(left[2, 0], 0, 9)
        self.assertAlmostEqual(left[2, 1], 0, 9)
        self.assertAlmostEqual(abs(left[2, 2]), 1, 9)

    def test_list_general_affine_multiplies_vector(self):
        non_uniform = Matrix([[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
        self.assertEqual(non_uniform.wrapped.Form(), gp_TrsfForm.gp_Other)
        self.assertAlmostEqual(non_uniform.multiply(Vector(1, 1, 1)), (2, 1, 1), 7)

        shear = Matrix([[1, 0.5, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
        self.assertAlmostEqual(shear.multiply(Vector(10, 20, 30)), (20, 20, 30), 7)

        projection = Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0]])
        self.assertAlmostEqual(projection.multiply(Vector(10, 20, 30)), (10, 20, 0), 7)


if __name__ == "__main__":
    unittest.main()
