.. _moving_objects:

Moving Objects
==============

build123d provides several ways to move, rotate and otherwise reposition an
object. The options differ along a few dimensions:

* the **mode** - builder mode, algebra mode, or operating directly on an object,
* whether they set an **absolute** location or make a **relative** change,
* whether they change the object **in place** or return a **copy**, and
* whether they position an object **before** or **after** it is created.

Almost every option builds on the :class:`~geometry.Location` and the rotation
*ordering* behind its orientation, so we start there.

.. _moving_objects_location:

The ``Location`` concept
------------------------

A :class:`~geometry.Location` represents a combination of translation and
rotation applied to a shape. It is the object used to position and orient
geometry, and it wraps two components:

* **position** - a 3D offset,
* **orientation** - a set of Euler angles (degrees) about the x, y and z axes.

There are three convenient ways to build one, and the three are equivalent:

.. code-block:: build123d

    Pos(1, 2, 3)                     # position only (a position-only Location subclass)
    Rot(X=45, Y=30, Z=20)            # orientation only (Rot is a short alias for Rotation)
    Location((1, 2, 3), (45, 30, 20))  # position and orientation together

``Pos`` is a position-only subclass of ``Location`` and ``Rot``/``Rotation`` is
an orientation-only subclass, so multiplying them composes to a single
``Location`` carrying both components:

.. code-block:: build123d

    Pos(1, 2, 3) * Rot(45, 30, 20) == Location((1, 2, 3), (45, 30, 20))

Every ``Shape`` (and ``Plane``, ``Axis`` and ``Location`` itself) exposes a
``location`` property, and the position and orientation can be read and written
through ``shape.position`` and ``shape.orientation``. Assigning a component sets
an absolute value; ``+=`` and ``-=`` make a relative change:

.. code-block:: build123d

    box_location = Box(1, 1, 1).location
    box_location.position = (1, 2, 3)        # absolute
    box_location.orientation = (30, 40, 50)  # absolute
    box_location.position += (3, 2, 1)       # relative

Locations compose with the ``*`` operator and flip direction with the ``-``
operator.

The orientation angles are applied in a particular **order** and about a
particular **reference frame**; together these are the rotation *ordering*.
This is covered in :ref:`moving_objects_rotation`.

.. _moving_objects_direct:

Direct manipulation methods
---------------------------

The direct methods and properties change an object that already exists. They
work on a *standalone* object - one you have created in algebra mode, or
extracted from a builder with ``.part``, ``.sketch`` or ``.line``. They come in
two flavours that are easy to confuse:

* **in place** - modify the object itself and return ``self``,
* **copy** - return a new, relocated object and leave the original untouched.

The copy methods correspond to multiplying in algebra mode (see
:ref:`moving_objects_algebra`); the in-place methods and the
``position``/``orientation`` properties have no algebra-mode equivalent.


Methods (move / locate and their copies)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The four core movement methods wrap ``move``/``locate`` and their copy variants:

.. list-table::
    :header-rows: 1

    * - Method
      - Positioning
      - Changes
      - Returns
    * - :meth:`~topology.Shape.move`
      - relative
      - in place
      - ``self``
    * - :meth:`~topology.Shape.moved`
      - relative
      - copy
      - new shape
    * - :meth:`~topology.Shape.locate`
      - absolute
      - in place
      - ``self``
    * - :meth:`~topology.Shape.located`
      - absolute
      - copy
      - new shape

``move`` applies a location *relative* to the object's current location, while
``locate`` sets an *absolute* location. Each takes a ``Location`` (or for
``moved``, also a ``Plane``):

.. code-block:: build123d

    shape.move(Location((1, 2, 3), (45, 0, 0)))   # relative, in place
    relocated = shape.moved(Location((1, 2, 3)))  # relative, copy
    shape.locate(Location((0, 0, 5)))             # absolute, in place
    relocated = shape.located(Location((0, 0, 5)))  # absolute, copy

Translation and rotation (convenience copies)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`~topology.Shape.translate` and :meth:`~topology.Shape.rotate` are
copy-style conveniences for the two most common relative operations. They always
return a new object and never change the original:

.. code-block:: build123d

    translated = shape.translate((x, y, z))          # relative translation, copy
    rotated = shape.rotate(axis, angle)              # relative rotation about an axis, copy

``rotate`` rotates about a given :class:`~geometry.Axis` by an angle in degrees.
See :ref:`moving_objects_rotate_axis` for examples.

.. note::
    ``translate`` and ``rotate`` (and the other transformation methods) have an
    optional ``transform`` parameter which regenerates the base geometry of the
    object itself instead of just changing its internal
    :class:`~geometry.Location`. This is quite slow and can be problematic; you
    almost always want the default behaviour, which only changes the location.

.. note::
    **Modifying an object after it has been added to a builder has no effect**

    The methods above act on a *standalone* object. If the object has already
    been added to an active builder, calling a mutating or copy method on the
    returned Python object does not change the model being built. For example:

    .. code-block:: build123d

        with BuildPart() as invalid:
            Cylinder(1, 2).moved(Location((1, 2, 3)))

    ``Cylinder(1, 2)`` creates the cylinder and immediately adds it to the
    ``BuildPart`` builder; ``.moved(...)`` is then applied to the temporary
    Python object that was returned, which has no connection back to the builder.
    The same applies to ``move``, ``locate``, ``located``, ``translate``,
    ``rotate`` and the ``position``/``orientation`` properties.

    Because the original object is still in the builder while the "moved" copy
    is discarded, this often looks like the object was duplicated at the origin.
    Placement must be decided *before* the object is created, which is what the
    ``Locations`` contexts and the ``rotation`` parameter are for (see
    :ref:`moving_objects_builder`). If you need to position an object you
    already have, create it (and optionally position it with algebraic methods)
    outside the builder then add the result to the builder with :func:`~operations_generic.insert`:.
    Alternatively, create it with ``mode=Mode.PRIVATE`` so it is not added
    immediately, insert a repositioned copy.


    .. code-block:: build123d

        blank = Box(10, 10, 10)  # not added to the builder
        with BuildPart() as part:
            insert(blank.rotate(Axis.Z, 45))            # add a rotated copy

    The same applies to an algebraically-positioned shape: inserting a placed copy directly
    adds two solids, because the shape adds itself on creation and the placed
    copy is then inserted again:

    .. code-block:: build123d

        with BuildPart() as part:
            insert(Pos(0, 0, 5) * Sphere(2))   # two solids - the sphere self-adds too

    Create it ``mode=Mode.PRIVATE`` instead, then insert the placed copy:

    .. code-block:: build123d

        with BuildPart() as part:
            sphere = Pos(0, 0, 5) * Sphere(2, mode=Mode.PRIVATE)
            insert(sphere)                     # one solid

    See also :ref:`moving_objects_faq`.

Properties (position and orientation)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``position`` and ``orientation`` properties read and write the components of
the object's :class:`~geometry.Location`. Assigning sets an **absolute** value;
``+=`` and ``-=`` make a **relative** change:

.. code-block:: build123d

    # absolute
    shape.position = (x, y, z)
    shape.orientation = (X, Y, Z)

    # relative
    shape.position += (x, y, z)
    shape.orientation += (X, Y, Z)

These are in-place mutations of the object's location.

.. _moving_objects_algebra:

Algebra mode
------------

The ``*`` placement arithmetic is the primary way to position objects in algebra mode: you multiply a
``Part``, ``Sketch`` or ``Curve`` by a ``Pos``, ``Rot``, ``Location`` or
``Plane`` to place it, since these objects define only their own topology and
not where in space they sit:

.. code-block:: build123d

    Pos(1, 2, 3) * Rot(45, 30, 20) * Box(1, 2, 3)     # position and rotation
    Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)  # on a plane

The ``with Locations(...)`` context covered below also works here. Outside a builder it
positions the objects created inside it, and with several locations the variable
holds all the placed copies:

.. code-block:: build123d

    with Locations((1, 2, 3), (4, 5, 6)):
        boxes = Box(1, 1, 1)      # two boxes, one at each location

    # equivalent to:
    boxes = Pos(1, 2, 3) * Box(1, 1, 1) + Pos(4, 5, 6) * Box(1, 1, 1)

Everything else from :ref:`moving_objects_direct` - the ``position``/
``orientation`` properties, the ``move``/``locate`` methods and their copy
variants - works here too, on any standalone object.

Multiplying locations and rotations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Location``s can be combined by multiplying them.
The same ``Location`` values can used in both modes: in algebra mode they are
written to the left of the object; in builder mode they are handed to a
``Locations`` context. The two blocks below are equivalent ways of placing a
cone at a rotated position:

.. code-block:: build123d

    # algebra mode
    cone = Pos(1, 0, 0) * Rot(X=45) * Cone(0.5, 0, 1)

.. code-block:: build123d

    # builder mode
    with BuildPart() as part:
        with Locations(Pos(1, 0, 0) * Rot(X=45)):
            Cone(0.5, 0, 1)

.. seealso::
    The :ref:`location_arithmetics` page works through these combinations with
    rendered examples of each position and rotation.

.. _moving_objects_builder:

Builder mode
------------

In builder mode an object adds itself to the builder as soon as it is created,
so its position and orientation must be decided *before* the object is made.
Two builder-specific tools do this: a ``Locations`` context and the ``rotation``
parameter.

Location contexts
^^^^^^^^^^^^^^^^^

The :class:`~build_common.Locations` context (and ``GridLocations``,
``PolarLocations`` and ``HexLocations``) makes one or more local ``Location``
objects active within a scope, and every object created inside that scope is
placed at each active location:

.. code-block:: build123d

    with BuildPart() as part:
        with Locations((0, 10), (0, -10)):
            Box(1, 1, 1)
            with GridLocations(x_spacing=5, y_spacing=5, x_count=2, y_count=2):
                Sphere(1)
            Cylinder(1, 1)

Here ``Locations`` creates two local positions at (0, 10) and (0, -10): ``Box``
is within its scope so two boxes are created, the ``GridLocations`` context
creates four positions that apply to the ``Sphere``, and ``Cylinder`` is out of
the ``GridLocations`` scope but still within ``Locations`` so two cylinders are
created.

These contexts create ``Location`` objects, not just points - ``PolarLocations``,
for example, also rotates objects within its scope, much as the hour and minute
hand on an analogue clock.

``Locations`` can also be used around a builder to move the completed output; the
enclosed builder still constructs locally and the active locations are applied
once when it publishes:

.. code-block:: build123d

    with BuildPart() as model:
        with Locations((-20, 0), (20, 0)):
            with BuildSketch() as holes:
                Circle(3)
            extrude(amount=5)

Here ``holes.sketch_local`` contains one circle on local ``Plane.XY`` while
``holes.sketch`` contains two placed circles, because the enclosing ``Locations``
context is active when the sketch is published to ``model``. The same rule
applies to an entire ``BuildPart``.

Locations contexts can be nested, and the active local locations can be read from
the context object:

.. code-block:: build123d

    with Locations(Plane.XY, Plane.XZ):
        locs = GridLocations(1, 1, 2, 2)
        for l in locs:
            print(l)

.. code-block::

    # Points at the four locations for each of the two planes
    Location(p=(-0.50,-0.50,0.00), o=(0.00,-0.00,0.00))
    Location(p=(-0.50,0.50,0.00), o=(0.00,-0.00,0.00))
    Location(p=(0.50,-0.50,0.00), o=(0.00,-0.00,0.00))
    Location(p=(0.50,0.50,0.00), o=(0.00,-0.00,0.00))
    Location(p=(-0.50,-0.00,-0.50), o=(90.00,-0.00,0.00))
    Location(p=(-0.50,0.00,0.50), o=(90.00,-0.00,0.00))
    Location(p=(0.50,0.00,-0.50), o=(90.00,-0.00,0.00))
    Location(p=(0.50,0.00,0.50), o=(90.00,-0.00,0.00))

The ``rotation`` parameter
^^^^^^^^^^^^^^^^^^^^^^^^^^

Most primitives also accept a ``rotation`` parameter as a shorthand for the same
rotation at creation:

.. code-block:: build123d

    with BuildPart() as part:
        Box(10, 10, 10, rotation=(10, 20, 30))

Everything else
^^^^^^^^^^^^^^^

Every method from :ref:`moving_objects_direct` and
:ref:`moving_objects_algebra` works the same way here - on a *standalone*
object. The only difference is timing: once an object is in a builder you cannot
move or copy it, because it added itself when it was created. To use the
algebraic methods in a builder, create the object with ``mode=Mode.PRIVATE``
(or place it outside the builder) and then add the result with
:func:`~operations_generic.insert`:

.. code-block:: build123d

    with BuildPart() as part:
        sphere = Pos(0, 0, 5) * Sphere(2, mode=Mode.PRIVATE)
        insert(sphere)

This is explained in full in the note in :ref:`moving_objects_direct`.

.. _moving_objects_rotation:

Understanding rotation
----------------------

Rotation reuses the same :class:`~geometry.Location` machinery as positioning:
the orientation component of a location, with a rotation *ordering* behind it.

The building blocks
^^^^^^^^^^^^^^^^^^^

1. **Euler angles** - ``Rot(X=a, Y=b, Z=c)``, ``Rotation((a, b, c))``, the
   ``rotation`` parameter on primitives, and ``shape.orientation`` all describe
   a rotation by one angle about each axis.

2. **About an arbitrary axis** - ``Rot(axis=Axis(...), angle=d)`` and
   ``shape.rotate(axis, d)`` rotate by a single angle about any
   :class:`~geometry.Axis`. Use this when the rotation is not aligned with the
   x, y or z axes, such as rotating around an edge or the center of mass.

3. **By composing locations** - ``Locations(Rot(...))`` in builder mode and
   ``Rot(...) * shape`` in algebra mode both apply a rotation by composing it
   into a location.

``Rot`` and ``Rotation`` are the same class (``Rot`` is just a short alias), so
``Rot((a, b, c))``, ``Rot(X=a, Y=b, Z=c)``, ``Rotation((a, b, c))`` and
``Location((0, 0, 0), (a, b, c))`` are all equivalent.

Rotation ordering
^^^^^^^^^^^^^^^^^

.. _moving_objects_ordering:

Rotations about more than one axis do **not** commute: rotating 90 degrees about
x and then about y gives a different result than the reverse order. The
``ordering`` parameter of ``Location`` and ``Rotation`` controls both the order
of the angles and the reference frame the rotations are applied about.

* **Intrinsic** (default) - the rotations are applied about the *local* axes of
  the object or plane being rotated. With ``Intrinsic.XYZ`` the x-angle is
  applied first, then the y-angle about the already-rotated axis, then the
  z-angle. This is what most BREP CAD systems use.
* **Extrinsic** - the rotations are applied about the *global* x, y and z axes.
  ``Extrinsic.XYZ`` is what OpenSCAD uses.

Every permutation is available (``Intrinsic.XYZ``, ``Intrinsic.YXZ``,
``Extrinsic.ZYX``, and so on), and the default is ``Intrinsic.XYZ``:

.. code-block:: build123d

    loc = Location((1, 2, 3), (10, 20, 30), ordering=Intrinsic.XYZ)
    rot = Rotation((10, 20, 30), ordering=Extrinsic.XYZ)
    rotated = shape.rotate(Axis.Z, 45)   # single-axis, ordering is irrelevant

For a single non-zero rotation - that is, only one of the three angles is
non-zero - intrinsic and extrinsic are identical, so ``ordering`` only matters
when two or more angles are non-zero.

To make the order of a multi-axis rotation explicit, compose the individual
rotations with ``*`` instead of relying on the ordering of one tuple:

.. code-block:: build123d

    Rot(X=45) * Rot(Y=30) * Rot(Z=20)   # x, then y, then z, unambiguously

This works in both modes - left of an object in algebra mode, or inside a
``Locations`` context in builder mode.

The ``Plane`` is a convenient way to capture this for construction. ``Plane.ZX``
is a global plane, but ``Plane.ZX.rotated((0, 0, 90))`` returns a new plane
rotated about its own axes, and ``Plane(origin, z_dir, x_dir)`` lets you define
an arbitrarily oriented frame directly.

.. _moving_objects_rotate_axis:

Rotating about an arbitrary axis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is no single convenience method to "rotate about this edge" or "rotate
about the center of mass parallel to that axis". Instead you construct the
:class:`~geometry.Axis` yourself and hand it to ``shape.rotate`` or
``Rotation(axis=..., angle=...)``.

To rotate about an axis through the object's center of mass, use the center as
the axis origin and a direction:

.. code-block:: build123d

    through_center = Axis(part.center(), Axis.Z.direction)  # CoM-parallel to Z
    tilted = part.rotate(through_center, 45)

``part.center()`` returns the center of mass of a part; ``Axis.Z.direction`` is
the unit vector of the world z-axis. Any direction works.

To rotate around an edge, use the edge's center as the axis origin and its
tangent at the midpoint as the direction. ``edge % 0.5`` is the tangent vector
at the middle of the edge, and ``edge @ 0.5`` the point there:

.. code-block:: build123d

    edge_axis = Axis(edge.center(), edge % 0.5)   # along the edge
    rotated = part.rotate(edge_axis, 90)

For a straight edge ``edge % 0.5`` is simply the edge's direction; for a curved
edge it is the tangent at the midpoint, which is often what you want. These
techniques are equivalent to ``Rot(axis=edge_axis, angle=90) * part`` in algebra
mode.
.. _moving_objects_comparison:

Choosing an approach
--------------------

The table below summarises the options and, most importantly, distinguishes
**relative** from **absolute** positioning and **in place** from **copy**
behaviour.

.. list-table:: Movement and rotation options
    :header-rows: 1

    * - Approach
      - Modes
      - Positioning
      - In place / Copy
      - Use case
    * - ``Locations(...)``
      - builder
      - during creation
      - \-
      - Especially useful for creating multiple copies at several locations, or using the special grid or polar location functions, or when composing multiple objects inside the context.
    * - ``rotation=``
      - any
      - during creation
      - \-
      - Best for simple primitives
    * - ``Pos * shape``
      - algebra
      - absolute
      - copy
      - Place an object at an absolute position.
    * - ``Rot * shape``
      - algebra
      - absolute
      - copy
      - Rotate an object about the origin (or compose with ``Pos``).
    * - ``Location(...) * shape``
      - algebra
      - absolute
      - copy
      - Position and rotate in one expression.
    * - ``Plane.rotated(...)``
      - algebra
      - absolute
      - copy
      - Re-orient the construction frame; place sketches and parts on a plane.
    * - ``shape.position +=``
      - direct
      - relative
      - in place
      - Quick tweak of a standalone object's position.
    * - ``shape.orientation =``
      - direct
      - absolute
      - in place
      - Quick tweak of a standalone object's orientation.
    * - ``shape.locate(...)``
      - direct
      - absolute
      - in place
      - Absolutely reposition the object itself.
    * - ``shape.located(...)``
      - direct
      - absolute
      - copy
      - Absolutely reposition a copy; keep the original.
    * - ``shape.move(...)``
      - direct
      - relative
      - in place
      - Nudge the object itself relative to its current location.
    * - ``shape.moved(...)``
      - direct
      - relative
      - copy
      - Nudge a copy relative to its current location.
    * - ``shape.translate(vec)``
      - direct
      - relative
      - copy
      - Translate a copy by a vector.
    * - ``shape.rotate(axis, angle)``
      - direct
      - relative (about axis)
      - copy
      - Rotate a copy about an arbitrary axis (e.g. an edge or CoM).
    * - ``Locations(Rot(...))``
      - builder
      - relative (composition)
      - copy
      - Explicitly ordered multi-axis rotation.
    * - ``Rot(...) * shape``
      - algebra
      - relative (composition)
      - copy
      - Explicitly ordered multi-axis rotation.

Use cases
^^^^^^^^^

* Builder mode with ``Locations`` or ``rotation=`` is the natural choice when
  the placement is a property of the design - a sketch on a face, a hole at a
  coordinate. You decide where things go before they are created, which is the
  robust, parametric way to build.

* Prefer ``Locations``/``GridLocations`` over many explicit copies when you want
  many placements of the *same* geometry - a locations context is usually more
  performant. The copy methods are the right tool when you need to keep the
  original geometry and place one or two copies.

* Copy methods shine when combining an object into something else. A copy placed
  with ``moved``/``located``/``*`` can be fused into a result with ``+`` in
  algebra mode, or inserted into a builder with
  :func:`~operations_generic.insert` - make the shape ``mode=Mode.PRIVATE`` so it
  does not add itself on creation (see :ref:`moving_objects_builder`):

  .. code-block:: build123d

      result = Box(10, 10, 10) + Pos(0, 0, 5) * Sphere(2)   # algebra mode

  .. code-block:: build123d

      with BuildPart() as part:
          sphere = Pos(0, 0, 5) * Sphere(2, mode=Mode.PRIVATE)
          insert(sphere)                   # add the placed copy

* In-place methods and properties are best for tweaking an existing shape's ``position``,
    for example repositioning an object center well after it was created.

* Plan the rotation when more than one axis is involved. Either choose an
  explicit ``ordering`` or compose ``Rot(...) * Rot(...)`` so the order is
  unambiguous.

.. _moving_objects_faq:

Frequently Asked Questions
--------------------------

Why is my moved object duplicated at the origin in builder mode?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is what happens when you modify or copy an object after it has already been
added to a builder. The full explanation and workaround are in the note in
:ref:`moving_objects_direct`.
