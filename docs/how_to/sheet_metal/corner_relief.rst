.. _sheet_metal_corner_relief:

#############
Corner relief
#############

Where two flanges meet at a corner of the blank, the two bends run into each
other. Fold them without doing anything and the material at the corner is
asked to bend two ways at once: it bunches, tears, or leaves a bulge that has
to be ground off. **Corner relief** cuts that material away before forming,
opening the corner so each flange can fold on its own. Every box, tray and
enclosure with folded-up sides has it.

.. image:: /how_to/assets/sheet_metal/corner_relief_basic.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_basic]
            :end-before: [corner_relief_basic]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_basic_algebra]
            :end-before: [corner_relief_basic_algebra]

``corner_relief`` takes the **corner vertices** of a flat face, each with a
bend on both sides of it, and cuts the chosen shape there. After flanging with
gaps the base's outline has extra vertices where each bend starts, but those
lie on a straight run of the outline and are ``SMOOTH``, so the corners are the
face's convex vertices: ``base.vertices().filter_by(Convexity.CONVEX)``. A
vertex that has a bend on only one side, such as one where a bend starts, is
refused.

**********
The shapes
**********

The shape is named by ``ReliefType``. The first three are cut in the *flat
pattern*, so that is where they come out their own shape: a round relief is a
circle on the blank, not on the formed part, where the parts crossing a bend
read smaller. One wide enough to pass right through a bend carries on into
the flange beyond it, as the hole would on the blank.

.. image:: /how_to/assets/sheet_metal/corner_relief_types.svg
    :align: center

==================  ===========================================================
Shape               What it is and when to use it
==================  ===========================================================
``ROUND``           A circle of ``radius`` centred on the corner. The most
                    common choice: a punched hole is cheap, it has no stress
                    concentration, and it hides under the folded corner.
``SQUARE``          A square-cornered notch of ``size`` aligned to the fold
                    lines. Suits laser-cut blanks and leaves the flanges
                    ending on straight edges, so they can be welded up.
``OBROUND``         A slot of ``length`` and ``width`` on the corner's
                    diagonal. Reaches further into the corner than a circle
                    of the same width, for a larger bend radius or a wider
                    gap.
``CONSTANT_WIDTH``  Continues the gap the two flanges already leave straight
                    through the corner to ``depth``. It is defined by the
                    formed part rather than the blank, so its width is
                    measured from the sheet, not supplied, and it is only
                    meaningful where two flanges meet on a corner the sheet
                    stops at. Flanges closed over the corner with a
                    negative ``gaps`` cross the line of the slot once
                    formed; what it cuts free of them is dropped, as it
                    would fall from the blank.
==================  ===========================================================

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_types]
            :end-before: [corner_relief_types]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_types_algebra]
            :end-before: [corner_relief_types_algebra]

Each shape has its own keyword and the others are refused: ``ROUND`` takes
``radius``, ``SQUARE`` takes ``size``, ``OBROUND`` takes ``length`` and
``width``, and ``CONSTANT_WIDTH`` takes only ``depth``.

A corner need not be square. The shapes are laid out on the blank either
side of the corner's miter line, the bisector of the two bends, so a round
relief is a circle on the blank at any corner angle and an obround lies along
the miter. A ``SQUARE`` is aligned to both fold lines only where they are at
right angles; elsewhere it stays a true square, set symmetrically about the
miter.

******************************
Moving it along the miter line
******************************

``ROUND``, ``SQUARE`` and ``OBROUND`` are centred on the corner. ``offset``
moves the centre along the corner's miter line, the bisector of the two
bends, by a distance measured on the blank: positive is outward, between the
two flanges, and negative is into the base.

This is for a **closed corner**. Flanges given a negative
:ref:`gap <sheet_metal_flange>` reach past the corner toward each other and
are cut back to the miter line where they would overlap on the blank. That
cut has no width, and a narrow slot laid on it, as a laser would cut one,
gives it some. ``offset`` says where along the cut the slot sits:

.. image:: /how_to/assets/sheet_metal/corner_relief_offset.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_offset]
            :end-before: [corner_relief_offset]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [corner_relief_offset_algebra]
            :end-before: [corner_relief_offset_algebra]

The miter runs from the corner for the length of the gap along each edge, so
its own length is the gap times the square root of two at a square corner. A
relief moved clear of the corner leaves the corner vertex in place, so the
same vertex can be selected again. ``CONSTANT_WIDTH`` has no centre to move
and refuses ``offset``.

*****************
Corners at a hole
*****************

A corner the sheet wraps *around* rather than stops at, the corner of a
flanged hole for example, is relieved the same way. There the sheet fills
three quadrants instead of one and both bends unroll into the fourth, each
taking whatever part of the profile lands on it.

***************************
Why it needs the parameters
***************************

A relief is laid out on the blank, and the blank is measured on the neutral
axis, whose position depends on the K-factor. That is why
``corner_relief`` needs ``sheet_parameters`` in Algebra mode even though it
only cuts.

***************
What it refuses
***************

* A vertex that is not a corner of a flat with a bend on each side of it.
* A keyword that does not belong to the chosen shape, or a required one left
  out.
* A relief that would cut the corner of the sheet loose, or reach through a
  flange.
* A ``CONSTANT_WIDTH`` relief where the two flanges touch, since there is no
  gap left to continue.
* A relief moved so far along the miter line that it removes nothing.

********
See also
********

* :ref:`Bend relief <sheet_metal_bend_relief>` is for a bend that stops inside
  the sheet without meeting a second bend: one fold line runs through the
  site instead of two.
* :ref:`Miter <sheet_metal_miter>` closes a corner where relief opens it.
* :ref:`Flange <sheet_metal_flange>` gaps are what leave the corner open in
  the first place.
