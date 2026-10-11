.. _key_concepts_algebra:

###########################
Key Concepts (algebra mode)
###########################

Build123d's algebra mode works on objects of the classes ``Shape``, ``Part``, ``Sketch`` and ``Curve`` and is based on two concepts:

1. **Object arithmetic**
2. **Placement arithmetic**

Object arithmetic
=====================

-   Creating a box and a cylinder centered at ``(0, 0, 0)``

    .. code-block:: build123d

        b = Box(1, 2, 3)
        c = Cylinder(0.2, 5)

-   Fusing a box and a cylinder

    .. code-block:: build123d

        r = Box(1, 2, 3) + Cylinder(0.2, 5)

-   Cutting a cylinder from a box

    .. code-block:: build123d

        r = Box(1, 2, 3) - Cylinder(0.2, 5)

-   Intersecting a box and a cylinder

    .. code-block:: build123d

        r = Box(1, 2, 3) & Cylinder(0.2, 5)

**Notes:**

* `b`, `c` and `r` are instances of class ``Compound`` and can be viewed with every viewer that can show ``build123d.Compound`` objects.
* A discussion around performance can be found in :ref:`algebra_performance`.
* A mathematically formal definition of the algebra can be found in :ref:`algebra_definition`.


.. _algebra_sewing:

Sewing sheet surfaces
---------------------

``Shell`` objects are sheet surfaces rather than solids, so ``+`` sews their faces
together along shared edges instead of fusing them. A fuse would leave the faces
side by side in a ``Compound``; sewing produces one connected surface, which is
what sheet metal parts are built from.

-   Adding a wall to a base surface

    .. code-block:: build123d

        base = Shell(Rectangle(20, 20).face())
        wall = Plane(origin=(10, 0, 5), z_dir=(1, 0, 0), x_dir=(0, 1, 0)) * Rectangle(20, 10)
        sheet = base + wall

Sewing applies whenever a ``Shell`` takes part in the addition - ``Shell + Face``,
``Face + Shell`` and ``Shell + Shell`` - and any 2D operand contributes its faces,
so sketch objects can be added directly:

    .. code-block:: build123d

        sheet += Plane(origin=(-10, 0, 5), z_dir=(1, 0, 0), x_dir=(0, 1, 0)) * Rectangle(20, 10)

**Notes:**

* Adding to a ``Shell`` always returns a ``Shell``. Faces that cannot be sewn into
  one connected shell - disjoint pieces, or three faces meeting on a single edge -
  raise a ``ValueError`` rather than silently returning a ``Compound``, so the
  result type never depends on the geometry.
* The result is cleaned, so faces that are coplanar with their neighbours merge
  into one face. Use the ``SkipClean`` context manager to keep the seam.
* A ``Sketch`` on the left keeps sketch semantics: ``sketch + shell`` fuses as
  before and stays a ``Sketch`` or ``Compound``. Put the ``Shell`` first to sew.

Placement arithmetic
=======================

See :ref:`Moving Objects page <moving_objects_algebra>`.

A ``Part``, ``Sketch`` or ``Curve`` does not have any location or rotation
parameter. An object defines its topology - shape, size and center - but does
not know where in space it will be located. Instead it is relocated with the
``*`` operator onto a plane and to a location relative to that plane:

.. code-block:: build123d

    plane * alg_compound              # on a plane (e.g. Plane.XZ)
    location * alg_compound           # at an absolute location
    plane * location * alg_compound   # on a plane, then at a location in the plane's frame

Detailed, rendered examples can be found in :ref:`location_arithmetics`.


.. _part_sketch_curve:

Part, Sketch and Curve
======================

:class:`~topology.Part`, :class:`~topology.Sketch` and :class:`~topology.Curve`
are :class:`~topology.Compound` subclasses that collect geometry of one dimension.
They are shapes like any other - they can be placed, selected from and passed to
operations - and they are what the Builders return:

.. list-table:: Geometry containers and Builder results
    :header-rows: 1
    :widths: 15 30 25 30

    * - Container
      - Geometry it collects
      - Select its contents
      - Builder result
    * - ``Part``
      - 3D solids
      - ``.solids()``
      - ``BuildPart.part``
    * - ``Sketch``
      - 2D faces
      - ``.faces()``
      - ``BuildSketch.sketch``
    * - ``Curve``
      - 1D edges
      - ``.edges()``
      - ``BuildLine.line``

The dimension describes the geometry, not its position: a sketch can be placed on
``Plane.XZ``, and a curve can follow a path in 3D space. A container can hold more
than one shape, including disconnected shapes, so a ``Part`` is not necessarily a
single :class:`~topology.Solid`, nor a ``Curve`` a single connected
:class:`~topology.Wire`. The selectors in the table return the individual shapes
as a :class:`~topology.ShapeList`.

Primitives usually already are the right container: ``Box(20, 10, 5)`` is a
``Part`` and ``Rectangle(20, 10)`` is a ``Sketch``. Curve primitives are the
exception - ``Line`` is an ``Edge`` and ``Polyline`` a ``Wire`` - and a ``Curve``
can collect their edges when one is needed.

Constructing a container only groups existing geometry. It does not fill an
outline, extrude faces or fuse solids; the operations do that, and each returns
the container of the next dimension up:

.. code-block:: build123d

    perimeter = Polyline((0, 0), (20, 0), (20, 10), (0, 10), close=True)
    profile = make_face(perimeter.edges())  # a Sketch
    block = extrude(profile, amount=5)  # a Part

In the same way, grouping two solids in a ``Part`` does not fuse them; that is
what the ``+`` operator above is for.

Combining Builder and algebra modes
===================================

Builder contexts such as ``BuildPart`` collect operations; they are not shapes and
therefore cannot be combined directly with algebra operators. Extract the completed
geometry with ``.line``, ``.sketch``, or ``.part`` before using it in algebra mode:

.. code-block:: build123d

    with BuildPart() as base:
        Box(80, 60, 10)

    with BuildPart() as bore:
        Cylinder(11, 10)

    result = base.part - bore.part

``BuildLine.line`` and ``BuildSketch.sketch`` work the same way, giving a
``Curve`` and a ``Sketch`` that operations such as ``make_face`` and ``extrude``
accept directly.


Selecting features of a result
==============================

The result of an operation carries a record of what that operation did, so the
selectors that builders offer work on it too. ``Select.LAST`` returns the features the
right operand brought in or the operation created, and ``Select.NEW`` only those that
existed in neither operand:

.. code-block:: build123d

    tray = Box(20, 20, 5) - Pos(Z=1.5) * Box(16, 16, 5)
    pocket_faces = tray.faces(Select.LAST)
    fillet(tray.edges(Select.NEW), 1)

See :ref:`when a feature came to be <when>` for the details.

Combining both concepts
=======================

**Object arithmetic** and **placement at locations** can be combined in a single
expression, since ``*`` composes placement (see
:ref:`Moving Objects <moving_objects_algebra>`) and the boolean operators combine
the results:

 .. code-block:: build123d

    b = Plane.XZ * Rot(X=30) * Box(1, 2, 3) + Plane.YZ * Pos(X=-1) * Cylinder(0.2, 5)

**Note:** In Python ``*`` binds stronger then ``+``, ``-``, ``&``, hence brackets are not needed.
