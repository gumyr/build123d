.. _sheet_metal_hem:

###
Hem
###

A hem folds the edge of the sheet back on itself. A raw sheared edge is sharp
and flexible; folding it over hides the edge, doubles the material along it
for stiffness, and gives a finished look. Hems are what the rims of a tray, the
edges of a door skin, and the top of an enclosure wall get.

A hem is really a flange folded through 180 degrees, and ``hem`` takes the same
rims a :ref:`flange <sheet_metal_flange>` does. What distinguishes hems from
each other is the profile of the fold, named by ``HemType``.

.. image:: ../assets/sheet_metal/hem_types.svg
    :align: center

=============  =================================================================
Type           Profile and when to use it
=============  =================================================================
``FLAT``       Folded completely flat against the sheet. The stiffest and most
               compact hem, at the cost of the tightest bend, so it suits
               ductile material and thin gauges.
``OPEN``       Folded back with a gap between the leg and the sheet. Easier
               to form than a flat hem and used where a flat one would crack
               the material, or to leave room for another sheet to slide in.
``TEARDROP``   Folded past 180 degrees on a generous radius so the leg angles
               back down to touch the sheet, giving a teardrop section. A
               common compromise between the strength of a flat hem and the
               formability of an open one.
``ROLLED``     An open curl with no flat leg: the edge is rolled round on a
               radius through a given angle. Used for wire-edge style rims
               and where a rounded edge is wanted.
=============  =================================================================

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [hem_types]
    :end-before: [hem_types]

*******************
Sizing each profile
*******************

Each profile has its own keyword arguments, and arguments that do not belong
to the chosen profile are refused rather than ignored:

==============  ============================  ================================
Type            Required                      Optional
==============  ============================  ================================
``FLAT``        ``width``
``OPEN``        ``width``, ``opening`` > 0
``TEARDROP``    ``width``                     ``radius``, ``opening``
``ROLLED``                                    ``radius``, ``roll_angle``
==============  ============================  ================================

``width`` is how far the hem reaches back across the sheet from the edge,
bend included, so it is the size you would measure on the finished part.
``opening`` is the gap between the leg and the sheet; an open hem's bend
radius follows from it, half the opening. ``radius`` is the inside radius of
a teardrop or rolled curl and defaults to the sheet's bend radius. A teardrop
with no ``opening`` brings the tip of the leg down to touch the sheet, and an
``opening`` stands it off by that much. ``roll_angle`` is how far a rolled hem
turns, in degrees; left out, the curl turns as far as it can before it would
meet the sheet, a little past 270 degrees.

A flat hem has no opening, so its fold would have an inside radius of zero
and the two legs would lie on one another, which no surface or solid can
represent. The fold is therefore given a very small inside radius, 0.001 in
the model's units, and an ``OPEN`` hem whose opening is smaller than twice
that uses the same. The reference shell carries this as a half-cylinder face
0.001 in radius along the fold, and the thickened part has a matching strip
0.002 wide on the inside of the fold. Both are valid geometry and survive
export and re-import; they are worth knowing about when a script walks the
faces of a hemmed part and expects every face to be sheet-sized. The flat
pattern is not affected: a fold this tight adds only its neutral-axis length
to the blank, which is what a closed hem does in practice.

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = hem(
        blank.edges().sort_by(Axis.X)[-1],
        HemType.OPEN,
        width=8,
        opening=2,
        sheet_parameters=parameters,
    )

***************
What it refuses
***************

* A keyword that does not belong to the chosen ``HemType``, or a required one
  left out.
* An ``opening`` that is not positive for ``OPEN``, and a ``roll_angle`` that
  is not positive or that turns the curl into the sheet.
* Everything a :ref:`flange <sheet_metal_flange>` refuses, since the rims are
  the same.

*******
Related
*******

* :ref:`Flange <sheet_metal_flange>` for a wall at any other angle.
* :ref:`Corner relief <sheet_metal_corner_relief>` where two hemmed walls
  meet at a corner.
