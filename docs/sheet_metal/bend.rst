.. _sheet_metal_bend:

####
Bend
####

A bend folds material the sheet already has. Where a :ref:`flange
<sheet_metal_flange>` adds a wall beyond a free edge, ``bend`` takes a blank
that has been cut to its outline, with the fold marked as a line across it, and
folds it there. This is how a fabricator works from a flat pattern: cut the
blank, then bend along the lines.

.. image:: ../assets/sheet_metal/bend_before.svg
    :align: center

.. image:: ../assets/sheet_metal/bend_basic.svg
    :align: center

.. literalinclude:: ../sheet_metal_examples.py
    :language: build123d
    :start-after: [bend_basic]
    :end-before: [bend_basic]

*********************
Marking the fold line
*********************

A blank has to carry the fold line as a real edge before it can be folded
along one, which means the blank is a shell of two coplanar flats meeting on
the line rather than a single face. The ``fold_lines()`` selector returns
exactly those edges. The example above gets its line by splitting the blank;
a blank imported with its fold lines already drawn works the same way.

********************
Which side stays put
********************

A fold line lies between two flats, so which of them stays where it is and
which swings is the one thing the line cannot say on its own. The way the line
was selected answers it: a line picked off a face, as
``sheet.flats().sort_by(Axis.X)[0].fold_lines()[0]`` does, records that face,
and ``bend`` holds that face still while everything on the far side of the
line swings through the angle, carrying whatever is attached to it.

A line taken straight off the sheet with ``sheet.edges()`` is refused rather
than guessed at, because both of its faces are equally its own. Select it
through the face you want to keep still.

******************
Angle and position
******************

The angle is signed, positive toward the face normal, the same as for a
flange. As it rolls up the bend takes a strip of the sheet with it, as wide as
the bend allowance, so that :ref:`unfold <sheet_metal_unfold>` gives back the
blank the part was drawn as. ``position`` says where that strip sits relative
to the line, with the same choices as a flange's :ref:`bend position
<sheet_metal_bend_position>`: ``BEND_OUTSIDE`` puts all of it past the line
and leaves the fixed face untouched, ``CENTER`` straddles the line, and the two
corner positions put the inside or outside corner of the formed part on it.

Whatever the blank's outline does across that strip, a taper, a corner round,
a notch, a hole, rolls into the bend with it, so the strip need not be the
same width at both ends.

************
Algebra mode
************

.. code-block:: build123d

    parameters = SheetMetalParameters(thickness=1, bend_radius=2)
    blank = Shell.make_sheet(
        [(Pos(-30, 0) * Rectangle(20, 40)).face(), (Pos(10, 0) * Rectangle(60, 40)).face()]
    )
    line = blank.flats().sort_by(Axis.X)[0].fold_lines()[0]
    sheet = bend(line, angle=90, sheet_parameters=parameters)

***************
What it refuses
***************

* A line not selected through a face, as above.
* A line that is not shared with a coplanar flat: a line already at a bend
  cannot be bent again, and a rim has no material beyond it to fold. Use a
  flange for a rim.
* Too little sheet: past the line for the bend allowance, or before it for the
  setback a set-back ``position`` asks for.
* Material that reaches round to both sides of the line, as a closed loop of
  faces would, since that fold would tear the sheet rather than carry it.

The sheet is not checked for running into itself, so a large angle on a blank
with other features can fold one part through another.

*******
Related
*******

* :ref:`Jog <sheet_metal_jog>` is two opposite bends along a line, stepping
  the far side sideways.
* :ref:`Flange <sheet_metal_flange>` adds a wall instead of folding the
  existing sheet.
