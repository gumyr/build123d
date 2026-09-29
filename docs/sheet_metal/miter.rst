.. _sheet_metal_miter:

#####
Miter
#####

A miter angles the side of a flange. Two walls folded up from adjacent edges
of a blank are held apart at the corner by their gaps; miter the ends of each
at 45 degrees and they meet along the corner instead, the way a picture frame
does. In the flat pattern a mitered corner is one straight cut from the rim to
the edge of the blank. Miters also trim a flange end back for clearance, and
with a negative angle they *extend* it into a flare.

.. image:: ../assets/sheet_metal/miter_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [miter_basic]
    :end-before: [miter_basic]

``miter`` takes **vertices**: the corners where a flange's free rim meets a
straight side running back to the bend. A positive angle trims the rim toward
its other end and a negative angle extends it. The angle is measured from the
side perpendicular to the rim, so 0 would leave the side as it is and 45 puts
the cut on the diagonal.

Selecting the corners of a wall is a matter of taking its vertices furthest
from the base: ``wall.vertices().group_by(Axis.Z)[-1]`` for a wall folded up
from ``Plane.XY``, or a single vertex of that group for one side only.

****************
Through the bend
****************

By default the cut stops where the wall meets its bend, leaving the bend
square-ended and the wall stepping in from it at the tangent line.
``through_bend=True`` carries the cut on to the fold line, which is what a
mitered corner is in the flat pattern: one straight cut across the whole
flange to the edge of the blank. A trimming miter narrows the bend to match
the wall and an extending one widens it.

.. image:: ../assets/sheet_metal/miter_through_bend.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [miter_through_bend]
    :end-before: [miter_through_bend]

The angle is held in the flat pattern rather than on the reference surface,
since that is where a miter is laid out, so the cut is very slightly skewed on
the formed bend by however far the neutral axis lies from the reference
surface. Mitered bends are what let flanges folded into a hole meet at its
corners instead of being held apart by a gap.

*******
Flaring
*******

A negative angle extends the side of the flange instead of trimming it. With
``through_bend`` the bend widens to match, so the flare runs from the fold
line rather than starting at the tangent line:

.. image:: ../assets/sheet_metal/miter_flare.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [miter_flare]
    :end-before: [miter_flare]

Two miters that eat past each other meet inside the flange and leave a
triangle, as does a lone one whose cut leaves through the far side.

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters)
    wall = sheet.flats().sort_by(Axis.Z)[-1]
    sheet = miter(
        wall.vertices().group_by(Axis.Z)[-1],
        30,
        through_bend=True,
        sheet_parameters=parameters,
    )

``sheet_parameters`` is only needed for ``through_bend`` in Algebra mode,
since that is the case where the cut is laid out on the blank.

***************
What it refuses
***************

* A vertex that is not the end of a free flange rim: a corner of the base, a
  vertex on a bend, or one whose side does not run straight back to the bend.
* An angle of 90 degrees or beyond in either direction.
* A cut that would run across a hole in the wall, or through a hole in the
  bend with ``through_bend``: only the rim and the side that meet at the
  corner are redrawn, so the rest of the outline must stay clear of the cut.

*******
Related
*******

* :ref:`Corner relief <sheet_metal_corner_relief>` is the alternative at a
  corner: open it instead of closing it.
* :ref:`Flange <sheet_metal_flange>` makes the walls a miter angles.
