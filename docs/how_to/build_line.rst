.. _drawing_lines_and_curves:

#########################
Drawing lines and curves
#########################

Lines and curves are the one-dimensional objects of build123d: they have
length and no area. They are drawn for two reasons above all. Joined into
a closed outline they become the edge of a face, for shapes that no
rectangle or circle will make. Left open they are a path, for a sweep to
follow. This guide shows how to draw them for either job.

In builder mode lines are drawn inside a ``BuildLine``, which collects
them. In algebra mode each is an object in its own right and they are
joined with ``+``. The lines themselves are written the same way in both.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - draw connected lines and arcs
      - each one started at ``previous @ 1``
    * - pick the right object
      - the table under "Choose the object"
    * - draw half an outline and reflect it
      - ``mirror``
    * - close an outline into a face
      - ``make_face``, ``make_hull``
    * - draw a path for a sweep
      - a line, and a sketch at ``path ^ 0``
    * - draw on another plane, or in space
      - ``BuildLine(plane)``, ``plane *``, 3D points
    * - round or bevel corners
      - ``fillet``, ``chamfer``, ``FilletPolyline``
    * - draw lines to build from, not to keep
      - ``mode=Mode.PRIVATE``
    * - start from an SVG file
      - ``import_svg_as_buildline_code``
    * - get the edges, corners or length back
      - ``edges()``, ``vertices()``, ``wire()``

In the pictures the object under discussion is drawn in blue and
construction lines dashed.

*********************************
Draw connected lines and arcs
*********************************

.. image:: /how_to/assets/build_line/lines_connect.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [connect]
            :end-before: [connect]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [connect_algebra]
            :end-before: [connect_algebra]

Each object is given a name, and each after the first starts where the
one before it ended: ``l1 @ 1`` is the point at the end of ``l1``. The
last one ends at ``l1 @ 0``, where the first began, which closes the
outline. Nothing is typed twice, so the pieces cannot drift apart.
:ref:`drawing_with_constraints` covers ``@`` and the other ways of tying
one object to another.

What comes out differs between the modes:

* In builder mode the ``BuildLine`` holds the result, as ``outline.line``.
* In algebra mode ``+`` joins the objects into one shape: a ``Wire`` when
  they connect end to end, as here, and a ``Curve`` when they do not.

*********************
Choose the object
*********************

There are many line and arc objects, and they differ mostly in what they
ask for. Pick the one that asks for what you already know.

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - You know
      - Use
    * - both ends
      - :class:`~objects_curve.Line`
    * - a string of corner points
      - :class:`~objects_curve.Polyline`, with ``close=True`` to return
        to the start
    * - a start, a length and an angle or direction
      - :class:`~objects_curve.PolarLine`
    * - an arc's centre, radius and angles
      - :class:`~objects_curve.CenterArc`
    * - an arc's ends and a point between them
      - :class:`~objects_curve.ThreePointArc`
    * - an arc's ends and its radius
      - :class:`~objects_curve.RadiusArc`
    * - an arc's ends and how far it bulges
      - :class:`~objects_curve.SagittaArc`
    * - an arc's ends and the direction it starts in
      - :class:`~objects_curve.TangentArc`
    * - an arc's start, starting direction, radius and angle
      - :class:`~objects_curve.JernArc`
    * - points a smooth curve must pass through
      - :class:`~objects_curve.Spline`
    * - control points that pull a curve toward them
      - :class:`~objects_curve.Bezier`
    * - a coil: pitch, height and radius
      - :class:`~objects_curve.Helix`

A ``RadiusArc`` bulges to one side of the line between its ends with a
positive radius and to the other with a negative one. The complete list,
with a picture of each, is in the :doc:`Objects reference </reference/objects>`.

***************************
Draw half and mirror it
***************************

A symmetric outline need only be drawn once.

.. image:: /how_to/assets/build_line/lines_mirror.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [mirror]
            :end-before: [mirror]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [mirror_algebra]
            :end-before: [mirror_algebra]

:func:`~operations_generic.mirror` reflects the lines in a plane, here
``Plane.YZ``, the plane that stands on the Y axis. In builder mode it
reflects everything drawn so far and adds the reflection. In algebra mode
it is given the half and returns the other, and the two are added.

Draw the half so that it starts and ends on the mirror plane, as this one
does at ``X = 0``, and the two halves meet to make a closed outline.

.. note::

    In algebra mode ``+`` also joins pieces that run on smoothly from one
    into the next. The two halves of the flat base become one line, and
    the two halves of the top lobe one curve, so this outline has eight
    edges where the builder keeps ten. The shape is the same.

********************************
Close an outline into a face
********************************

A closed outline is still only lines. :func:`~operations_sketch.make_face`
fills it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [face]
            :end-before: [face]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [face_algebra]
            :end-before: [face_algebra]

In builder mode the ``BuildLine`` is written inside a ``BuildSketch``.
When it ends, its lines are handed to the sketch, and ``make_face`` turns
the lines waiting there into a face. In algebra mode ``make_face`` is
given the outline and returns the face as a sketch. Either way the result
is a sketch like any other, ready to ``extrude``.

The outline must be closed. :func:`~operations_sketch.make_hull` does not
need one: it makes the face that a band stretched round the lines would
enclose, whether or not they touch.

.. image:: /how_to/assets/build_line/lines_hull.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [hull]
            :end-before: [hull]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [hull_algebra]
            :end-before: [hull_algebra]

***************************
Draw a path for a sweep
***************************

.. image:: /how_to/assets/build_line/lines_path.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [path]
            :end-before: [path]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [path_algebra]
            :end-before: [path_algebra]

A path is drawn like an outline and left open. The spline is given
``tangents`` so that it sets off in the direction the arc ends in,
``l1 % 1``, and arrives heading down, and the three pieces make one
smooth path.

The profile has to stand across the start of the path, and ``path ^ 0``
is the place for it: a location at the start of the path, facing along
it. In builder mode the path and the sketch are both made inside the
``BuildPart``, which passes them to ``sweep``. In algebra mode ``sweep``
is given the two. :ref:`placing_sketches` has more on ``^``.

**************************************
Draw on another plane, or in space
**************************************

Lines are drawn in X and Y, and like a sketch they can be put on any
plane afterwards.

.. image:: /how_to/assets/build_line/lines_plane.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [plane]
            :end-before: [plane]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [plane_algebra]
            :end-before: [plane_algebra]

The grey line is what was drawn and the blue one is where it ends up,
standing in ``Plane.YZ``. The plane can also be a face of a part or a
location.

In builder mode the points given to the objects are always in the
builder's own flat coordinates, never in the plane's, and the plane is
applied once, to the finished line. Both versions are kept:
``upright.line`` is the line on its plane and ``upright.line_local`` is
the line as it was drawn. A ``BuildLine`` takes one plane, where a
``BuildSketch`` can take several.

Lines need not be flat at all. Points can be given with three
coordinates:

.. image:: /how_to/assets/build_line/lines_space.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [space]
            :end-before: [space]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [space_algebra]
            :end-before: [space_algebra]

The polyline leaves the XY plane at its second corner and the spline
carries on from it, rising. A path like this suits a sweep; it cannot be
made into a face, which needs a flat outline.

******************************
Round or bevel the corners
******************************

.. image:: /how_to/assets/build_line/lines_corners.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [corners]
            :end-before: [corners]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [corners_algebra]
            :end-before: [corners_algebra]

:func:`~operations_generic.fillet` rounds the corners it is given, which
for a line are vertices. ``group_by(Axis.Y)[0]`` picks the two lowest.
:func:`~operations_generic.chamfer` bevels them the same way, with a
``length`` in place of a ``radius``. In builder mode the line being drawn
is changed; in algebra mode the changed line is returned.

When every corner of a polyline is to be rounded alike, or each by its
own radius, :class:`~objects_curve.FilletPolyline` does it as the line is
made:

.. literalinclude:: /how_to/build_line.py
    :language: build123d
    :start-after: [corners_polyline]
    :end-before: [corners_polyline]

**************************
Use construction lines
**************************

Some lines are drawn only to build from: a centre line, an axis of
symmetry, a circle that other lines must reach. They belong in the
drawing and not in the result.

.. image:: /how_to/assets/build_line/lines_construction.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [construction]
            :end-before: [construction]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [construction_algebra]
            :end-before: [construction_algebra]

``guide`` is the centre line of this slot. Every point of the outline is
taken from it: ``guide @ 0`` and ``guide @ 1`` for its ends, ``guide % 0``
for its direction, and ``across``, that direction turned a quarter turn
and made 6 long, for half the width. Change the guide's length or angle
and the slot follows.

In builder mode ``mode=Mode.PRIVATE`` makes an object without adding it
to the line being built, so the guide can be used and is left out of the
result. In algebra mode nothing is added until you add it, so the guide
is simply left out of the sum.

When only part of a construction line is wanted in the result, cut that
part out with ``trim`` and add it; :ref:`drawing_with_constraints` shows
this with an ellipse.

**************************
Start from an SVG file
**************************

An outline that already exists as an SVG drawing can be turned into
build123d code, not just imported as fixed geometry:

.. code-block:: build123d

    svg_code, builder_name = import_svg_as_buildline_code("club.svg")

:func:`~importers.import_svg_as_buildline_code` returns the source of a
``BuildLine`` that draws the paths of the file, and the name it gave the
builder. The club outline above began this way. Paste the code into a
script and it can be edited like any other: given constraints, mirrored,
or made parametric.

***********************
Get the pieces back
***********************

A finished line can be asked for its parts, in the same way as any other
shape.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [pieces]
            :end-before: [pieces]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/build_line.py
            :language: build123d
            :start-after: [pieces_algebra]
            :end-before: [pieces_algebra]

``edges()`` and ``vertices()`` give lists that can be sorted, grouped and
filtered; :ref:`selectors` covers how. ``wire()`` gives the whole line as
one ``Wire``, which has a ``length`` and can be asked for points and
directions along all of it with ``@`` and ``%``.

************
See also
************

* :ref:`tutorial_drawing_outlines` builds an outline and a sweep path
  step by step.
* :ref:`drawing_with_constraints` covers tying lines and arcs to one
  another.
* :ref:`placing_sketches` covers the planes a sketch, and so a line, can
  be put on.
* :class:`~build_line.BuildLine` in the reference lists the members of the
  builder itself.
