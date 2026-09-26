.. _sheet_metal_recipes:

#######
Recipes
#######

Short worked answers to the things a sheet metal part usually needs, each
built from the operations on the preceding pages. Every snippet is complete
and runs as shown.

*****************************
A tab folded up out of a slot
*****************************

A slot cut in the base is a hole, and its straight edges are rims, so a flange
folds a tab up out of it. ``gaps`` make the tab narrower than the slot, which
is what leaves clearance at its sides:

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=1) as bracket:
        with BuildSketch():
            Rectangle(100, 60)
            SlotCenterToCenter(30, 8, mode=Mode.SUBTRACT)
        slot_edge = bracket.rims().filter_by(Axis.X).sort_by(Axis.Y)[1]
        flange(slot_edge, length=12, gaps=2)

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

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.rims().sort_by(Axis.X)[-1], length=20)
        with Locations((50, 0)):
            Box(20, 6, 60, mode=Mode.SUBTRACT)

The cutter must reach the reference surface, which for ``SheetSurface.INSIDE``
is the drawn face rather than the middle of the material; a cutter spanning
both sides of the drawing plane always does.

****************
Flaring a flange
****************

``miter`` with a negative angle extends a flange's sides instead of trimming
them, and ``through_bend=True`` widens the bend to match, so the flare runs
from the fold line rather than starting at the bend tangent:

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as leg:
        with BuildSketch():
            Rectangle(40, 20)
        flange(leg.rims().sort_by(Axis.X)[-1], length=30)
        wall = leg.flats().sort_by(Axis.Z)[-1]
        miter(wall.vertices().group_by(Axis.Z)[-1], -15, through_bend=True)

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

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as plate:
        with BuildSketch():
            Rectangle(100, 60)
        flange(
            plate.rims().sort_by(Axis.X)[-1],
            length=15,
            gaps=(10, 30),
            position=BendPosition.MATERIAL_INSIDE,
        )
    blank = unfold(plate.sheet, plate.sheet_parameters)

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

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as box:
        with BuildSketch():
            Rectangle(60, 40)
        flange(box.rims(), length=15, gaps=3.1)
        walls = box.flats().group_by(Axis.Z)[-1]
        miter(walls.vertices().group_by(Axis.Z)[-1], 45, through_bend=True)

***********************
A part from its drawing
***********************

A U channel dimensioned to its outside faces, 60 wide, 40 high and 100 long,
in 2 mm sheet bent to an inside radius of 3, is drawn with exactly those
numbers: ``position`` puts the outside corner on the edge and ``length_mode``
measures the wall to the outer sharp:

.. code-block:: build123d

    with BuildPart() as channel_part:
        with BuildSheet(thickness=2, bend_radius=3) as channel:
            with BuildSketch():
                Rectangle(60, 100)
            flange(
                channel.rims().filter_by(Axis.Y),
                length=40,
                position=BendPosition.MATERIAL_OUTSIDE,
                length_mode=FlangeLength.OUTER_SHARP,
            )
        thicken()

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

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as lug:
        with BuildSketch():
            Rectangle(20, 10)
        flange(lug.rims().sort_by(Axis.X)[-1], length=10)

    with BuildSheet(thickness=1, bend_radius=2) as plate:
        with BuildSketch():
            Rectangle(60, 40)
        with Locations((20, 0)):
            insert(lug)
