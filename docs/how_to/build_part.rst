.. _building_parts:

##############
Building parts
##############

A part is a solid: a shape with volume, and usually the thing being
designed. Most parts start as a sketch that is made solid, and are then
worked on, with features added to their faces, holes drilled, edges
rounded and the inside hollowed out. This guide shows how to do each of
those.

In builder mode a part is made inside a ``BuildPart``, which collects
the solids created in it and applies each operation to what it holds. In
algebra mode solids are combined with ``+``, ``-`` and ``&``, and each
operation is given the shape to work on and returns the result.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - make a sketch solid
      - ``extrude``
    * - make a solid some other way
      - the table under "Choose how to make the solid"
    * - add, cut or trim with solids
      - ``mode=``, or ``+``, ``-``, ``&``
    * - add a feature to a face
      - a sketch on the face, then ``extrude``
    * - drill holes
      - ``Hole``, ``CounterBoreHole``, ``CounterSinkHole``
    * - round or bevel edges
      - ``fillet``, ``chamfer``
    * - hollow a part, or cut it open
      - ``offset`` with ``openings``, ``split``
    * - control what an operation works on
      - pending sketches, or pass them yourself
    * - use one part as a tool on another
      - ``insert(part, mode=...)``, a nested ``BuildPart``, or ``-``
    * - measure a part or get its faces
      - ``faces()``, ``edges()``, ``volume``
    * - work in inches or other units
      - ``IN``, ``MM`` and the other constants

In the pictures hidden edges are dotted, and where an example starts
from sketches they are drawn in blue.

***********************
Make a sketch solid
***********************

.. image:: /how_to/assets/build_part/part_extrude.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [extrude]
            :end-before: [extrude]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

:func:`~operations_part.extrude` pushes a sketch along the direction it
faces, by ``amount``. A negative amount goes the other way, and
``both=True`` goes both ways from the sketch.

In builder mode the sketch is written inside the part and ``extrude``
takes it from there; in algebra mode ``extrude`` is given the sketch.
:ref:`sketching` covers making the sketch, and
:ref:`tutorial_sketch_then_extrude` goes through this step by step.

********************************
Choose how to make the solid
********************************

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - The shape is
      - Use
    * - the same cross-section all the way along
      - :func:`~operations_part.extrude`
    * - a profile turned round an axis
      - :func:`~operations_part.revolve`
    * - a blend from one cross-section to another
      - :func:`~operations_part.loft`
    * - a cross-section carried along a path
      - :func:`~operations_generic.sweep`
    * - a curved face given a thickness
      - :func:`~operations_part.thicken`
    * - a box, cylinder, sphere, cone, torus or wedge
      - :class:`~objects_part.Box`, :class:`~objects_part.Cylinder`,
        :class:`~objects_part.Sphere`, :class:`~objects_part.Cone`,
        :class:`~objects_part.Torus`, :class:`~objects_part.Wedge`

:ref:`tutorial_beyond_extrude` uses ``revolve``, ``loft`` and ``sweep``
on one part, and :ref:`tutorial_combining_solids` discusses when
ready-made solids are the better tool.

*********************************
Add, cut and trim with solids
*********************************

.. image:: /how_to/assets/build_part/part_combine.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [combine]
            :end-before: [combine]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [combine_algebra]
            :end-before: [combine_algebra]

Solids combine as sketch objects do. In builder mode every object has a
``mode``: ``Mode.ADD``, the default, joins it to the part;
``Mode.SUBTRACT`` cuts it out; ``Mode.INTERSECT`` keeps only what the
part and the object have in common, shown here by the sphere that rounds
off the corners. In algebra mode the three are ``+``, ``-`` and ``&``.

In builder mode the result is ``block.part``. In algebra mode ``block``
is the part.

***************************
Add a feature to a face
***************************

.. image:: /how_to/assets/build_part/part_on_face.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [on_face]
            :end-before: [on_face]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [on_face_algebra]
            :end-before: [on_face_algebra]

A feature is a sketch placed on a face of the part and extruded: outward
with a positive amount to add material, inward with a negative one and
``Mode.SUBTRACT`` to cut. The face is selected from the part as it
stands, so the second selection here finds the top of the new pad, not
the top of the box.

:ref:`placing_sketches` covers putting a sketch on a face, turning it
and measuring it from a corner, and :ref:`selectors` covers choosing the
face.

***************
Drill holes
***************

.. image:: /how_to/assets/build_part/part_holes.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [holes]
            :end-before: [holes]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [holes_algebra]
            :end-before: [holes_algebra]

:class:`~objects_part.Hole`, :class:`~objects_part.CounterBoreHole` and
:class:`~objects_part.CounterSinkHole` are solids that cut by default.
Each drills down from its place, into the face it is placed on.

In builder mode ``Locations`` is given the face, which puts the place at
the centre of the face and facing out of it, and the grid of four is
laid out about that place. With no ``depth`` a hole goes right through
the part. In algebra mode the hole is placed with the face's plane and
subtracted, and it needs a ``depth``, since on its own it has no part to
go through.

*****************************
Round and bevel the edges
*****************************

.. image:: /how_to/assets/build_part/part_edges.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [edges]
            :end-before: [edges]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [edges_algebra]
            :end-before: [edges_algebra]

:func:`~operations_generic.fillet` rounds the edges it is given and
:func:`~operations_generic.chamfer` bevels them. ``filter_by(Axis.Z)``
keeps the four upright edges, and ``group_by(Axis.Z)[-1]`` is every edge
at the top, which by then includes the four new rounded corners.

Do the larger rounding first, and leave edge finishing until the shape
is settled: every fillet adds faces and edges that later selections have
to allow for. :ref:`tutorial_selecting_and_finishing` covers both.

**********************************
Hollow a part, and cut it open
**********************************

.. image:: /how_to/assets/build_part/part_hollow.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [hollow]
            :end-before: [hollow]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [hollow_algebra]
            :end-before: [hollow_algebra]

:func:`~operations_generic.offset` with a negative ``amount`` moves
every face inward and leaves a shell of that thickness. ``openings``
names the faces to leave open, here the top.

:func:`~operations_generic.split` cuts a part with a plane and keeps one
side, which is a quick way to look inside while designing. It keeps the
side the plane faces; ``keep=Keep.BOTTOM`` keeps the other and
``Keep.BOTH`` both.

**************************************
Control what an operation works on
**************************************

In builder mode sketches and lines made inside a part are not added to
it. They wait there as *pending* objects, and the next operation that
needs them takes them.

.. image:: /how_to/assets/build_part/part_pending.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [pending]
            :end-before: [pending]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [pending_algebra]
            :end-before: [pending_algebra]

``loft`` is given nothing in the builder version. It takes the two
pending sketches, in the order they were made, and they are then used
up, so a later operation will not find them again. ``extrude`` takes
pending sketches the same way, and ``sweep`` a pending sketch and a
pending line.

This saves typing, and it carries information: a pending sketch
remembers the plane it was made on, which gives ``extrude`` its
direction.

The same operations accept their input explicitly, as they must in
algebra mode. To do that in a builder, keep the sketches out of the
pending list with ``mode=Mode.PRIVATE`` and pass them yourself:

.. literalinclude:: /how_to/build_part.py
    :language: build123d
    :start-after: [pending_explicit]
    :end-before: [pending_explicit]

A private sketch is also the way to make a drawing inside a part that is
only to be measured from or wrapped, and never extruded.

The :ref:`tea cup <tea_cup>` example relies on pending objects
throughout: its handle is a sketch and a line, both pending, taken by a
``sweep()`` with no arguments.

.. image:: /how_to/assets/build_part/tea_cup.png
    :align: center
    :width: 50%

*************************************
Use one part as a tool on another
*************************************

.. image:: /how_to/assets/build_part/part_tool.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [tool]
            :end-before: [tool]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [tool_algebra]
            :end-before: [tool_algebra]

A finished part can be used on another like any solid. In builder mode
:func:`~operations_generic.insert` brings an existing shape into the
part being built, with a ``mode`` like any object, at the current place.
In algebra mode it is ordinary subtraction of a moved copy. The plug
itself is not changed by either.

In builder mode the tool can also be built in place, as a ``BuildPart``
inside the ``BuildPart`` it works on:

.. literalinclude:: /how_to/build_part.py
    :language: build123d
    :start-after: [tool_nested]
    :end-before: [tool_nested]

A builder has a ``mode`` like any object. When the inner builder ends,
what it built is combined with the part of the builder round it, here by
being cut out. Everything inside the inner block is built on its own
first, so the cone is a whole solid before any cutting happens, however
many objects and operations it takes to make.

The inner builder is given its place, ``Pos(0, 0, 4)``, as an argument,
and builds at its own origin; a ``with Locations(...)`` block round it
does the same. Afterwards ``plug.part`` is the tool where it was placed
and ``plug.part_local`` the tool as it was built.

Use a nested builder when the tool is only for this part, and a separate
one with ``insert`` when it is a part in its own right or is used more
than once.

***********************************
Measure a part or get its faces
***********************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [pieces]
            :end-before: [pieces]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_part.py
            :language: build123d
            :start-after: [pieces_algebra]
            :end-before: [pieces_algebra]

A part can be asked for its ``faces()``, ``edges()`` and ``vertices()``,
as lists that can be sorted, grouped and filtered, and for its
``volume``, ``area`` and bounding box. In builder mode the selectors are
on the builder and the measurements on ``block.part``.

***********************
Work in other units
***********************

Lengths in build123d are plain numbers and carry no unit. Exports to
formats such as STEP and STL treat them as millimetres. To write a
dimension in another unit, multiply by its constant:

.. literalinclude:: /how_to/build_part.py
    :language: build123d
    :start-after: [units]
    :end-before: [units]

These are defined:

.. code-block:: build123d

    MM = 1
    CM = 10 * MM
    M = 1000 * MM
    IN = 25.4 * MM
    FT = 12 * IN
    THOU = IN / 1000

Writing ``* MM`` after a dimension changes nothing and says what the
number means. Some export formats, DXF among them, can be told which
unit to declare; see the import and export guide.

************
See also
************

* :ref:`tutorial_sketch_then_extrude`, :ref:`tutorial_beyond_extrude`
  and :ref:`tutorial_selecting_and_finishing` build parts step by step.
* :ref:`sketching` and :ref:`placing_sketches` cover the sketches parts
  are made from.
* :ref:`moving_objects` covers placing and turning solids.
* :class:`~build_part.BuildPart` in the reference lists the members of
  the builder itself.
