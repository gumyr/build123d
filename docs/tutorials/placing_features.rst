.. _tutorial_placing_features:

################
Placing features
################

So far almost everything has been drawn at the origin. A real part has the
same feature in many places - a hole in each corner, vents in a ring, the
same cut-out for every fan - and typing a coordinate for each one soon gets
out of hand. In this tutorial you will lay out this panel for two cooling
fans by describing *patterns* of places instead:

.. image:: /tutorials/assets/placing_features/panel_extrude.svg
    :align: center
    :width: 70%

Along the way you will:

* create a feature at each place in a list,
* describe a grid or a ring of places and let build123d work out the points,
* use the direction a place faces, as well as its position,
* put one pattern inside another, and
* stand a whole sketch, places and all, on a different plane.

It takes about twenty minutes and follows on from
:ref:`tutorial_sketch_then_extrude`, which introduces sketches, ``extrude``,
and how the builder and algebra tabs on this page work.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the panel, in
millimetres. The first two lines describe the panel itself, the third its
mounting holes, and the last three the fans and the vents in front of them.

.. literalinclude:: /tutorials/placing_features.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

****************************
Step 2: A list of places
****************************

The panel is a rounded rectangle with a mounting hole in each corner.
:class:`~build_common.Locations` holds a list of places, and whatever is
created at a ``Locations`` is created once at each place in it - here, four
circles subtracted from the outline.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [places_builder]
            :end-before: [places_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [places_algebra]
            :end-before: [places_algebra]

.. image:: /tutorials/assets/placing_features/panel_places.svg
    :align: center
    :width: 60%

``Locations`` is the same object in both modes. In builder mode it is a
``with`` block, and everything created inside the block is created at each
of its places. In algebra mode the ``*`` operator places a shape at each of
them.

This works, and it has the weakness that the typed corners had in
:ref:`tutorial_drawing_outlines`. The numbers 77 and 42 are half the size of
the panel less a margin, worked out by hand and typed four times. Resize the
panel and the holes stay where they were.

****************************
Step 3: A grid of places
****************************

Four holes at the corners of a rectangle are a two by two grid.
:class:`~build_common.GridLocations` describes a grid by the spacing between
its places in X and in Y and the number of places each way, and centres it
on the origin.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [grid_builder]
            :end-before: [grid_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [grid_algebra]
            :end-before: [grid_algebra]

These are exactly the four holes of step 2, and the picture is unchanged.
But the spacing is now computed from ``panel_width``, ``panel_height`` and
``inset``, so the holes follow the panel. You have said what the pattern
*is*, and left the points to build123d.

*********************************
Step 4: Places round a circle
*********************************

A fan needs vents in front of it.
:class:`~build_common.PolarLocations` spaces a number of places evenly round
a circle of a given radius. For now there is one fan, at the centre of the
panel, with a slot at each place.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [polar_builder]
            :end-before: [polar_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [polar_algebra]
            :end-before: [polar_algebra]

.. image:: /tutorials/assets/placing_features/panel_polar.svg
    :align: center
    :width: 60%

Look at which way the slots point. A
:class:`~objects_sketch.SlotOverall` is drawn lying along the X axis, yet
every one of these lies along its own spoke of the ring. That is because a
place is more than a point: it also has a *direction*. Each place in a
``PolarLocations`` faces outwards from the centre, and a shape created there
is turned to match. The places in ``Locations`` and ``GridLocations`` all
face the same way, which is why the question did not come up before.

If you want the positions without the turning, ``PolarLocations`` takes
``rotate=False``, and all ten slots would then lie along X.

***********************************
Step 5: A place has a direction
***********************************

The air leaving a fan is spinning, and vents that lean with the spin let it
through more easily. In :ref:`tutorial_sketch_then_extrude` a slot was
turned with ``rotation=90``. The same parameter leans these, by
``vent_lean`` degrees:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [lean_builder]
            :end-before: [lean_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [lean_algebra]
            :end-before: [lean_algebra]

.. image:: /tutorials/assets/placing_features/panel_lean.svg
    :align: center
    :width: 60%

Every slot has turned by the same 30 degrees, but each from a different
starting direction: its own spoke. A shape's ``rotation`` is measured from
the direction of the place it is created at, not from the X axis of the
sketch. This is the rule that makes patterns useful. Describe a feature
once, as it should look at one place, and it comes out right at all of
them.

********************************
Step 6: Places within places
********************************

The panel holds two fans, side by side, and each needs the same vents and
its own four screw holes. Nothing about a fan has to be described twice.
Its vents and its screw holes are patterns *around the fan's centre*, and
the two centres are themselves a list of places.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [nested_builder]
            :end-before: [nested_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [nested_algebra]
            :end-before: [nested_algebra]

.. image:: /tutorials/assets/placing_features/panel_nested.svg
    :align: center
    :width: 60%

Compare this with step 5. The line that makes the vents has not changed; it
has only moved inside a ``Locations`` holding the two fan centres, and the
whole ring is now made at each. The screw holes are a second pattern, a
grid, placed at the same two centres.

In builder mode one location block goes inside another, and the inner
pattern is made at every place of the outer one. In algebra mode ``*`` does
the same between two sets of places - ``fans * PolarLocations(...)`` is the
ring at each fan - and then places the shape at every one of the results.

Try a ``vent_count`` of 14 or a ``fan_spacing`` of 90 at the top of the
file. Both fans change together, because there is only one description of a
fan.

**********************
Step 7: Extrude it
**********************

Every feature is in the sketch, so one ``extrude`` finishes the panel.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [extrude_builder]
            :end-before: [extrude_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

.. image:: /tutorials/assets/placing_features/panel_extrude.svg
    :align: center
    :width: 70%

**************************************
Step 8: The sketch has a place too
**************************************

Every place so far has been measured in the flat of the sketch, from its
centre. The sketch itself is somewhere as well. Until now that has been
``Plane.XY``, the plane of the floor, which is where a sketch goes when you
do not say. A fan panel stands upright, so put the sketch on ``Plane.XZ``,
the plane of the front wall.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [plane_builder]
            :end-before: [plane_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/placing_features.py
            :language: build123d
            :start-after: [plane_algebra]
            :end-before: [plane_algebra]

.. image:: /tutorials/assets/placing_features/panel_plane.svg
    :align: center
    :width: 70%

That is the only change, and none of the places inside the sketch were
touched. Their coordinates are positions *in the sketch*, across it and up
it, so when the sketch stands up they stand up with it. ``extrude`` follows
too: it always pushes straight out of the face of the sketch.

In builder mode the plane is given to ``BuildSketch``. In algebra mode the
finished sketch is placed on the plane with the same ``*`` that placed a
circle at a list of points.

********************
What you learned
********************

* A **place** has a position and a direction. A shape created there is
  moved to the position and turned to the direction, and its own
  ``rotation`` is measured from that direction.
* :class:`~build_common.Locations` is a list of places you name one by one;
  :class:`~build_common.GridLocations` and
  :class:`~build_common.PolarLocations` work a pattern out from a
  description of it. ``HexLocations`` does the same for a honeycomb.
* The same three objects are used in both modes: as ``with`` blocks in
  builder mode and with ``*`` in algebra mode.
* Patterns **nest**. Describe a feature once, around its own centre, and
  place the whole of it wherever it is needed.
* Places are measured in the sketch, and the sketch sits on a **plane**, so
  a finished layout can be stood anywhere without changing it.

The places in this tutorial were all worked out from dimensions. The next
step is to take them from the part itself - the top face, that corner, the
longest edge - which is the subject of the next tutorial.
