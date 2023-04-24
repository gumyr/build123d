##################
CAD Object Centers
##################

Finding the center of a CAD object is a surprisingly complex operation.  To illustrate
let's consider a simple isosceles triangle enclosed in its bounding box:

.. image:: assets/center.svg
    :align: center

One can see that there is a significant difference between the centers of its geometry and
that of its bounding box.

To allow the designer to choose the center that makes the most sense for the given
shape there are three possible values for the :class:`~build_enums.CenterOf` Enum:

+--------------------------------+----+----+----+----------+
| :class:`~build_enums.CenterOf` | 1D | 2D | 3D | Compound |
+================================+====+====+====+==========+
| CenterOf.BOUNDING_BOX          | ✓  | ✓  | ✓  | ✓        |
+--------------------------------+----+----+----+----------+
| CenterOf.GEOMETRY              | ✓  | ✓  |    |          |
+--------------------------------+----+----+----+----------+
| CenterOf.MASS                  | ✓  | ✓  | ✓  | ✓        |
+--------------------------------+----+----+----+----------+

