##########
Operations
##########

Operations are functions that take objects as inputs and transform them into new objects. For example, a 2D Sketch can be extruded to create a 3D Part. All operations are Python functions which can be applied using both the Algebra and Builder APIs. It's important to note that objects created by operations are not affected by ``Locations``, meaning their position is determined solely by the input objects used in the operation.

Here are a couple ways to use :func:`~operations_part.extrude`, in Builder and Algebra mode:

.. code-block:: python

    with BuildPart() as cylinder:
        with BuildSketch():
            Circle(radius)
        extrude(amount=height)

.. code-block:: python

    cylinder = extrude(Circle(radius), amount=height)

The following table summarizes all of the available operations. Operations marked as 1D are
applicable to BuildLine and Algebra Curve, 2D to BuildSketch and Algebra Sketch, 3D to
BuildPart and Algebra Part.

+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| Operation                                    | Description                        | 0D | 1D | 2D | 3D | Example                |
+==============================================+====================================+====+====+====+====+========================+
| :func:`~operations_generic.add`              | Add object to builder              |    | ✓  | ✓  | ✓  | :ref:`16 <ex 16>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.bounding_box`     | Add bounding box as Shape          |    | ✓  | ✓  | ✓  |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.chamfer`          | Bevel Vertex or Edge               |    |    | ✓  | ✓  | :ref:`9 <ex 9>`        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.extrude`             | Draw 2D Shape into 3D              |    |    |    | ✓  | :ref:`3 <ex 3>`        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.fillet`           | Radius Vertex or Edge              |    |    | ✓  | ✓  | :ref:`9 <ex 9>`        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.loft`                | Create 3D Shape from sections      |    |    |    | ✓  | :ref:`24 <ex 24>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.make_brake_formed`   | Create sheet metal parts           |    |    |    | ✓  |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_sketch.make_face`         | Create a Face from Edges           |    |    | ✓  |    | :ref:`4 <ex 4>`        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_sketch.make_hull`         | Create Convex Hull from Edges      |    |    | ✓  |    |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.mirror`           | Mirror about Plane                 |    | ✓  | ✓  | ✓  | :ref:`15 <ex 15>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.offset`           | Inset or outset Shape              |    | ✓  | ✓  | ✓  | :ref:`25 <ex 25>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.project`          | Project points, lines or Faces     | ✓  | ✓  | ✓  |    |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.project_workplane`   | Create workplane for projection    |    |    |    |    |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.revolve`             | Swing 2D Shape about Axis          |    |    |    | ✓  | :ref:`23 <ex 23>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.scale`            | Change size of Shape               |    | ✓  | ✓  | ✓  |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.section`             | Generate 2D slices from 3D Shape   |    |    |    | ✓  |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.split`            | Divide object by Plane             |    | ✓  | ✓  | ✓  | :ref:`27 <ex 27>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_generic.sweep`            | Extrude 1/2D section(s) along path |    |    | ✓  | ✓  | :ref:`14 <ex 14>`      |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_part.thicken`             | Expand 2D section(s)               |    |    |    | ✓  |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+
| :func:`~operations_sketch.trace`             | Convert lines to faces             |    |    | ✓  |    |                        |
+----------------------------------------------+------------------------------------+----+----+----+----+------------------------+

Reference
^^^^^^^^^
.. autoclass:: operations_generic.add
.. autoclass:: operations_generic.bounding_box
.. autoclass:: operations_generic.chamfer
.. autoclass:: operations_part.extrude
.. autoclass:: operations_generic.fillet
.. autoclass:: operations_part.loft
.. autoclass:: operations_part.make_brake_formed
.. autoclass:: operations_sketch.make_face
.. autoclass:: operations_sketch.make_hull
.. autoclass:: operations_generic.mirror
.. autoclass:: operations_generic.offset
.. autoclass:: operations_generic.project
.. autoclass:: operations_part.project_workplane
.. autoclass:: operations_part.revolve
.. autoclass:: operations_generic.scale
.. autoclass:: operations_part.section
.. autoclass:: operations_generic.split
.. autoclass:: operations_generic.sweep
.. autoclass:: operations_part.thicken
.. autoclass:: operations_sketch.trace
