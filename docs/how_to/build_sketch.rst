.. _sketching:

#########
Sketching
#########

A sketch is a flat shape with area: one or more faces, all in one plane.
It is the usual starting point for a part, the profile that
:func:`~operations_part.extrude`, :func:`~operations_part.revolve` and the
other part operations turn into a solid. This guide shows how to make the
sketch you want.

Sketch objects are filled shapes, not outlines, which is what lets them be
combined: one added to another, cut out of it, or used to trim it.

In builder mode a sketch is made inside a ``BuildSketch``, which combines
the objects created in it. In algebra mode the objects are combined with
``+``, ``-`` and ``&``.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - add, cut or trim with shapes
      - ``mode=``, or ``+``, ``-``, ``&``
    * - pick the right object
      - the table under "Choose the object"
    * - put a feature where it belongs
      - ``Locations``, ``Pos``, ``align=``, ``rotation=``
    * - make a shape no object makes
      - lines and ``make_face``
    * - round or bevel corners
      - ``fillet``, ``chamfer``
    * - grow, shrink or make a frame
      - ``offset``
    * - draw half and reflect it
      - ``mirror``
    * - add lettering
      - ``Text``
    * - use a shape to build from, not to keep
      - ``mode=Mode.PRIVATE``
    * - start from a face of the part
      - ``insert(face)``, or the face itself
    * - put the sketch somewhere else
      - see :ref:`placing_sketches`
    * - get the edges, corners or area back
      - ``edges()``, ``vertices()``, ``area``

*********************************
Add, cut and trim with shapes
*********************************

.. image:: /how_to/assets/build_sketch/sketch_combine.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [combine]
            :end-before: [combine]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [combine_algebra]
            :end-before: [combine_algebra]

The first object starts the sketch and each later one is combined with
what is there. In builder mode every object has a ``mode``:

* ``Mode.ADD``, the default, joins the object to the sketch;
* ``Mode.SUBTRACT`` cuts it out;
* ``Mode.INTERSECT`` keeps only what the sketch and the object have in
  common, shown here by the large circle that trims the corners.

In algebra mode the three are the operators ``+``, ``-`` and ``&``.

The result is ``plate.sketch`` in builder mode, while in algebra mode
``plate`` is itself the sketch.

*********************
Choose the object
*********************

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - For
      - Use
    * - a rectangle
      - :class:`~objects_sketch.Rectangle`, or
        :class:`~objects_sketch.RectangleRounded` with rounded corners
    * - a circle or an ellipse
      - :class:`~objects_sketch.Circle`, :class:`~objects_sketch.Ellipse`
    * - a polygon with equal sides
      - :class:`~objects_sketch.RegularPolygon`
    * - a polygon from its corner points
      - :class:`~objects_sketch.Polygon`
    * - a four-sided shape with sloping sides
      - :class:`~objects_sketch.Trapezoid`
    * - a triangle from sides and angles
      - :class:`~objects_sketch.Triangle`
    * - a slot from its overall length
      - :class:`~objects_sketch.SlotOverall`
    * - a slot from the distance between its centres
      - :class:`~objects_sketch.SlotCenterToCenter`
    * - a slot that follows an arc
      - :class:`~objects_sketch.SlotArc`
    * - lettering
      - :class:`~objects_sketch.Text`

The complete list, with a picture of each, is in the
:doc:`Objects reference </reference/objects>`.

**********************************
Put a feature where it belongs
**********************************

.. image:: /how_to/assets/build_sketch/sketch_position.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [position]
            :end-before: [position]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [position_algebra]
            :end-before: [position_algebra]

Three things decide where an object lands.

**align** says which part of the object sits on its place. Objects are
centred by default; ``align=Align.MIN`` puts the lower-left corner there
instead, so this panel has a corner at the origin and its features can
be measured from that corner. Each direction can be set on its own:
``align=(Align.MIN, Align.CENTER)``.

**The place** is the origin unless another is given: a ``with
Locations(...)`` block in builder mode, ``Pos(x, y) *`` in algebra mode.
Places nest, so the grid of four holes here is centred on ``(40, 25)``.
:class:`~build_common.GridLocations`,
:class:`~build_common.PolarLocations` and
:class:`~build_common.HexLocations` lay out patterns, and
:ref:`tutorial_placing_features` goes through them.

**rotation** turns the object about its own place, in degrees.

********************************
Make a shape no object makes
********************************

.. image:: /how_to/assets/build_sketch/sketch_outline.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [outline]
            :end-before: [outline]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [outline_algebra]
            :end-before: [outline_algebra]

Draw the outline with lines and arcs and
:func:`~operations_sketch.make_face` fills it. In builder mode the
``BuildLine`` is written inside the sketch, and ``make_face`` turns the
lines it leaves there into a face. In algebra mode ``make_face`` is given
the lines.

The face is then a shape like any other, and the hole is cut from it in
the usual way. :ref:`drawing_lines_and_curves` covers drawing the
outline.

******************************
Round or bevel the corners
******************************

.. image:: /how_to/assets/build_sketch/sketch_corners.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [corners]
            :end-before: [corners]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [corners_algebra]
            :end-before: [corners_algebra]

The corners of a sketch are its vertices.
:func:`~operations_generic.fillet` rounds the ones it is given and
:func:`~operations_generic.chamfer` bevels them. Here
``group_by(Axis.X)[-1]`` is the two corners furthest to the right and
``[0]`` the two furthest to the left; :ref:`selectors` covers choosing
them. In builder mode the sketch is changed; in algebra mode the changed
sketch is returned.

********************************
Grow, shrink or make a frame
********************************

.. image:: /how_to/assets/build_sketch/sketch_offset.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [offset]
            :end-before: [offset]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [offset_algebra]
            :end-before: [offset_algebra]

:func:`~operations_generic.offset` moves the whole edge of a sketch
outward by a positive ``amount`` and inward by a negative one, keeping
its shape. On its own it grows or shrinks the sketch.

To make a frame, shrink the shape and cut the result out of the
original, which leaves a band the width of the offset. In builder mode
that is one line, ``offset`` with ``mode=Mode.SUBTRACT``. In algebra mode
the original is kept in a variable and the offset is subtracted from it.

***************************
Draw half and mirror it
***************************

.. image:: /how_to/assets/build_sketch/sketch_mirror.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [mirror]
            :end-before: [mirror]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [mirror_algebra]
            :end-before: [mirror_algebra]

:func:`~operations_generic.mirror` reflects a sketch in a plane, here
``Plane.YZ``, drawn dashed. In builder mode it reflects what the sketch
holds so far and adds the reflection. In algebra mode it returns the
reflection, to be added. Where the two halves touch they become one face.

*****************
Add lettering
*****************

.. image:: /how_to/assets/build_sketch/sketch_text.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [text]
            :end-before: [text]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [text_algebra]
            :end-before: [text_algebra]

:class:`~objects_sketch.Text` makes a sketch of the given text at the
given size, one face for each separate piece of each character. It
combines like any other object: added, it is raised lettering once
extruded; subtracted, as here, it is cut through.

Text can also follow a path, and the font matters when the letters are
to become solid geometry; :ref:`tutorial_bicycle_tire` covers both.

*****************************
Use construction geometry
*****************************

Some shapes are wanted only for what can be measured from them.

.. image:: /how_to/assets/build_sketch/sketch_construction.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [construction]
            :end-before: [construction]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [construction_algebra]
            :end-before: [construction_algebra]

The hexagon is never part of the flange: it is there only for its six
corners, which are where the holes go.

In builder mode ``mode=Mode.PRIVATE`` makes an object without adding it
to the sketch. In algebra mode nothing is combined until you combine it,
so the hexagon is simply never added.

*********************************
Start from a face of the part
*********************************

A face of a part is already a flat shape, and can be the start of a
sketch.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [from_face]
            :end-before: [from_face]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [from_face_algebra]
            :end-before: [from_face_algebra]

The top of the box is taken, shrunk by 4 all round, and cut 6 deep into
the box, which leaves a tray with a wall 4 thick. Because the recess is
made from the face, it follows the box when its size changes.

In builder mode the sketch is placed on the face, and
:func:`~operations_generic.insert` brings the face into it. A face
inserted into a sketch is laid flat in the sketch's own coordinates
first, like everything else drawn there. In algebra mode the face is
used where it is: ``offset`` is given the face and returns a sketch in
the same place.

To bring the outline or the silhouette of a whole part into a sketch,
see :ref:`projection_plane`.

.. _sketching_on_other_planes:

**************************
Where a sketch ends up
**************************

A sketch is always drawn flat, in its own X and Y, and is then carried
to wherever it belongs, like a sticker drawn on a table and stuck on the
part. ``BuildSketch`` is given the plane, face or location to put it on,
or several of them; in algebra mode the sketch is multiplied by one.
:ref:`placing_sketches` covers choosing it.

In builder mode both versions are kept, and places given outside the
sketch are applied to the finished sketch in the same way:

.. literalinclude:: /how_to/build_sketch.py
    :language: build123d
    :start-after: [local]
    :end-before: [local]

``sketch_local`` is the sketch as it was drawn, while ``sketch`` is the
sketch where it was put, which is what an enclosing ``BuildPart`` receives.

***********************
Get the pieces back
***********************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [pieces]
            :end-before: [pieces]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_sketch.py
            :language: build123d
            :start-after: [pieces_algebra]
            :end-before: [pieces_algebra]

A sketch can be asked for its ``faces()``, ``edges()`` and
``vertices()``, as lists that can be sorted, grouped and filtered, and
for its ``area``. In builder mode the selectors are on the builder and
the measurements on ``plate.sketch``.

************
See also
************

* :ref:`tutorial_sketch_then_extrude` builds a part from a sketch step by
  step.
* :ref:`placing_sketches` covers the planes a sketch can be put on.
* :ref:`drawing_lines_and_curves` covers the outlines that ``make_face``
  fills.
* :class:`~build_sketch.BuildSketch` in the reference lists the members
  of the builder itself.
