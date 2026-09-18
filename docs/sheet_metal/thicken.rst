.. _sheet_metal_thicken:

#######
Thicken
#######

A sheet is a surface until it is given material. :func:`~operations_part.thicken`
turns the reference shell into a solid ``Part`` by giving it the sheet
thickness where the :ref:`reference surface <sheet_metal_concepts>` says the
material is: entirely to one side of the shell for ``INSIDE`` and ``OUTSIDE``,
straddling it for ``MID`` and ``NEUTRAL``. The result is the part you export,
measure, assemble with others, or subtract from.

.. image:: ../assets/sheet_metal/thicken_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [thicken_basic]
    :end-before: [thicken_basic]

*******************
Nested in BuildPart
*******************

A ``BuildSheet`` nested in ``BuildPart`` publishes its finished shell and its
parameters to the part builder as pending input when the context exits. A
bare ``thicken()`` then consumes them, so the parameters are given once, on
the ``BuildSheet``. The part builder's ``mode`` applies as usual, so a sheet
part can be added to, subtracted from, or intersected with what the
``BuildPart`` already holds.

``BuildSheet`` has no ``part`` of its own. Its results are ``tray.sheet``, the
placed reference ``Shell``, and ``tray.sheet_local`` before the builder's
output placement, together with ``tray.sheet_parameters``.

**************
Standing alone
**************

Outside ``BuildPart`` the same call takes the shell and the parameters
explicitly:

.. code-block:: build123d

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(60, 40)
        flange(tray.rims(), length=15, gaps=3.1)

    part = thicken(tray.sheet, sheet_parameters=tray.sheet_parameters)

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = flange(blank.edges(), length=15, gaps=3.1, sheet_parameters=parameters)
    part = thicken(sheet, sheet_parameters=parameters)

******************
Brake-formed parts
******************

:func:`~operations_part.make_brake_formed` is an older, independent
``BuildPart`` operation that sweeps a section along a path of straight lines
to make a folded part directly, without a reference shell. It has no bend
allowance, relief or unfolding, so it suits a quick bracket whose flat pattern
is not needed. ``BuildSheet`` is not the context for it.

*******
Related
*******

* :ref:`Unfold <sheet_metal_unfold>` is the other way out of the model.
* The :ref:`tutorial <sheet_metal_tutorial>` thickens an enclosure and unfolds
  it in its last two steps.
