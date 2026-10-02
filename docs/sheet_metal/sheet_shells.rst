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

The two surfaces are found as pairs of faces with the sheet between them,
rather than by the type of any face. A bend is two coaxial cylinders lying
side by side whose radii differ by the thickness, and nothing else on a
sheet-metal part is, so where the part has bends they settle the thickness
outright - a rolled tube has no flat at all but its two ends. A flat is two
planar faces facing away from each other with the sheet between: each planar
face casts its shadow into the material, holes and all, and pairs with the
first face facing back that the shadow falls on. The faces of the sheet's
edges pair the same way across its width, but a sheet's faces are far larger
than its edge faces, so the distance the most face area agrees on is the
thickness. The faces of pairs at that distance are the surfaces, and sew into
the two sides of the sheet; everything else - every edge face, hole wall,
relief and hem end - is thickness.

``thickness``, when the sheet's thickness is known, is taken as given and
nothing is searched for. It settles a part whose own measurements are
ambiguous, and a thickness that does not leave two surfaces is refused rather
than replaced by one that does.

``tolerance`` is how far a measured distance may be from the thickness, as a
fraction of it, and still count. Offset surfaces are approximations, and the
blended corner faces of a relief can measure a few millionths off; the default
of 1e-4 is generous for that and still far below any feature size. It only
needs changing if a part comes back with too few or too many surface faces,
which shows up as the surfaces failing to sew into two.

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
* A given ``thickness`` that is not positive, or at which the paired faces do
  not form exactly two surfaces.
* A solid with no pair of faces a sheet apart, such as a sphere, or whose
  paired faces do not form two surfaces: a cube, whose six faces pair into one
  closed surface, or a welded assembly of sheets.
* A ``tolerance`` that is not positive.

*******
Related
*******

* :ref:`Unfold <sheet_metal_unfold>` develops a recovered surface into the
  flat pattern.
* :ref:`Thicken <sheet_metal_thicken>` is the opposite direction, from a
  reference shell to the solid.
