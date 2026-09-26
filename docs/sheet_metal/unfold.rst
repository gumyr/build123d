.. _sheet_metal_unfold:

######
Unfold
######

The **flat pattern** is the blank a part is cut from: the folded part
developed back into a flat sheet, with each bend replaced by the length of
flat it consumes. It is what goes to the laser or the punch, and getting it
right is the reason the model tracks the neutral axis at all. ``unfold``
produces it from the reference shell.

.. image:: ../assets/sheet_metal/unfold_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [unfold_basic]
    :end-before: [unfold_basic]

Each bend is developed at its **neutral radius**, worked out from the
thickness, the K-factor and the reference surface, so the flat it becomes is
the bend allowance and the pattern folds back to the part. That is why the
operation needs the sheet parameters, and takes them from the enclosing
``BuildSheet``.

**********************
Where the pattern goes
**********************

The pattern is always built on ``Plane.XY``, and ``align`` places it within
that plane. The default, ``Align.NONE``, leaves it where the development put
it, registered with the source sheet: the base stays where it was and the
walls unfold outward from it. ``Align.MIN`` puts the pattern's lower-left
corner on the origin, which is what a nesting or cutting workflow usually
wants.

*******************
Exporting the blank
*******************

The pattern is a planar ``Shell``, so its outline and holes export like any
other 2D geometry. A DXF for the cutter:

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)
        flat = unfold(align=Align.MIN)

    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer("cut")
    exporter.add_shape(flat, layer="cut")
    exporter.write("tray_blank.dxf")

Bend lines are the boundaries between the developed bends and the flats, so
the developed bend faces of the pattern can go on a separate layer for the
brake operator.

****************
The Shell method
****************

:meth:`~topology.Shell.unfold` is the method behind the operation. It accepts
the parameters optionally, and *without* them falls back to each bend's
geometric radius on the reference surface, which produces a pattern that will
not fold back to the requested part. Prefer the operation unless you
specifically want the geometric development.

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
    flat = unfold(sheet, sheet_parameters=parameters, align=Align.MIN)

***************
What it refuses
***************

* No sheet: a bare ``unfold()`` outside any ``BuildSheet``.
* Missing parameters in Algebra mode, or parameters given inside a
  ``BuildSheet``.

*******
Related
*******

* :ref:`Thicken <sheet_metal_thicken>` is the other way out of the model: the
  solid part rather than the blank.
* :ref:`Dimensioning <sheet_metal_dimensioning>` explains the bend allowance
  and deduction the pattern's length comes from.
