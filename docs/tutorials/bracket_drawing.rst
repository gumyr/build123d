.. _tech_drawing_tutorial:
.. _tutorial_bracket_drawing:

###################
A technical drawing
###################

A model on a screen is not always enough. A part that someone else is to
make, check or approve usually travels as a drawing: a sheet of paper with
the part seen flat from the front, the top and the side, its sizes marked,
and a title block in the corner. In this tutorial you will make that
drawing from a model, so that it never has to be drawn by hand and is
never out of date:

.. image:: /tutorials/assets/bracket_drawing/sheet_finished.svg
    :align: center
    :width: 90%

Along the way you will:

* make a drawing sheet with a border and a title block,
* turn a 3D part into the flat lines of a view with ``drawing_view``,
* arrange the standard views on the sheet so that they line up,
* show hidden edges as dotted lines,
* add dimensions and labels, and
* export the sheet as an SVG file.

It takes about twenty minutes. The part is the bracket of
:ref:`design_tutorial`, and this tutorial carries on in that file: every
step below is added to the end of it. Apart from one line in step 1, it is
the same in builder and algebra mode.

*****************
Step 1: Setup
*****************

Open the file you ended :ref:`design_tutorial` with and add two lines to
the end of it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bracket_drawing.py
            :language: build123d
            :start-after: [part_builder]
            :end-before: [part_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bracket_drawing.py
            :language: build123d
            :start-after: [part_algebra]
            :end-before: [part_algebra]

``date`` is part of Python and is used for the date in the title block.
``part`` is the finished bracket, under a name that is the same in both
modes, so that everything from here on can be too.

To look at each step as you go, show what it makes in your viewer, for
example ``show(sheet, front)``. Step 8 writes the finished sheet to a file.

*********************
Step 2: The sheet
*********************

A drawing starts with the sheet it is drawn on.
:class:`~drafting.TechnicalDrawing` makes one: a border, with letters and
numbers round the edge to refer to places on the sheet, and a title block
filled in from its arguments.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [sheet]
    :end-before: [sheet]

.. image:: /tutorials/assets/bracket_drawing/sheet_blank.svg
    :align: center
    :width: 70%

The sheet is an ordinary flat sketch on ``Plane.XY``, with the origin at
its centre. ``PageSize.A5`` makes it 210 mm by 148 mm, so one unit on the
sheet is one millimetre of paper, and the bracket, which is 50 mm long,
will be drawn at its real size. ``nominal_text_size`` and ``line_width`` are
reduced from their defaults to suit a small sheet.

*******************
Step 3: A view
*******************

A view is the part seen from somewhere, flattened onto paper.
:meth:`~topology.Mixin3D.drawing_view` makes one.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [view]
    :end-before: [view]

.. image:: /tutorials/assets/bracket_drawing/sheet_view.svg
    :align: center
    :width: 70%

The first argument is the *viewpoint*: the place the part is looked at
from. It is a place, not a direction, so it is given as the middle of the
part moved a long way along -Y, which is in front of the bracket.
``look_at=center`` aims the view at the middle of the part, so the line of
sight runs exactly along Y and the view is square-on.

Two lists of edges come back. ``visible`` are the edges that can be seen
from the viewpoint, and ``hidden`` are the ones behind the part's own
surfaces: here, the insides of the two arms. Both are flat, on
``Plane.XY``, centred on the origin, which is why the view has landed in
the middle of the sheet. In the picture the hidden edges are dotted.

**********************************
Step 4: Put the view in its place
**********************************

The sheet needs several views, each in its own place. That is worth a small
function: it takes the direction to look from and a position on the sheet,
and gives back the two lists of edges, moved there. Keep the ``center``
line of step 3 and replace the line after it with this.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [place]
    :end-before: [place]

.. image:: /tutorials/assets/bracket_drawing/sheet_front.svg
    :align: center
    :width: 70%

The function builds the viewpoint as step 3 did, a long way from the
centre in the direction asked for. ``Pos(*position) * edge`` moves an edge
across the sheet, as it would move any shape. ``up`` says which direction
of the model is to point up the page, and is the model's Z unless told
otherwise.

The first view made with it is the same front view, now towards the lower
left of the sheet.

******************************
Step 5: The other views
******************************

A drawing shows the part from three sides, and the three views are placed
by a convention, so that anyone can read them. In the convention used
here, *third-angle projection*, each view sits on the side it is seen
from: the view from the top goes above the front view, and the view from
the right goes to the right of it.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [views]
    :end-before: [views]

.. image:: /tutorials/assets/bracket_drawing/sheet_views.svg
    :align: center
    :width: 70%

* The **top** view looks down from +Z. Looking straight down, the model's
  Z cannot point up the page, so ``up=(0, 1, 0)`` puts the back of the
  bracket at the top. It has the same X position as the front view, so the
  two line up: a feature can be followed straight up from one to the
  other.
* The **right** view looks from +X and has the same Y position as the
  front view, so those two line up as well.
* The last is a view from a corner, ``(1, -1, 1)``. It is not one of the
  standard three, but it shows at a glance what the other three describe.

The hidden edges now earn their place. The hole through the arms cannot be
seen from the front or the top, and appears in both as dotted lines; the
slot appears dotted in the top and right views.

**************************
Step 6: Dimensions
**************************

A drawing says how big things are. An :class:`~drafting.ExtensionLine` is
the usual way: two thin lines carried out from the part, with an arrowed
line and a number between them.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [dimensions]
    :end-before: [dimensions]

.. image:: /tutorials/assets/bracket_drawing/sheet_dimensions.svg
    :align: center
    :width: 70%

:class:`~drafting.Draft` holds the style that all the dimensions share -
the size of the text and the arrows, and how numbers are written - so that
it is set once. ``decimal_precision=0`` and ``display_units=False`` give
plain whole numbers; the title block already says the units are
millimetres.

Each ``ExtensionLine`` is given two points to measure between and an
``offset``, which is how far, and in which direction, to stand the
dimension off from them. The points come from the bounding box of a view:
the length is measured along the bottom of the front view and set 8 mm
below it, the width up its left side, and the height up the right side of
the top view.

No number was typed in. Each dimension measures the distance between its
two points and writes that, so the drawing cannot disagree with the model.
This is also why the views are drawn at real size: a view that had been
scaled would be measured at its scaled size.

*********************
Step 7: Labels
*********************

Name the views. A label is a ``Text``, placed like any other sketch
object.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [labels]
    :end-before: [labels]

.. image:: /tutorials/assets/bracket_drawing/sheet_labels.svg
    :align: center
    :width: 70%

Each label is centred 4 mm above the bounding box of its view, so it
follows the view if the view is moved.

*********************
Step 8: Export
*********************

Everything on the sheet is a flat shape, and
:class:`~exporters.ExportSVG` writes flat shapes to an SVG file, which a
web browser will open and print.

.. literalinclude:: /tutorials/bracket_drawing.py
    :language: build123d
    :start-after: [export]
    :end-before: [export]

.. image:: /tutorials/assets/bracket_drawing/sheet_finished.svg
    :align: center
    :width: 90%

The exporter draws in *layers*, each with its own style, and every shape
is added to one of them:

* ``Sheet`` is filled with black. The border, the text and the arrows are
  all thin filled shapes, and the fill is what makes them solid.
* ``Visible`` is a medium line for the edges that can be seen.
* ``Hidden`` is a thin, grey, dotted line. The edges of the corner view
  that are out of sight are left out altogether.

``unit=Unit.MM`` makes one unit of the drawing one millimetre in the file,
so the sheet prints at its real size.

Now go to the top of the file and change ``length`` to 60. The bracket is
longer, and so is every view of it; the dimension reads 60; and nothing in
the drawing code was touched.

For a CAD program, :class:`~exporters.ExportDXF` writes a DXF file in the
same way.

********************
What you learned
********************

* :class:`~drafting.TechnicalDrawing` makes a sheet with a border and a
  title block.
* :meth:`~topology.Mixin3D.drawing_view` gives the edges of a part as seen
  from a viewpoint, flat, in two lists: visible and hidden. Aim it with
  ``look_at`` to get a square-on view.
* The views of a drawing are placed by convention and lined up with one
  another, which giving them a shared X or Y position does.
* :class:`~drafting.ExtensionLine` measures what it is given, with its
  style held in a :class:`~drafting.Draft`.
* :class:`~exporters.ExportSVG` writes the sheet to a file, with a layer
  for each style of line.
* A drawing made in code follows the model, dimensions included.

:ref:`projection_view` has more on ``drawing_view``, including perspective
views.
