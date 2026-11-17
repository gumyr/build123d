.. _centers:

#######################
The centre of a shape
#######################

"Put it at the centre" sounds like one instruction. For anything less
regular than a box or a circle it is three, because a shape has more than
one centre, and they can be far apart. build123d lets the designer say which
is meant with :class:`~build_enums.CenterOf`, and uses a particular one
itself in each place where it needs a centre. This page describes the three,
says which shapes have which, and lists which one the library uses where.

*****************
Three centres
*****************

``CenterOf.BOUNDING_BOX``
    The middle of the smallest box, square to the axes, that holds the
    shape. It depends only on the shape's extent, so it is easy to predict,
    and it changes if the shape is turned.

``CenterOf.MASS``
    The balance point: the centre of gravity of a solid of even density, or
    the centroid of a face or a curve. It does not change if the shape is
    turned.

``CenterOf.GEOMETRY``
    The middle of the shape measured along the shape itself: the point
    halfway along a curve, or the middle of a surface. It is the only one of
    the three that is always *on* a curve or a curved face.

A curve shows all three apart:

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [curve]
    :end-before: [curve]

.. image:: /explanation/assets/center/one_d_center.svg
    :align: center
    :width: 50%

The bounding box is dashed, and of the three marks only the triangle, the
point halfway along, is on the arc.

A flat face has only two, because its ``GEOMETRY`` centre is defined to be its
centre of mass:

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [face]
    :end-before: [face]

.. image:: /explanation/assets/center/center.svg
    :align: center
    :width: 50%

Here the centre of the bounding box is not on the face at all. That is the
usual surprise: for an angle, a ring, a C shape or a hook, the middle of the
box is in the empty part.

****************************
Which shapes have which
****************************

``shape.center()`` takes the centre wanted and has a default, and both
depend on the kind of shape.

.. list-table::
    :header-rows: 1
    :widths: 34 16 16 17 17

    * - Shape
      - Default
      - ``BOUNDING_BOX``
      - ``GEOMETRY``
      - ``MASS``
    * - ``Edge``, ``Wire`` and the line objects
      - ``GEOMETRY``
      - ✓
      - ✓
      - ✓
    * - ``Face``
      - ``GEOMETRY``
      - ✓
      - ✓
      - ✓
    * - ``Sketch``, ``Part``, ``Curve``, ``Solid``, ``Compound``
      - ``MASS``
      - ✓
      - raises ``ValueError``
      - ✓
    * - ``Vertex``, ``Shell``
      - one centre; ``center()`` takes no option
      -
      -
      -

Two consequences are worth knowing.

**A sketch is not a face.** ``Rectangle`` and the other sketch objects are
``Sketch`` objects, which may hold several faces, so there is no single
surface to take the middle of. Ask the face:

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [geometry_error]
    :end-before: [geometry_error]

**The default changes with the class.** The same piece of geometry gives a
different answer as a ``Face`` and as a ``Sketch``:

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [defaults]
    :end-before: [defaults]

For flat faces the two defaults are the same point, so the difference shows
only on curved ones.

********************************
``GEOMETRY`` on a curved face
********************************

For a face that is not flat, ``GEOMETRY`` is the middle of the surface, the
point at ``face.position_at(0.5, 0.5)``, and so it is on the face. The centre
of mass of a curved face generally is not: it is somewhere in the hollow.

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [curved]
    :end-before: [curved]

``wall`` is a quarter of the side of a cylinder. Use ``GEOMETRY`` for a point
to work from on the surface, such as the place to start a hole or put a
label, and ``MASS`` for the balance point.

************************************
Which centre the library uses
************************************

Several features need a centre and choose one for themselves.

``align``
    Uses the bounding box. ``Align.CENTER`` puts the middle of the
    bounding box on the origin, ``Align.MIN`` and ``Align.MAX`` its sides.
    So an object made with the default alignment is centred on its box, and
    its centre of mass may be elsewhere:

    .. literalinclude:: /explanation/center.py
        :language: build123d
        :start-after: [align]
        :end-before: [align]

Sorting and grouping
    ``sort_by``, ``group_by`` and ``filter_by_position`` measure each shape
    at its default centre: edges and faces at ``GEOMETRY``, solids at
    ``MASS``. Sorting the faces of the cone along Z puts the flat base, at
    ``-5``, before the sloping side, whose middle is at ``0``.

Planes and places taken from a face
    ``Plane(face)`` has its origin at the face's default centre, and
    ``Locations(face)`` is a place there.

    .. literalinclude:: /explanation/center.py
        :language: build123d
        :start-after: [plane]
        :end-before: [plane]

    ``face.center_location`` is a different point, because it is always the
    middle of the surface, ``position_at(0.5, 0.5)``, with the surface normal
    there as its z. On a flat face that is not symmetrical it need not be the
    centre of mass, or on the face: for the angle above it is ``(5, 5, 0)``.

***************************
What a centre is not
***************************

**It is not the shape's position.** ``shape.position`` is where the shape's
location is, the origin it was made about, whereas a centre is where the
material is.

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [position]
    :end-before: [position]

**It is not the centre of an arc's circle.** The three centres of an arc are
all near the arc, whereas the point it is drawn about is
:attr:`~topology.Edge.arc_center`.

.. literalinclude:: /explanation/center.py
    :language: build123d
    :start-after: [arc_center]
    :end-before: [arc_center]

************
See also
************

* :ref:`selectors` for sorting and grouping by position.
* :ref:`placing_sketches` for planes taken from faces.
* :ref:`moving_objects` for ``align`` and placement.
