.. _tutorial_spiral_ramp:

#############
A spiral ramp
#############

A channel that climbs round a spiral, a marble run or a cable tray, is a
shape carried along a curve, which is what ``sweep`` is for. Two things make
it harder than it sounds. The channel has to stay level from side to side
all the way up, or whatever runs along it falls out. And the ramp needs
something to stand on, a support whose height is different at every point
along it.

In this tutorial you will build the ramp and its support without working
out either of those by hand:

.. image:: /tutorials/assets/spiral_ramp/ramp_finished.png
    :align: center
    :width: 60%
    :alt: A channel climbing half a turn of a spiral, standing on a curved wall that follows it

Along the way you will:

* draw the cross-section of the channel as a single line given a thickness
  with ``offset``,
* stand that section at the start of a ``Helix``, facing along it,
* sweep it along the helix so that it stays level,
* cast the underside of the ramp onto the ground with ``project_to_plane``,
  and
* extrude that footprint up until it meets the ramp.

It takes about fifteen minutes. Sweeping along a path is introduced in
:ref:`tutorial_drawing_outlines`, choosing faces in
:ref:`tutorial_selecting_and_finishing`, and casting a part onto a plane in
:ref:`tutorial_projection_chalice`. How the builder and algebra tabs on this
page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the ramp, in
millimetres.

.. literalinclude:: /tutorials/spiral_ramp.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*************************
Step 2: The section
*************************

The cross-section of the channel is a floor with a wall at each side, all
of one thickness. Drawing its outline point by point would take eight
corners. It is easier to draw the three lines that whatever runs in the
channel touches, and then give them a thickness.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [section_builder]
            :end-before: [section_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [section_algebra]
            :end-before: [section_algebra]

.. image:: /tutorials/assets/spiral_ramp/ramp_section.png
    :align: center
    :width: 55%

* ``Polyline`` draws the inside of the channel, in black: down one wall,
  across the floor and up the other. The floor is on the X axis and centred
  on the origin, which matters in the next step.
* :func:`~operations_generic.offset` of an open line, with a ``side``, makes
  a second line ``wall`` away on that side and joins the two at their ends,
  which gives a closed outline. ``Side.RIGHT`` is the right of the line as
  it is drawn, here below and outside it, so the thickness is added away
  from the channel and the inside keeps the size it was given.
* ``make_face`` fills the outline.

The outer corners come out rounded, because every point of the new line is
the same distance from the old one.

*********************
Step 3: The path
*********************

The path is a :class:`~objects_curve.Helix`, given by its ``pitch``, its
height and its radius. The height is the pitch times the number of turns,
so half a turn climbs half the pitch. ``center`` starts it ``lift`` above
the ground, to leave room for the support.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [path_builder]
            :end-before: [path_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [path_algebra]
            :end-before: [path_algebra]

.. image:: /tutorials/assets/spiral_ramp/ramp_path.png
    :align: center
    :width: 55%

A section has to stand across the start of its path, facing along it. In
:ref:`tutorial_drawing_outlines` that was done by picking the plane that
happened to face the right way. A helix sets off in no such convenient
direction: this one climbs at 2.73° as it leaves.

``path.location_at(0)`` answers the question directly. ``Edge.location_at``
gives a position along a line, from 0 at its start to 1 at its end, together
with an orientation there whose Z direction runs along the line. A sketch
placed at that location therefore stands across the line, with its origin
on it:

.. image:: /tutorials/assets/spiral_ramp/ramp_start.png
    :align: center
    :width: 55%

The origin of the section was the middle of the floor, so that is the point
the path passes through, and ``radius`` is the radius of the middle of the
channel.

In builder mode the section is the sketch of step 2 with one change: it is
drawn at the location, ``BuildSketch(path.location_at(0))``. In algebra mode
the flat section is moved there by multiplying it by the location.

*********************
Step 4: The sweep
*********************

:func:`~operations_generic.sweep` carries the section along the path.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [sweep_builder]
            :end-before: [sweep_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [sweep_algebra]
            :end-before: [sweep_algebra]

.. image:: /tutorials/assets/spiral_ramp/ramp_sweep.png
    :align: center
    :width: 55%

In builder mode ``sweep`` takes the sketch and the line that were just
made; in algebra mode both are passed to it.

``is_frenet=True`` is what keeps the channel level. A sweep has to decide
how the section is turned about the path at every point along it, and
there is more than one reasonable answer. Here are the far ends of two
sweeps of this section, seen end on:

.. image:: /tutorials/assets/spiral_ramp/ramp_level.png
    :align: center
    :width: 55%

The grey one is the default. It turns the section as little as it can from
one point to the next, and on a path that curves and climbs at once that
lets the section roll over: half way along, the floor already leans more
than 4° toward the centre of the spiral. The blue one is made with
``is_frenet=True``, which takes the section's orientation from the way the
path itself is curving. A helix always curves toward its axis, so the floor
stays square to the axis the whole way, and level from side to side.

.. note::

    ``is_frenet`` suits a path that keeps curving the same way, as a helix
    does. Where a path straightens, or bends back the other way, the
    direction it is curving in is undefined or reverses, and the section
    can flip there. For such paths leave it off.

***************************
Step 5: The footprint
***************************

The support has to sit exactly under the ramp, so its outline is the
outline of the ramp seen from above. Rather than draw that, cast it:
:func:`~operations_generic.project_to_plane` casts a shape onto a plane
along the plane's normal.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [footprint_builder]
            :end-before: [footprint_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [footprint_algebra]
            :end-before: [footprint_algebra]

.. image:: /tutorials/assets/spiral_ramp/ramp_footprint.png
    :align: center
    :width: 55%

Only one face of the ramp is cast, its flat underside, in red. Casting the
whole ramp would give its full outline, walls and rounded corners included.
The underside alone gives a support exactly as wide as the channel, set in
a little from the edges of the ramp.

Choosing that face takes two selectors:

* ``group_by(Face.area)[-1]`` is the group of largest faces. There are two
  in it, because the floor of the channel and the underside below it are
  the same size.
* ``sort_by(Axis.Z)[0]`` is the lower of the two.

The footprint, in grey, is half a ring lying flat on ``Plane.XY``: the
ground, ``lift`` below the low end of the path.

In builder mode the projection is made inside a new sketch and drawn into
it. In algebra mode it is returned and kept in ``footprint``.

***********************
Step 6: The base
***********************

The footprint now has to rise to meet the ramp, and how far is different
all the way along: 29 mm at the low end and 44 mm at the high end. An
:func:`~operations_part.extrude` with ``until`` stops at a surface instead
of at a distance.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [base_builder]
            :end-before: [base_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/spiral_ramp.py
            :language: build123d
            :start-after: [base_algebra]
            :end-before: [base_algebra]

.. image:: /tutorials/assets/spiral_ramp/ramp_finished.png
    :align: center
    :width: 55%

``Until.NEXT`` stops the extrusion at the first surface it meets, which is
the underside of the ramp, so the top of the base takes the shape of that
surface and climbs with it. This step takes a few seconds to run, as the
extrusion has to be cut by a surface that is not flat.

.. note::

    :class:`~build_enums.Until` has four values, and two of them look the
    other way. ``NEXT`` and ``LAST`` are the first and the last surface met
    *along* the direction of the extrusion. ``PREVIOUS`` and ``FIRST`` are
    the first and the last surface met going *backward* from the sketch.
    The ramp is above the footprint, so only ``NEXT`` and ``LAST`` find it,
    and ``LAST`` would carry the base up through the ramp to its top.

In builder mode ``extrude`` takes the footprint sketch, stops at the part
being built, and adds the base to it. In algebra mode the ramp is named as
the ``target``, the base comes back as a solid of its own, and ``+=`` joins
the two.

The result is one solid. Nowhere in the file is the height of the base
written down, nor its outline: both follow from the ramp. Try a ``pitch``
of 60, a ``lift`` of 10, or a channel 20 wide with a ``lip`` of 5, and the
base follows.

********************
What you learned
********************

* :func:`~operations_generic.offset` of an open line with a ``side`` gives a
  closed outline of even thickness, which is a quick way to draw a section
  of sheet or wall.
* ``Edge.location_at`` gives a place on a line and the orientation to stand
  a sketch across it there, ready for a sweep along that line.
* :func:`~operations_generic.sweep` has to choose how the section turns
  about the path. On a path that keeps curving one way, such as a helix,
  ``is_frenet=True`` holds the section steady.
* :func:`~operations_generic.project_to_plane` casts one face, or a whole
  part, onto a plane, which gives a sketch the exact shape of something
  already built.
* ``group_by`` followed by ``sort_by`` picks one face out of several that
  tie.
* :func:`~operations_part.extrude` with ``until`` stops at a surface of a
  part instead of at a distance, so a support fits whatever it holds up.
