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
| :func:`~operations_sketch.full_round`        | Round-off Face along given Edge    |    |    | ✓  |    | :ref:`ttt-24-spo-06`   |
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

The following table summarizes all of the selectors that can be used within
the scope of a Builder. Note that they will extract objects from the builder that is
currently within scope without it being explicitly referenced.

+---------------------------------+--------------------------------------+----------------------+
|                                                                        |        Builder       |                                 
+---------------------------------+--------------------------------------+------+--------+------+
| Selector                        | Description                          | Line | Sketch | Part |
+=================================+======================================+======+========+======+
| :func:`~build_common.edge`      | Select edge from current builder     |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.edges`     | Select edges from current builder    |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.face`      | Select face from current builder     |      |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.faces`     | Select faces from current builder    |      |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.solid`     | Select solid from current builder    |      |        |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.solids`    | Select solids from current builder   |      |        |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.vertex`    | Select vertex from current builder   |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.vertices`  | Select vertices from current builder |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.wire`      | Select wire from current builder     |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+
| :func:`~build_common.wires`     | Select wires from current builder    |  ✓   |   ✓    |   ✓  |
+---------------------------------+--------------------------------------+------+--------+------+



Reference
^^^^^^^^^
.. autofunction:: operations_generic.add
.. autofunction:: operations_generic.bounding_box
.. autofunction:: operations_generic.chamfer
.. autofunction:: operations_part.extrude
.. autofunction:: operations_generic.fillet
.. autofunction:: operations_sketch.full_round
.. autofunction:: operations_part.loft
.. autofunction:: operations_part.make_brake_formed
.. autofunction:: operations_sketch.make_face
.. autofunction:: operations_sketch.make_hull
.. autofunction:: operations_generic.mirror
.. autofunction:: operations_generic.offset
.. autofunction:: operations_generic.project
.. autofunction:: operations_part.project_workplane
.. autofunction:: operations_part.revolve
.. autofunction:: operations_generic.scale
.. autofunction:: operations_part.section
.. autofunction:: operations_generic.split
.. autofunction:: operations_generic.sweep
.. autofunction:: operations_part.thicken
.. autofunction:: operations_sketch.trace

.. autofunction:: build_common.edge
.. autofunction:: build_common.edges
.. autofunction:: build_common.face
.. autofunction:: build_common.faces
.. autofunction:: build_common.solid
.. autofunction:: build_common.solids
.. autofunction:: build_common.vertex
.. autofunction:: build_common.vertices
.. autofunction:: build_common.wire
.. autofunction:: build_common.wires
