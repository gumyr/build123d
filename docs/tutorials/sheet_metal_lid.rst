.. _tutorial_sheet_metal_lid:

########################
A lid for the enclosure
########################

:ref:`sheet_metal_tutorial` made the base of an enclosure with walls
folded up from a blank. This tutorial makes the lid that goes on it, and a
lid is a different kind of sheet metal part. It is nearly flat, and all of
its features are small folds that make it fit: lips that step up to rest
on the rims of the base, and tabs that reach down inside to hold it in
place.

.. image:: /tutorials/assets/sheet_metal_lid/lid_fitted.svg
    :align: center
    :width: 60%

Those folds use the sheet metal operations the base did not need. Along
the way you will:

* step an edge up or down with ``jog``,
* fold a tab narrower than the edge it comes from,
* cut ``bend_relief`` so that such a tab can be formed,
* trim the corners of a flange with ``miter``,
* fold material the sheet already has with ``bend``, and
* fit one sheet metal part to another and check the fit.

It takes about twenty-five minutes, and it carries on in the file you
ended :ref:`sheet_metal_tutorial` with: every step below is added to the
end of that file. How the builder and algebra tabs on this page work is
described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Add the dimensions of the lid below the base.

.. literalinclude:: /tutorials/sheet_metal_lid.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The lid is the same thickness as the base, bent to a tighter radius,
because its folds are small. Its plate is ``plate_length`` by
``plate_width``, chosen to drop between the walls and the hems of the base
with a little room to spare. The other values are introduced with the step
that uses them.

Each step below shows the whole of the lid's code as it stands at that
point.

*************************
Step 2: The plate
*************************

Start as the base did, with a flat blank in a sheet of its own.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [plate_builder]
            :end-before: [plate_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [plate_algebra]
            :end-before: [plate_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_plate.svg
    :align: center
    :width: 50%

This is a second sheet with its own material, so in builder mode it is a
second ``BuildSheet``, and in algebra mode a second
``SheetMetalParameters``.

*******************************
Step 3: Stepped lips
*******************************

The lid rests on the hemmed rims of the two long walls, but its plate sits
lower, between them, so that it cannot slide sideways. Each long edge
therefore has to step up and then run on level: up over the hem, and out
across the top of it. That shape is a *jog*.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [lips_builder]
            :end-before: [lips_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [lips_algebra]
            :end-before: [lips_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_lips.svg
    :align: center
    :width: 60%

:ref:`jog <sheet_metal_jog>` makes two bends as one feature: up through 90
degrees, a short straight run, and back through 90 degrees, so that what
comes after is parallel to what came before. Given a rim, it adds new
material to it, as ``flange`` does. ``offset`` is the height of the step
and ``length`` is how far the sheet runs on beyond it, which here is the
lip.

``lid.rims().filter_by(Axis.X)`` are the two long edges of the plate. Both
are stepped in one call.

A jog has a least height. Each of its two bends takes up room, so the step
cannot be smaller than the two bend radii together. That is why this sheet
has a small ``lid_bend_radius``: with the 2 mm of the base, a step of 4 mm
could not be made.

**********************
Step 4: Tabs
**********************

The lips stop the lid moving across the box. To stop it moving along the
box, fold a tab down from each end of the plate, to sit just inside the
short walls.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [tabs_builder]
            :end-before: [tabs_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [tabs_algebra]
            :end-before: [tabs_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_tabs.svg
    :align: center
    :width: 60%

The picture, like the next three, is from underneath, where the tabs are.

This is ``flange`` again, used differently in two ways.

``angle=-90`` folds down instead of up. A positive angle folds towards the
side of the sheet its faces look out from, which for the plate is upwards,
and a negative angle folds the other way.

``gaps=tab_gap`` now leaves a long stretch of each end unbent, so that the
tab is much narrower than the edge it is folded from. In the base, the
gaps were small and were there to clear the corners. Here they make the
feature.

The edges are found by selection. After step 3 the sheet has several rims
that run along Y - the ends of the plate, and the ends of the two lips,
higher up. ``group_by(Axis.Z)[0]`` takes the lowest group, which is the
ends of the plate.

***************************************
Step 5: Relieve the bends
***************************************

Look at where each tab meets the plate. The bend stops partway along the
edge, and beside it the edge carries straight on, flat. Metal cannot fold
on one side of a point and stay flat on the other. Formed like this, it
would tear at each end of the bend, and the tear would run into the plate.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [relief_builder]
            :end-before: [relief_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [relief_algebra]
            :end-before: [relief_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_relief.svg
    :align: center
    :width: 60%

:ref:`bend_relief <sheet_metal_bend_relief>` cuts a small notch into the
sheet at each end of a bend, so that the bend ends on a free edge and has
nothing to tear. It is given the bends themselves. A sheet's ``bends()``
are its curved faces, and ``filter_by(Axis.Y)`` keeps the ones whose axis
runs along Y, which are the two tab bends and not the four bends of the
lips. ``ReliefType.OBROUND`` is a notch with a rounded end.

This is the companion of the ``corner_relief`` used on the base. Corner
relief is for a place where two bends meet; bend relief is for the end of
one bend that stops inside the sheet.

******************************************************
Step 6: Trim the corners of the tabs
******************************************************

A tab with square corners catches on the wall as the lid goes on. Cut the
lower corners off at an angle.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [miter_builder]
            :end-before: [miter_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [miter_algebra]
            :end-before: [miter_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_miter.svg
    :align: center
    :width: 60%

:ref:`miter <sheet_metal_miter>` angles the side of a flange. It is given
*vertices*: the corners where the free edge of a flange meets its sides.
``tabs`` are the two flat faces that look along X, and
``group_by(Axis.Z)[0]`` takes their lowest vertices, four in all. Each
side is trimmed by ``tab_miter`` degrees, measured from square.

The same operation with a larger angle is what makes two walls meet along
a corner like a picture frame, where the base left its corners open.
:ref:`sheet_metal_recipes` shows that.

***********************************
Step 7: Bend a lead-in
***********************************

One more refinement: tip the bottom of each tab inwards a little, so that
it guides the lid into the box.

Everything folded so far was *new* material, added beyond an edge. This is
different. The tab is already there, and it is to be folded across its
middle. That is what :ref:`bend <sheet_metal_bend>` is for.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [lead_in_builder]
            :end-before: [lead_in_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [lead_in_algebra]
            :end-before: [lead_in_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_lead_in.svg
    :align: center
    :width: 60%

A sheet can only be folded along a line that is an edge of it, and there
is no edge across the middle of a tab. So first one is made: ``split``
with ``keep=Keep.BOTH`` divides the sheet with a plane ``lead_in_height``
below the plate and keeps both sides, which leaves each tab as two flat
faces sharing a new edge. Nothing else is at that height, so nothing else
is cut.

An edge shared by two flat faces in the same plane is a *fold line*, and
``fold_lines()`` on a face gives the ones on its border. Which face the
line is taken from matters: that face stays where it is, and the face on
the other side of the line swings. Here the line is taken from the upper
part of each tab, the highest group of faces looking along X, so the lower
part is what moves.

``bend`` then folds one line through ``lead_in_angle`` degrees, with the
sign choosing the direction, as for a flange. There are two tabs, so it is
done twice. In algebra mode every ``bend`` gives back a new sheet, so the
second fold line has to be found again on that new sheet, which is why the
selection is inside the loop.

*************************
Step 8: Thicken
*************************

The lid is finished as a surface. Give it its thickness.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [thicken_builder]
            :end-before: [thicken_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [thicken_algebra]
            :end-before: [thicken_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_underside.svg
    :align: center
    :width: 60%

***********************************
Step 9: Put the lid on
***********************************

The lid was made flat on ``Plane.XY``, with its plate where the floor of
the base is. Lift it into place and see whether it fits.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [fit_builder]
            :end-before: [fit_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [fit_algebra]
            :end-before: [fit_algebra]

.. code-block:: text

    False

.. image:: /tutorials/assets/sheet_metal_lid/lid_fitted.svg
    :align: center
    :width: 60%

The lift is worked out from the parts. The lips have to rest on the
highest point of the base, which is the top of its hems,
``base.bounding_box().max.Z``. In the lid's own coordinates the underside
of a lip is ``step_height - lid_thickness`` above the plate: the step up,
less the thickness of the sheet, which lies below the surface that was
modelled.

``do_children_intersect``, from :ref:`joint_tutorial`, reports ``False``:
no part of the lid is inside any part of the base. Cut through the middle,
the fit looks like this:

.. image:: /tutorials/assets/sheet_metal_lid/lid_section.svg
    :align: center
    :width: 70%

Each lip steps up over a hem and lies on top of it, flush with the outside
of the wall. The plate sits between the hems, and the tab, seen end on in
the middle, hangs down inside the short wall with its tip turned in.

*************************************
Step 10: The flat pattern
*************************************

Last, the piece to cut.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [flat_builder]
            :end-before: [flat_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_lid.py
            :language: build123d
            :start-after: [flat_algebra]
            :end-before: [flat_algebra]

.. image:: /tutorials/assets/sheet_metal_lid/lid_flat.svg
    :align: center
    :width: 55%

Every feature of the lid can be read off its pattern. The pairs of lines
along the top and bottom are the two bends of each jog. At each end, the
tab is the piece that sticks out, with its mitred corners, two lines where
it folds down from the plate, and two more further out for the lead-in.
Beside each tab are the two slots of its bend relief.

This is how the part would be made: cut to this outline, then folded
along the lines. Write the pattern to a DXF file exactly as in
:ref:`sheet_metal_tutorial`.

********************
What you learned
********************

* :ref:`jog <sheet_metal_jog>` steps a sheet sideways with two bends, and
  needs at least the two bend radii of height to do it.
* ``flange`` with a negative ``angle`` folds the other way, and with large
  ``gaps`` makes a tab narrower than its edge.
* A bend that stops inside the sheet needs
  :ref:`bend_relief <sheet_metal_bend_relief>`; a corner where two bends
  meet needs ``corner_relief``.
* :ref:`miter <sheet_metal_miter>` trims the sides of a flange at an angle.
* :ref:`bend <sheet_metal_bend>` folds existing material along a fold
  line, which is an edge between two flat faces; ``split`` makes one where
  it is wanted.
* ``bends()`` and ``flats()``, filtered by axis and grouped by height,
  pick out the features of a sheet.
* Two sheet metal parts are fitted like any others: place one from the
  measurements of the other, and check that they do not overlap.

:ref:`sheet_metal` has a page for each of these operations, and
:ref:`sheet_metal_recipes` has more ways of combining them.
