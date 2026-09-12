.. _sheet_metal_flange:

######
Flange
######

A flange is a wall folded up from the edge of the sheet. In the shop it is the
most common feature there is: the sides of a tray, the lips of a bracket, the
return on a panel that gives it stiffness. Making one adds two faces to the
model, the cylindrical **bend** and the flat **wall** beyond it.

.. image:: ../assets/sheet_metal/flange_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [flange_basic]
    :end-before: [flange_basic]

``flange`` takes one or more **rims**, the free edges of the sheet's flats,
and the ``length`` of the wall. Rims come from ``tray.rims()``, or from the
edges of a selected flat. The wall stands on the edge and reaches ``length``
past the bend.

*******************
Angle and direction
*******************

The angle is signed. Positive angles fold toward the normal of the face the
edge belongs to, which for a blank drawn on ``Plane.XY`` is up; negative
angles fold the other way. Anything short of a full fold is allowed, so an
angle of 45 gives a sloping wall and 90 a square one.

.. image:: ../assets/sheet_metal/flange_angle.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [flange_angle]
    :end-before: [flange_angle]

The bend's inside ``radius`` defaults to the sheet's ``bend_radius`` and can
be given per flange.

****
Gaps
****

Two flanges folded from edges that meet at a corner would collide as they fold.
``gaps`` trims the bend and wall back from the ends of the edge so neighbours
clear each other. A single value applies to both ends; a pair gives the start
and end of the edge separately. The gap has to be at least the sheet
thickness, and slightly more leaves the corner comfortable to form.

.. image:: ../assets/sheet_metal/flange_gaps.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [flange_gaps]
    :end-before: [flange_gaps]

Gaps leave each bend stopping short of the edge of the blank, and the corner
between two of them is where :ref:`corner relief <sheet_metal_corner_relief>`
goes. A flange narrower than its edge, with large gaps, leaves the face
keeping the rest of its edge as tabs beside the bend.

.. _sheet_metal_bend_position:

*******************
Where the bend sits
*******************

By default the bend *starts* at the edge: everything the flange adds lies
past it, and the face keeps its full drawn size as the flat before the bend.
That is ``BendPosition.BEND_OUTSIDE``, and it is the natural choice when the
face was drawn to its tangent line, the size of flat it will actually have.

A drawing more often dimensions to the corner the formed part will have. The
other positions set the bend back onto the face so that a chosen feature of
the formed bend lands on the edge, with the face giving up a strip of material
to the bend as it rolls up:

.. image:: ../assets/sheet_metal/flange_position.svg
    :align: center

=====================  ========================================================
Position               What lands on the edge
=====================  ========================================================
``BEND_OUTSIDE``       The bend's tangent line: the whole bend lies past the
                       edge. The default.
``MATERIAL_INSIDE``    The inside corner of the formed part, where the inner
                       faces of base and wall would meet if folded sharp.
``MATERIAL_OUTSIDE``   The outside corner of the formed part.
``CENTER``             The middle of the bend, which straddles the edge.
=====================  ========================================================

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [flange_position]
    :end-before: [flange_position]

Only the bend's own span between the gaps is taken from the face; beside it,
the face keeps its edge as tabs that still reach the corner it was drawn to.
Where two flanged edges meet, each bend's strip would take material the other
needs, so the gaps there have to be wider than the setback. The two corner
positions are undefined at 180 degrees, where the faces never meet.

********************
How long the wall is
********************

``length`` is the flat wall by default, measured from the bend's tangent line.
A drawing usually gives the overall size instead, to a virtual sharp, and
``length_mode`` takes it that way so the trigonometry is left to the flange:

.. image:: ../assets/sheet_metal/flange_length.svg
    :align: center

=================  ============================================================
Length mode        ``length`` is measured from
=================  ============================================================
``TANGENT``        The bend's tangent line: the length is the flat wall alone.
                   The default.
``INNER_SHARP``    The corner the extended inner faces make.
``OUTER_SHARP``    The corner the extended outer faces make: the overall
                   outside size a drawing gives.
=================  ============================================================

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [flange_length]
    :end-before: [flange_length]

With ``position`` placing one corner on the edge and ``length_mode`` measuring
to the other, a part can be modelled straight from its drawing dimensions. The
worked example under :ref:`dimensioning <sheet_metal_dimensioning>` shows a
channel drawn with its outside sizes.

************
Algebra mode
************

The same call takes the edges of a blank face or of a sheet and returns the
new ``Shell``. The parameters are passed explicitly:

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(
        blank.edges().sort_by(Axis.X)[-1], length=15, sheet_parameters=parameters
    )
    sheet = flange(sheet.rims().sort_by(Axis.X)[0], length=15, sheet_parameters=parameters)

***************
What it refuses
***************

* An edge that is not a straight free rim of a flat. A bend's edge, a fold
  line shared with another flat, or a curved outline edge cannot be flanged.
* A ``sheet_parameters`` argument inside ``BuildSheet``, or a missing one
  outside it.
* Gaps that leave no edge to bend, and set-back positions whose strip would
  reach past the face.

*******
Related
*******

* :ref:`Hem <sheet_metal_hem>` is a flange folded all the way back onto the
  sheet.
* :ref:`Jog <sheet_metal_jog>` on a rim is a stepped flange.
* :ref:`Bend <sheet_metal_bend>` folds material the blank already has,
  instead of adding a wall.
* :ref:`Miter <sheet_metal_miter>` angles the sides of the wall a flange made.
