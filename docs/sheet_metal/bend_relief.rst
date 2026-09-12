.. _sheet_metal_bend_relief:

###########
Bend relief
###########

A bend that stops partway along an edge, a flange narrower than the sheet it
folds from, leaves a corner where the sheet has to fold on one side of the
fold line and stay flat on the other. Formed like that the material tears at
the end of the bend, and the tear runs into the flat. **Bend relief** notches
the sheet beside the end of the bend so the fold line ends on a free edge
instead. Any partial-width flange or tab needs it.

.. image:: ../assets/sheet_metal/bend_relief_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [bend_relief_basic]
    :end-before: [bend_relief_basic]

``bend_relief`` takes the **bend faces** themselves, from ``tray.bends()``,
and relieves both ends of each. An end that already runs out to the edge of
the blank needs nothing and is left alone, so a selection acts as a filter:
give it every bend and only the ones that stop inside the sheet are notched.

**********
The shapes
**********

The shape is named by ``ReliefType``, the same enum :ref:`corner relief
<sheet_metal_corner_relief>` uses, and like those it is cut in the flat
pattern so it keeps its shape on the blank:

.. image:: ../assets/sheet_metal/bend_relief_types.svg
    :align: center

=============  ================================================================
Shape          What it is and when to use it
=============  ================================================================
``SQUARE``     A square-cornered notch beside the bend, ``depth`` past the
               fold line and ``width`` across. The usual laser-cut relief.
``OBROUND``    The same notch with a rounded far end. Kinder to the material
               than a square notch, since the round spreads the stress.
``ROUND``      A hole of ``radius`` centred on the end of the fold line. It
               shortens the bend as well as notching the sheet beside it, and
               is the choice for punched blanks.
=============  ================================================================

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [bend_relief_types]
    :end-before: [bend_relief_types]

``CONSTANT_WIDTH`` is not accepted here: it continues the gap two flanges
leave, so it is only defined where two of them meet.

*************
Default sizes
*************

Sizes left out follow the usual shop rule, measured from the fold line: the
relief reaches the bend radius plus one thickness into the sheet and is one
thickness wide. ``SQUARE`` and ``OBROUND`` take that pair as ``depth`` and
``width``. ``ROUND`` takes a ``radius`` that also sets how far the hole
reaches past the bend end, so it defaults to one thickness rather than to the
notches' reach, and it has to fit in the sheet left past the bend end.

*****************************
Bend relief or corner relief?
*****************************

The two divide on how many fold lines run through the site: one at a bend
end, two at a corner. Where flange gaps leave a corner open, both bends stop
inside the sheet, so both ends want relief and their notches overlap, and
between them they would cut the corner of the sheet loose. ``bend_relief``
reports that rather than doing it. That corner belongs to
:ref:`corner relief <sheet_metal_corner_relief>`, which opens it in a single
cut.

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(
        blank.edges().sort_by(Axis.X)[-1], length=15, gaps=8, sheet_parameters=parameters
    )
    sheet = bend_relief(sheet.bends(), ReliefType.SQUARE, sheet_parameters=parameters)

***************
What it refuses
***************

* A face that is not a bend of the sheet.
* ``CONSTANT_WIDTH``, and any keyword that does not belong to the chosen
  shape.
* A relief that would cut a corner of the sheet loose, as at a flange corner,
  or a round relief too large for the sheet past the bend end.

*******
Related
*******

* :ref:`Corner relief <sheet_metal_corner_relief>` where two bends meet.
* :ref:`Flange <sheet_metal_flange>` gaps are what make a bend stop inside
  the sheet.
