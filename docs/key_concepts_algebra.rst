###########################
Key Concepts (algebra mode)
###########################

Build123d's algebra mode works on objects of the classes ``Shape``, ``Part``, ``Sketch`` and ``Curve`` and is based on two concepts:

1. **Object arithmetic**
2. **Placement arithmetic**

Object arithmetic
=====================

-   Creating a box and a cylinder centered at ``(0, 0, 0)``

    .. code-block:: python

        b = Box(1, 2, 3)
        c = Cylinder(0.2, 5)

-   Fusing a box and a cylinder

    .. code-block:: python

        r = Box(1, 2, 3) + Cylinder(0.2, 5)

-   Cutting a cylinder from a box

    .. code-block:: python

        r = Box(1, 2, 3) - Cylinder(0.2, 5)

-   Intersecting a box and a cylinder

    .. code-block:: python

        r = Box(1, 2, 3) & Cylinder(0.2, 5)

**Notes:**

* `b`, `c` and `r` are instances of class ``Compound`` and can be viewed with every viewer that can show ``build123d.Compound`` objects.
* A discussion around performance can be found in :ref:`algebra_performance`.
* A mathematically formal definition of the algebra can be found in :ref:`algebra_definition`.


Placement arithmetic
=======================

A ``Part``, ``Sketch`` or ``Curve`` does not have any location or rotation parameter.
The rationale is that an object defines its topology (shape, sizes and its center), but does not know 
where in space it will be located. Instead, it will be relocated with the ``*`` operator onto a plane 
and to location relative to the plane (similar ``moved``). 

The generic forms of object placement are:

1. Placement on ``plane`` or at ``location`` relative to XY plane:

    .. code-block:: python

        plane * alg_compound
        location * alg_compound

2. Placement on the ``plane`` and then moved relative to the ``plane`` by ``location`` 
(the location is relative to the local corrdinate system of the plane).

    .. code-block:: python

        plane * location * alg_compound


Details can be found in :ref:`location_arithmetics`.

Examples:

-   Box on the ``XY`` plane, centered at `(0, 0, 0)` (both forms are equivalent):

    .. code-block:: python

        Plane.XY * Box(1, 2, 3)

        Box(1, 2, 3)

    Note: On the ``XY`` plane no placement is needed (mathematically ``Plane.XY *`` will not change the 
    location of an object).

-   Box on the ``XY`` plane centered at `(0, 1, 0)` (all three are equivalent):

    .. code-block:: python

        Plane.XY * Pos(0, 1, 0) * Box(1, 2, 3)

        Pos(0, 1, 0) * Box(1, 2, 3) 

        Pos(Y=1) * Box(1, 2, 3)

    Note: Again, ``Plane.XY`` can be omitted.

-   Box on plane ``Plane.XZ``:

    .. code-block:: python

        Plane.XZ * Box(1, 2, 3)

-   Box on plane ``Plane.XZ`` with a location ``(X=1, Y=2, Z=3)`` relative to the ``XZ`` plane, i.e., 
    using the x-, y- and z-axis of the ``XZ`` plane:

    .. code-block:: python

        Plane.XZ * Pos(1, 2, 3) * Box(1, 2, 3)

-   Box on plane ``Plane.XZ`` moved to ``(X=1, Y=2, Z=3)`` relative to this plane and rotated there 
    by the angles `(X=0, Y=100, Z=45)` around ``Plane.XZ`` axes:

    .. code-block:: python

        Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)

        Location((1, 2, 3), (0, 100, 45)) * Box(1, 2, 3)

    Note: ``Pos * Rot`` is the same as using ``Location`` directly

-   Box on plane ``Plane.XZ`` rotated on this plane by the angles ``(X=0, Y=100, Z=45)`` (using the 
    x-, y- and z-axis of the ``XZ`` plane) and then moved to ``(X=1, Y=2, Z=3)`` relative to the ``XZ`` plane:

    .. code-block:: python

        Plane.XZ * Rot(0, 100, 45) * Pos(0,1,2) * Box(1, 2, 3)


Combing both concepts
==========================

**Object arithmetic** and **Placement at locations** can be combined:

 .. code-block:: python

    b = Plane.XZ * Rot(X=30) * Box(1, 2, 3) + Plane.YZ * Pos(X=-1) * Cylinder(0.2, 5)

**Note:** In Python ``*`` binds stronger then ``+``, ``-``, ``&``, hence brackets are not needed.

