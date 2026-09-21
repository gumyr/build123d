.. _sheet_metal_sheet_shells:

############
Sheet shells
############

A sheet-metal part does not always start life in ``BuildSheet``. It may be
imported from a STEP file, built directly as a solid, or received from
another program, and then there is no reference shell to unfold or to add a
flange to. :func:`~operations_sheet.sheet_shells` is the way back: it takes a
constant-thickness solid apart into its two sheet surfaces and its thickness.

.. image:: ../assets/sheet_metal/sheet_shells_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [sheet_shells_basic]
    :end-before: [sheet_shells_basic]

The two surfaces come back larger area first, and no more is claimed about
them than that. On a part bent one way the larger one is the outside, but a
part bent both ways has no outside, so the order is a fact rather than a
label.

******************
How it finds them
******************

The thickness faces, the narrow faces along every edge, hole, relief and hem,
are found by measurement rather than by type. Every face is measured between
its non-adjacent boundary edges. Each thickness face has two boundary edges
exactly the thickness apart, so taking away the faces that measure the
thickness leaves the two surfaces, and the thickness is the smallest distance
shared by two or more faces that does so. The smallest matters: along an
extruded profile, a channel or a trough, every sheet face measures the length
of the part, and taking those away also leaves two surfaces, its two ends.
Every face with a pair of edges at the thickness is then a thickness face, and
what remains sews into the two surfaces.

``thickness``, when the sheet's thickness is known, is taken as given and
nothing is searched for. It settles a part whose own measurements are
ambiguous, and a thickness that does not leave two surfaces is refused rather
than replaced by one that does.

``tolerance`` is how far a measured distance may be from the thickness, as a
fraction of it, and still count. Offset surfaces are approximations, and the
blended corner faces of a relief can measure a few millionths off; the default
of 1e-4 is generous for that and still far below any feature size. It only
needs changing if a part comes back with too few or too many thickness faces,
which shows up as the surfaces failing to split in two.

********************
Back into the model
********************

Either surface is a reference ``Shell``. Pair it with parameters that name
the thickness and which surface it is, and the sheet operations apply:

.. code-block:: build123d

    larger, smaller, thickness = sheet_shells(imported_part)
    parameters = SheetMetalParameters(
        thickness=thickness, sheet_surface=SheetSurface.INSIDE
    )
    flat_pattern = unfold(smaller, sheet_parameters=parameters, align=Align.MIN)

The bend radius is not returned; it is the radius of the smallest cylindrical
face on the chosen surface if a later operation needs it.

***************
What it refuses
***************

* A shape that does not hold exactly one solid.
* A given ``thickness`` that is not positive, or whose faces do not leave
  exactly two surfaces when taken away.
* A solid with no distance that is a thickness, one whose faces leave exactly
  two surfaces when taken away: a sphere, which measures nothing, a cube, whose
  every face measures the same, or a welded assembly of sheets.
* A ``tolerance`` that is not positive.

*******
Related
*******

* :ref:`Unfold <sheet_metal_unfold>` develops a recovered surface into the
  flat pattern.
* :ref:`Thicken <sheet_metal_thicken>` is the opposite direction, from a
  reference shell to the solid.
