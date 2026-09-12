.. _sheet_metal_cutouts:

#################
Holes and cutouts
#################

Most of the holes in a sheet metal part are cut in the blank before it is
formed: mounting holes, vents, slots for tabs. A few are cut *after* forming,
straight through a bend from one direction, where the blank would have had to
carry an awkward developed outline. build123d supports both, and which one you
get follows from what you draw the cutter as.

***************
Holes in a face
***************

A 2D shape drawn inside ``BuildSheet`` is a **cutter for the face it lies
on**. Drawn in ``Mode.SUBTRACT`` it trims that face, so a circle on the
default plane cuts the base and one placed on a wall's plane cuts the wall.
Where the shape lies is where it cuts:

.. image:: ../assets/sheet_metal/cutout_face.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [cutout_face]
    :end-before: [cutout_face]

A nested ``BuildSketch`` in ``Mode.SUBTRACT`` cuts the same way, which is how
a pattern of holes lands on one face: a sketch on the plane of a selected
flat cuts the pattern into that flat alone.

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.rims().sort_by(Axis.Y)[-1], length=20)

        wall = tray.flats().sort_by(Axis.Z)[-1]
        with BuildSketch(Plane(wall), mode=Mode.SUBTRACT):
            with GridLocations(20, 8, 3, 2):
                Circle(2)

Cutting this way is limited to the face the cutter lies on. A face lying on no
sheet face is refused rather than ignored, and a hole that has to cross a bend
needs a solid cutter.

A sketch object written inside ``BuildSheet`` with the default ``Mode.ADD`` is
refused: a sheet is never drawn from 2D pieces the way a sketch is, so new
material always arrives through a nested ``BuildSketch``.

**********************
Cutouts through a bend
**********************

A **solid** in ``Mode.SUBTRACT`` cuts every face it passes through. This is
the *drawn cutout* of sheet metal packages: a profile drawn on a view plane
and cut straight through the folded part, so it may cross a bend. Part objects
are cutters too, so holes can be placed with the usual location contexts, and
a cutter built before the context comes in with
:func:`~operations_generic.insert`:

.. image:: ../assets/sheet_metal/cutout_solid.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [cutout_solid]
    :end-before: [cutout_solid]

.. code-block:: build123d

    punch = extrude(Pos(50, 0) * Rectangle(20, 6), 30, both=True)

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.rims().sort_by(Axis.X)[-1], length=20)
        insert(punch, mode=Mode.SUBTRACT)

A drawn cutout *trims*: it changes the outline of each face it crosses without
changing the face's supporting surface, so the sheet keeps its planar and
cylindrical geometry and still unfolds. Three things follow:

* The cutter has to reach the **reference surface**, which for
  ``SheetSurface.INSIDE`` or ``OUTSIDE`` is one face of the material rather
  than its middle. A cutter placed against the opposite face misses the shell
  entirely; one spanning both sides of the drawing plane always reaches it.
* A cut that separates the sheet into disconnected pieces is refused, since
  the reference shell must stay connected.
* A cutter removes the area it covers where it crosses the reference surface.
  Shaped cutters such as ``CounterSinkHole`` therefore leave a plain opening
  of that size rather than forming the material.

************
Algebra mode
************

:meth:`~topology.Shell.cut_sheet` is the operation behind both kinds of
cutter. It trims a sheet with solids, which cut every face they pass through,
or with faces coplanar with one of its flats:

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges().sort_by(Axis.X)[-1], length=20, sheet_parameters=parameters)
    sheet = sheet.cut_sheet(Pos(30, 0) * Box(12, 8, 60))
    sheet = sheet.cut_sheet(Pos(-10, 0) * Circle(4))

*******
Related
*******

* :ref:`Bend relief <sheet_metal_bend_relief>` and :ref:`corner relief
  <sheet_metal_corner_relief>` are cuts too, but laid out on the blank by the
  fold geometry rather than drawn.
* The :ref:`recipes <sheet_metal_recipes>` include a tab folded up out of a
  slot, where the slot is a hole whose edge is then flanged.
