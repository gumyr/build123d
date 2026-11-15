.. _sheet_metal_recipes:

#######
Recipes
#######

Short worked answers to the things a sheet metal part usually needs, each
built from the operations on the preceding pages. Every snippet is complete
and runs as shown: they are all part of the tested examples script.

*****************************
A tab folded up out of a slot
*****************************

A slot cut in the base is a hole, and its straight edges are rims, so a flange
folds a tab up out of it. ``gaps`` make the tab narrower than the slot, which
is what leaves clearance at its sides:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_tab]
            :end-before: [recipe_tab]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_tab_algebra]
            :end-before: [recipe_tab_algebra]

The tab is 26 wide in a 30 slot and stands 13 high, its bend included. The
bend rolls up into the slot, so the slot has to be wider than the bend's
footprint, here the reference radius of 1.

*******************************
A cut across a bend from a view
*******************************

A normal cut is a solid, and a part object in ``Mode.SUBTRACT`` cuts every
face it passes through. A box tall enough to reach the sheet on both sides of
the drawing plane, centred on the bend, cuts a slot through the base, the bend
and the wall in one go:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_cut]
            :end-before: [recipe_cut]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_cut_algebra]
            :end-before: [recipe_cut_algebra]

The cutter must reach the reference surface, which for ``SheetSurface.INSIDE``
is the drawn face rather than the middle of the material; a cutter spanning
both sides of the drawing plane always does.

****************
Flaring a flange
****************

``miter`` with a negative angle extends a flange's sides instead of trimming
them, and ``through_bend=True`` widens the bend to match, so the flare runs
from the fold line rather than starting at the bend tangent:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_flare]
            :end-before: [recipe_flare]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_flare_algebra]
            :end-before: [recipe_flare_algebra]

The wall's free end is 38.2 wide on a 20 edge, and the bend has widened to
22.1. Without ``through_bend`` the bend stays 20 wide and the wall steps out
from it at the tangent line.

*******************************
A flange narrower than its edge
*******************************

``gaps`` leave part of the edge unbent, and the face keeps that part of its
edge as tabs beside the bend. With a set-back ``position`` the face is notched
by the setback under the bend only, so the tabs still reach the corner the
face was drawn to, and ``unfold`` shows the notch on the blank:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_narrow]
            :end-before: [recipe_narrow]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_narrow_algebra]
            :end-before: [recipe_narrow_algebra]

The bend is 20 wide on a 60 edge, the base still reaches ``x = 50`` on the
tabs either side of it, and the blank carries a notch 2 deep, the inside
setback of a 90 degree bend at radius 2, where the bend's strip came out of
the face. Two flanges meeting at a corner with set-back positions need gaps
wider than the setback, so their strips do not overlap, and the corner then
wants :ref:`corner relief <sheet_metal_corner_relief>` as usual.

******************************
Walls that meet at the corners
******************************

Flanges folded from adjacent edges are held apart by their gaps. Miter the
ends of each wall at 45 degrees through the bend and they meet along the
corner instead, ready to be welded:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_corners]
            :end-before: [recipe_corners]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_corners_algebra]
            :end-before: [recipe_corners_algebra]

***********************
A part from its drawing
***********************

A U channel dimensioned to its outside faces, 60 wide, 40 high and 100 long,
in 2 mm sheet bent to an inside radius of 3, is drawn with exactly those
numbers: ``position`` puts the outside corner on the edge and ``length_from``
measures the wall to the outer sharp:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_channel]
            :end-before: [recipe_channel]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
            :language: build123d
            :start-after: [recipe_channel_algebra]
            :end-before: [recipe_channel_algebra]

Thickened, the part measures 60 × 100 × 40 outside, and its flat pattern is
``60 + 40 + 40 - 2 × 3.717 = 132.566`` long: the outside dimensions less two
bend deductions. The arithmetic is under
:ref:`dimensioning <sheet_metal_dimensioning>`.

**************************
Reusing a sheet in another
**************************

:func:`~operations_generic.insert` brings faces, sketches, shells and other
``BuildSheet`` builders into the current sheet, with optional rotation and
placement, as long as the result sews into one connected shell. Solids are
not accepted as sheet material, only as cutters, since ``BuildSheet`` does not
reverse-engineer a reference surface from a solid.

.. literalinclude:: /how_to/sheet_metal/sheet_metal_examples.py
    :language: build123d
    :start-after: [recipe_reuse]
    :end-before: [recipe_reuse]

``insert`` is a builder operation. In Algebra mode, make the lug where it
belongs instead: flange the edge of the plate, with ``gaps`` to set its
width.
