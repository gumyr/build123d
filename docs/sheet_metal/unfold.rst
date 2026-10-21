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

``unfold`` returns two things: the pattern, a planar ``Shell`` whose outline
and holes export like any other 2D geometry, and a record of what each of
its faces developed from. A DXF with the outline for the cutter and a bend
line per bend for the brake operator:

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)
        flat, face_map = unfold(align=Align.MIN)

    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer("cut")
    exporter.add_layer("bend_up", line_type=LineType.DASHED)
    exporter.add_layer("bend_down", line_type=LineType.DASHED)
    exporter.add_shape(flat, layer="cut")
    for face in flat.faces():
        record = face_map[face]
        if record.is_bend:
            layer = "bend_up" if record.up else "bend_down"
            exporter.add_shape(record.bend_line, layer=layer)
    exporter.write("tray_blank.dxf")

``face_map`` is a :class:`~sheet_utils.FaceMap`, looked up by any face of the
pattern, and each entry is an :class:`~sheet_utils.UnfoldedFace`:

* ``sheet_face`` - the face of the folded sheet it developed from, for every
  face
* ``is_bend`` - whether that face was a cylinder
* ``angle``, ``inside_radius``, ``neutral_radius`` - the bend to put back,
  and the radius its strip's width was taken at
* ``bend_line`` - the centre line of the strip, on the pattern, from the first
  point it meets material to the last; a hole across the bend does not
  interrupt it
* ``up`` - the bend folds toward +Z as the blank lies on ``Plane.XY``

The lookup is by the face's underlying kernel shape, so it still answers
after the pattern has been moved for nesting, but not after an operation
that rebuilds its faces, such as a boolean or ``clean``.

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
    flat, face_map = unfold(sheet, sheet_parameters=parameters, align=Align.MIN)

***************
What it refuses
***************

* No sheet: a bare ``unfold()`` outside any ``BuildSheet``.
* Missing parameters in Algebra mode, or parameters given inside a
  ``BuildSheet``.
* A fold with no bend in it: two faces meeting along an edge at an angle,
  two flats at a sharp corner or a wall leaving its bend before the tangent.
  Unfolding develops bends, and hinging such a fold would cut the pattern
  short by the allowance a real bend consumes and record no bend for it. The
  error names the edge and the angle; give the fold a bend radius. A sheet
  from ``BuildSheet`` never has one, since every bend gets a radius, but a
  bracket modelled as two boxes and taken apart with ``sheet_shells`` does.
* A sheet closed into a loop, which has nowhere to start: a tube, or walls
  that touch at a corner and were sewn together. It needs a cut first.
* A surface other than a plane or a cylinder, or a sheet with no planar face
  at all.

*******
Related
*******

* :ref:`Thicken <sheet_metal_thicken>` is the other way out of the model: the
  solid part rather than the blank.
* :ref:`Dimensioning <sheet_metal_dimensioning>` explains the bend allowance
  and deduction the pattern's length comes from.
