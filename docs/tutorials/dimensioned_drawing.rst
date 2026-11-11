.. _tutorial_dimensioned_drawing:

##########################
From a drawing to a sketch
##########################

Sooner or later a part arrives as a drawing: an outline with its dimensions
marked on it. The drawing was made by someone using a graphical CAD program,
who sketched the shape roughly and then added dimensions and *constraints* -
this arc is tangent to that line - until a solver had enough to fix every
point. In this tutorial you will turn this drawing into a build123d sketch:

.. image:: /tutorials/assets/constraints/complex_sketch.png
    :align: center
    :width: 70%

build123d has no solver of that kind. Each line is given exactly when it is
made, as in :ref:`tutorial_drawing_outlines`. A drawing like this one does
not give every point, though, and the tutorial is about what to do where it
does not. Along the way you will:

* read a drawing for what it tells you and what it leaves out,
* draw *construction geometry*: lines that help and are then left out,
* make an arc tangent to a line and passing through a point,
* draw a line that runs until it meets something,
* make an arc tangent to two things, and choose between the answers, and
* check the finished sketch against the drawing.

It takes about thirty minutes. It uses ``@``, ``make_face`` and the
``BuildLine`` inside ``BuildSketch`` arrangement of
:ref:`tutorial_drawing_outlines`, and follows the advice of
:ref:`design_tutorial`. How the builder and algebra tabs on this page work
is described in :ref:`tutorial_sketch_then_extrude`.

****************************
Step 1: Read the drawing
****************************

Before writing anything, go round the outline and sort it into what the
drawing states and what it leaves for you to work out.

Most of this outline is stated. The left end is a block 32 high with three
7 mm corners cut off; the top right is a flat 29 long with a 5 mm corner and
a side 24 high; the sloping side runs from the bottom of that to a point 29
in from the right, on the bottom edge. Every one of those corners can be
written down as a pair of coordinates.

Three places cannot, and each is marked on the drawing by a tangent symbol,
the circled mark with a line through it:

#. **The R19 arc along the top.** It ends at the left end of the top flat
   and is tangent to the line sloping at 10°. Where it meets that line is
   not given.
#. **The R29 arc at the bottom.** Its centre is marked with a cross, on the
   sloping side and 19 above the bottom edge. Where it starts and stops is
   not given, and so neither is the length of the short flat it runs from.
#. **The R5 arc.** It is tangent to the R29 arc and to the bottom of the
   left-hand block. Neither its centre nor its ends are given.

Those three are the work of this tutorial. In each, the drawing gives a
relationship in place of a position, and build123d has an object that takes
the relationship and finds the position.

Last, choose the origin. The centre of the hole is a good place: the
drawing measures from it in both directions, and the hole then needs no
positioning at all.

*******************************
Step 2: Name the dimensions
*******************************

Start a new Python file with the import and the numbers on the drawing, in
millimetres.

.. literalinclude:: /tutorials/dimensioned_drawing.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The first block is the drawing, copied. Two things in it need a word:

* ``foot_drop`` is the 19 at the bottom left, the distance the part goes
  on below the left-hand block. The 19 at the bottom right, the height of
  the R29 centre, is the same distance, so one name serves for both.
* ``foot_inset`` is the 29 along the bottom, and ``top_flat`` the 29 along
  the top. They are equal on this drawing, but they are different
  dimensions, so they have different names.

The second block turns those numbers into the six levels that the drawing
is measured between: the ``left`` and ``right`` of the part, its ``top`` and
``bottom``, and the top and bottom of the left-hand block, called the
``lobe`` here. All six are measured from the hole. With them, a corner of
the drawing reads the way the drawing does - ``(right - top_flat, top)`` is
"29 in from the right, on the top edge" - and no arithmetic with bare
numbers appears anywhere below.

As before, each step below shows the whole of the rest of the file as it
stands at that point.

***********************************************
Step 3: Start where the drawing is complete
***********************************************

Draw what is fully stated first. It gives the unknown pieces something to
be tangent to and to end on. The top flat, its corner and the right side
are one ``Polyline``, and the sloping side is a ``Line`` from where that
ends.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [known_builder]
            :end-before: [known_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [known_algebra]
            :end-before: [known_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_known.svg
    :align: center
    :width: 55%

In this picture and the ones that follow, the finished outline is shown in
grey so that you can see where each piece belongs. What the step adds is in
red, and its ends are marked.

**************************************************************
Step 4: An arc tangent to a line and through a point
**************************************************************

Now the first gap. The R19 arc must end at the left end of the top flat,
which is ``top_right @ 0``, and must be tangent to the 10° line. The line
starts above the hole, at ``(0, lobe_top)``, but how far it goes depends on
the arc, which is the thing being looked for.

So draw the line longer than it can possibly need to be, as *construction
geometry*: something drawn to be measured against, and not part of the
outline. Then ask for the arc.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [top_arc_builder]
            :end-before: [top_arc_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [top_arc_algebra]
            :end-before: [top_arc_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_top_arc.svg
    :align: center
    :width: 55%

:class:`~objects_curve.PolarLine` draws a line from a point, of a given
length, at a given angle: here 50 long and 10° below the X axis. Its name
starts with ``c_`` to mark it as construction, a convention used for the
rest of this page. It is the dashed line in the picture.

In builder mode, ``mode=Mode.PRIVATE`` makes the line without adding it to
the ``BuildLine``, so it can be used and will not end up in the outline. In
algebra mode nothing is collected automatically, so there is nothing to
switch off: the line is simply never handed to ``make_face``.

:class:`~objects_curve.ConstrainedArcs` is the new object. It is given the
things the arc must satisfy and works out the arc:

* a line or arc, such as ``c_slope``, means *be tangent to this*;
* a point, such as ``top_right @ 0``, means *pass through this*; and
* ``radius`` fixes the size.

The arc it returns starts where it touches the construction line and ends
at the point. ``top_arc @ 0`` is therefore the answer to the question the
drawing left open: where the sloping line stops. It is used in step 7.

*****************************************************
Step 5: A line that runs until it meets something
*****************************************************

The second gap is at the bottom. The short flat there starts at the end of
``slant`` and runs left until it reaches the R29 arc. The arc's centre is
on ``slant``, level with the bottom of the lobe.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [foot_builder]
            :end-before: [foot_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [foot_algebra]
            :end-before: [foot_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_foot.svg
    :align: center
    :width: 55%

Four lines, and three of them are construction:

* ``c_base`` is a line along the bottom of the lobe, right across the part.
* ``slant.intersect(c_base)`` finds where the two cross. It returns a list,
  because two shapes can cross in more than one place, and ``[0]`` takes
  the only entry: the centre of the R29 arc.
* ``c_neck`` is an arc of that radius about that centre. As with
  ``c_slope``, it is drawn longer than needed - 50° of it, starting from
  180°, the direction pointing left - because where it should stop is not
  yet known.
* ``foot`` is the one line that is kept. It is a ``PolarLine`` again, with
  a difference: its ``length`` is not a number but ``c_neck``. Given a
  shape for its length, a ``PolarLine`` goes in its direction until it
  meets that shape, and stops there.

"Go this way until you reach that" is one of the commonest things a
drawing says without saying it, and it needs no calculation here.
``CenterArc`` and several other arcs accept a shape for their ``arc_size``
in the same way.

***************************************************************
Step 6: An arc tangent to two things, and a choice
***************************************************************

The third gap is the R5 arc that joins the R29 arc to the bottom of the
lobe. It is tangent to both, and both already exist as construction:
``c_neck`` and ``c_base``. So this is ``ConstrainedArcs`` again, with two
tangencies and a radius.

There is a catch. Ask for a circle of radius 5 that touches both and there
are two answers:

.. image:: /tutorials/assets/dimensioned_drawing/lever_candidates.svg
    :align: center
    :width: 45%

Both circles touch the dashed line and the dashed arc. One sits outside the
R29 arc and one inside it, and nothing in the request says which is wanted.
This is normal for tangent constructions, and it is not an error:
``ConstrainedArcs`` finds every answer, and you say which to keep.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [neck_builder]
            :end-before: [neck_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [neck_algebra]
            :end-before: [neck_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_neck.svg
    :align: center
    :width: 55%

The ``selector`` is a function that is handed all the answers and returns
the ones to keep. The answers arrive as a list of the kind that
:ref:`tutorial_selecting_and_finishing` works with, so they are chosen in
the same way: ``arcs.sort_by(Axis.X)[0]`` puts them in order along X and
takes the first, the one further left. On the drawing, that is the one
outside the R29 arc.

Choose by position, as here, and not by counting - ``arcs[0]`` would also
have run, and would have meant "whichever the kernel happened to find
first".

The R29 arc can now be finished, because both of its ends are known: it
starts where ``foot`` ends and stops where ``small_arc`` begins.
``c_neck.trim(...)`` returns the piece of the construction arc between
those two points. In builder mode :func:`~operations_generic.insert` adds
that piece to the outline, which is needed because ``trim`` is a method of
the arc and does not add its result itself.

.. note::

    Tangent arcs can also be narrowed down before they are made, by saying
    whether the answer should be outside or should enclose each thing it
    touches, and whether the short or the long way round is wanted.
    :ref:`constrained_arcs_and_lines` describes these, and
    :ref:`constraints_explained` discusses why build123d works this way.

*******************************
Step 7: Close the outline
*******************************

Everything that was missing has been found. What remains is the lobe, and
all of its corners are stated on the drawing. It is one ``Polyline`` that
starts at the end of the R5 arc, goes round the three cut corners to the
point above the hole, and then down the 10° slope to the point found in
step 4.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [lobe_builder]
            :end-before: [lobe_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [lobe_algebra]
            :end-before: [lobe_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_lobe.svg
    :align: center
    :width: 55%

The first and last points of the ``Polyline`` are ``small_arc @ 1`` and
``top_arc @ 0``. Neither is a number you could have typed, and the outline
closes on both exactly.

The 10° slope is drawn here without mentioning the angle. Its two ends are
both on ``c_slope``, so it has the right slope because of how its ends were
found.

******************************************
Step 8: Make the face and check it
******************************************

The outline becomes a face as in :ref:`tutorial_drawing_outlines`, and the
hole is a circle at the origin, where step 1 put it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [face_builder]
            :end-before: [face_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/dimensioned_drawing.py
            :language: build123d
            :start-after: [face_algebra]
            :end-before: [face_algebra]

.. image:: /tutorials/assets/dimensioned_drawing/lever_face.svg
    :align: center
    :width: 55%

In builder mode the construction lines were private, so ``make_face()``
sees only the seven pieces of the outline. In algebra mode the same seven
are listed by name.

A drawing gives you a way to check your work, because it has dimensions
that were never used. The last line prints the size of the sketch:

.. code-block:: text

    Vector: (X=81, Y=57, Z=0)

81 is on the drawing and went in as ``overall_width``. 57 also went in, but
only to place the top edge; that the part really is 57 high, down to the
flat that was found by running into an arc, is confirmation that the
outline was read correctly.

.. tip::

    If you use the `ocp-vscode
    <https://github.com/bernhard-42/vscode-ocp-cad-viewer>`_ viewer, its
    ``ImageFace`` puts a picture into the scene as a flat face. Scaled and
    positioned so that it lies under the sketch, the drawing itself becomes
    something to trace over and compare with as you go:

    .. code-block:: build123d

        from ocp_vscode import ImageFace, show

        drawing = ImageFace(
            "complex_sketch.png",
            scale=29 / 264,
            origin_pixels=(297, 390),
            location=Location((0, 0, -0.1)),
        )
        show(drawing, lever)

    ``scale`` is millimetres per pixel - here a 29 mm dimension measured
    264 pixels on the image - and ``origin_pixels`` is the pixel that
    should sit at the origin, the centre of the hole.

The sketch is finished, and it is an ordinary sketch: ``extrude`` it, as in
:ref:`tutorial_sketch_then_extrude`, to make the part.

Try a ``slope_angle`` of 15, a ``top_radius`` of 25 or a ``neck_fillet`` of
8 at the top of the file. The tangent points move, the outline still
closes, and the sketch is still 81 by 57.

********************
What you learned
********************

* Read a drawing for what it states and what it only relates. Draw what is
  stated first.
* **Construction geometry** is drawn to be measured against and left out of
  the result: ``mode=Mode.PRIVATE`` in builder mode, and simply not used in
  algebra mode. Draw it longer than it needs to be.
* :class:`~objects_curve.ConstrainedArcs` makes an arc from what it must be
  tangent to, what it must pass through, and its radius.
* A tangent construction often has several answers. A ``selector`` chooses
  among them, and should choose by position.
* A :class:`~objects_curve.PolarLine` given a shape for its ``length`` runs
  until it meets that shape.
* ``intersect`` finds where two lines cross, and ``trim`` cuts a line or
  arc down to the piece between two points.
* Use a dimension the drawing gives and you did not need as a check.

:ref:`drawing_with_constraints` has shorter recipes for these and for other
relationships a drawing can state: perpendicular, a constant distance, a
smooth join between two curves.
