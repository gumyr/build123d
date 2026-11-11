.. _tutorial_sketch_then_extrude:

####################
Sketch, then extrude
####################

Most parts are easiest to make by drawing their shape flat and then giving it
depth. In this tutorial you will build this slotted mounting plate that way:
its outline, its hexagonal hole, its two slots and its raised rim are all
drawn as flat sketches first, and only then turned into a solid.

.. image:: /tutorials/assets/sketch_then_extrude/plate_rim.svg
    :align: center

Along the way you will:

* draw a sketch from ready-made 2D shapes,
* turn a sketch into a solid with ``extrude``,
* cut holes by changing the sketch, not by cutting the solid,
* repeat a feature in more than one place, and
* derive one sketch from another with ``offset``.

It takes about fifteen minutes. You need build123d installed and a way to
look at a model, as described in :ref:`hello_world`; nothing else is assumed.

Every step shows its code twice, in builder mode and in algebra mode. The
objects and operations are the same in both - the same ``RectangleRounded``,
the same ``extrude`` - and only the way they are used differs: builder mode
collects them inside ``with`` blocks, algebra mode combines them with
operators. Pick whichever tab you prefer - the others on the page follow -
and ignore the second one. Both make exactly the same part. :ref:`where_next`
describes the difference between the two.

*************
Step 1: Setup
*************

Start a new Python file with the import and the dimensions of the plate, all
in millimetres. Giving each dimension a name now means that the part can be
resized later by changing a number in one place.

.. literalinclude:: /tutorials/sketch_then_extrude.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

This part is the same in both modes. Each step below shows the whole of the
rest of the file as it stands at that point, so you can replace what you had
with what is shown.

********************
Step 2: The outline
********************

The plate is a rectangle with rounded corners, and build123d has that shape
ready-made: :class:`~objects_sketch.RectangleRounded`.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [outline_builder]
            :end-before: [outline_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [outline_algebra]
            :end-before: [outline_algebra]

.. image:: /tutorials/assets/sketch_then_extrude/plate_outline.svg
    :align: center

This is a *sketch*: a flat shape with an area but no thickness. In builder
mode the ``with BuildSketch()`` block collects the 2D objects created inside
it; in algebra mode the object is the sketch. Either way it is centred on the
origin and lies flat on the XY plane.

**********************
Step 3: Give it depth
**********************

:func:`~operations_part.extrude` pushes a sketch straight up into a solid,
here by ``thickness``.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [extrude_builder]
            :end-before: [extrude_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

.. image:: /tutorials/assets/sketch_then_extrude/plate_extrude.svg
    :align: center

It is the same ``extrude`` in both modes, and its first argument is the shape
to extrude. In algebra mode that argument is given: ``extrude(outline, ...)``.
In builder mode the sketch sits inside a ``with BuildPart()`` block, and when
the argument is left out ``extrude`` takes the sketch that was just finished.
It can be given there too - ``extrude(outline.sketch, amount=thickness)``
does the same thing - but leaving it out is the usual style. The finished
solid is ``plate.part`` in builder mode and ``plate`` in algebra mode.

That is the whole method. The rest of the tutorial changes the *sketch*, and
the solid follows.

******************************************
Step 4: Shape the sketch, not the solid
******************************************

The plate needs a hexagonal hole through its centre to hold a nut. Do not
reach for a way to cut the solid. Take the hexagon out of the sketch instead,
so that the shape being extruded already has the hole in it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [hexagon_builder]
            :end-before: [hexagon_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [hexagon_algebra]
            :end-before: [hexagon_algebra]

.. image:: /tutorials/assets/sketch_then_extrude/plate_hexagon_sketch.svg
    :align: center

:class:`~objects_sketch.RegularPolygon` draws the hexagon. In builder mode
``mode=Mode.SUBTRACT`` removes it from the sketch instead of adding it (see
:class:`~build_enums.Mode`); in algebra mode the ``-=`` operator does the
same job. The ``extrude`` line has not changed, and the hole comes out the
full depth of the plate:

.. image:: /tutorials/assets/sketch_then_extrude/plate_hexagon.svg
    :align: center

Keeping the design in the sketch pays off as a part grows: the flat drawing
stays readable, every feature is the same depth without being told, and
there is one extrusion to change if the thickness does.

***********************************
Step 5: The same feature twice
***********************************

Two slots let the plate slide on its fixings before they are tightened.
:class:`~objects_sketch.SlotOverall` draws one from its overall length and
its width; ``rotation=90`` turns it to run across the plate.

Until now every shape has landed at the origin. The slots go either side of
it, ``slot_spacing`` apart.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [slots_builder]
            :end-before: [slots_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [slots_algebra]
            :end-before: [slots_algebra]

.. image:: /tutorials/assets/sketch_then_extrude/plate_slots_sketch.svg
    :align: center

In builder mode :class:`~build_common.Locations` names the two places, and
everything created inside its block is created at each of them. In algebra
mode :class:`~geometry.Pos` moves a slot to where it belongs, and an ordinary
Python loop does that twice. Placing things is the subject of a later
tutorial; this is all that is needed here.

.. image:: /tutorials/assets/sketch_then_extrude/plate_slots.svg
    :align: center

*******************************************
Step 6: A second sketch for the rim
*******************************************

A raised rim stiffens the plate. It is a second sketch, extruded higher than
the first: the outline of the plate with a smaller copy of itself removed,
leaving a band ``rim_width`` wide.

The smaller copy is not drawn. :func:`~operations_generic.offset` makes it
from the outline, moving every edge inwards by the same distance, corners
included.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [rim_builder]
            :end-before: [rim_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sketch_then_extrude.py
            :language: build123d
            :start-after: [rim_algebra]
            :end-before: [rim_algebra]

.. image:: /tutorials/assets/sketch_then_extrude/plate_rim_sketch.svg
    :align: center

Again it is one operation used two ways. In algebra mode ``offset`` is given
the shape to work on and the result is subtracted from that shape. In builder
mode, with no shape named, it works on the sketch so far, and
``mode=Mode.SUBTRACT`` removes the result from it. The second
``extrude`` adds its solid to the first, and the plate is finished:

.. image:: /tutorials/assets/sketch_then_extrude/plate_rim.svg
    :align: center

Because the rim is derived from the outline, it follows the outline. Change
``length`` to 120 or ``corner_radius`` to 15 at the top of the file and run
it again: the plate, the slots and the rim all move together.

*****************
What you learned
*****************

* A **sketch** is a flat shape. :class:`~objects_sketch.RectangleRounded`,
  :class:`~objects_sketch.RegularPolygon` and
  :class:`~objects_sketch.SlotOverall` are three of the ready-made ones;
  :ref:`cheat_sheet` lists the rest.
* :func:`~operations_part.extrude` turns a sketch into a solid.
* Shapes are **added to or subtracted from** a sketch, with ``mode=`` in
  builder mode and ``+`` and ``-`` in algebra mode.
* Design decisions belong in the sketch. The solid is what the sketch
  produces.
* :func:`~operations_generic.offset` derives a new shape from an existing
  one, so the two stay in step.
