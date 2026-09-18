.. _sheet_metal_jog:

###
Jog
###

A jog steps the sheet sideways: a bend, a short straight run, and a bend back
the other way, leaving the far side parallel to where it was but offset from
it. Fabricators use one to let a panel sit flush over a neighbour, to clear a
weld or a fastener head, or to stiffen a long flat with a step. It is two
bends made as one feature so that the step comes out at the right height.

.. image:: ../assets/sheet_metal/jog_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [jog_basic]
    :end-before: [jog_basic]

****************
Offset and angle
****************

``offset`` is the size of the step, measured between the reference surfaces of
the two flats, which is the same face of the sheet on either side of the jog.
Its sign says which way to step, positive toward the face normal.

``angle`` is how steeply the run climbs: 90 for a square step, less for a
sloping one. The two bends between them climb ``(r1 + r2)(1 - cos angle)``
and the straight run makes up the rest, so a jog needs at least that much
offset; a shallower angle needs less.

.. image:: ../assets/sheet_metal/jog_profile.svg
    :align: center

Both bends take their allowance of the blank, and ``position`` places the
first bend on its line the way it does for a :ref:`bend <sheet_metal_bend>`,
so :ref:`unfold <sheet_metal_unfold>` gives the blank back.

***********************
On a fold line or a rim
***********************

Given a **fold line**, selected through the face that stays as ``bend`` takes
it, the material on the far side of the line steps across and carries on
parallel to where it was, taking whatever is attached to it along. No
``length`` is taken, since the material is already there.

Given a **rim**, a free edge as ``flange`` takes it, the jog is a stepped
flange: new material steps off the edge and runs on for ``length`` in the
plane of the face it came from. ``gaps`` trim the bend ends the way they do
for a flange.

.. image:: ../assets/sheet_metal/jog_rim.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [jog_rim]
    :end-before: [jog_rim]

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Rectangle(60, 40)
    sheet = jog(
        blank.edges().sort_by(Axis.X)[-1],
        offset=10,
        length=15,
        sheet_parameters=parameters,
    )

***************
What it refuses
***************

* An offset smaller than the two bends alone climb at the given angle, and
  an angle outside ``(0, 180)``.
* ``length`` or ``gaps`` on a fold line, where there is no new material to
  size, and a missing ``length`` on a rim.
* A fold line not selected through a face, and a mix of fold lines and rims
  in one call.
* Everything a :ref:`bend <sheet_metal_bend>` refuses, since a jog is two of
  them.

*******
Related
*******

* :ref:`Bend <sheet_metal_bend>` for a single fold along a line.
* :ref:`Flange <sheet_metal_flange>` for a wall off a rim without the step.
