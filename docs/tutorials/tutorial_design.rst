.. _design_tutorial:

################
Designing a Part
################

The tutorials before this one each taught a technique on a part that was
chosen to suit it. A real part arrives the other way round: you have a
drawing, or an object in your hand, and have to decide how to build it.

This page is a way of making those decisions. It is a checklist of eleven
steps to go through before and while you write the code, and it follows one
rule throughout: work in the lowest dimension you can - lines before
sketches, sketches before solids. As an example, it goes through the design
of this bracket:

.. image:: /tutorials/assets/design/bracket_hand_drawing.jpg
    :align: center

Each step gives the general advice first and then applies it to the
bracket. Not every step produces code, and for a given part some steps
produce nothing at all. How the builder and algebra tabs on this page work
is described in :ref:`tutorial_sketch_then_extrude`.

**********************************************************
Step 1: Examine the part in all three orientations
**********************************************************

Start by picturing the part from the front, the top and the side. Look for
symmetry in each view. A plane of symmetry halves the work: only one side
has to be designed, and the other is a mirror image of it.

The bracket has two planes of symmetry, so only a quarter of it needs to be
designed.

.. image:: /tutorials/assets/design/bracket_with_symmetry.png
    :align: center

**********************************************
Step 2: Identify rotational symmetries
**********************************************

Look for anything that could be made by turning a flat shape round an axis:
cylinders, cones, spheres, or any feature that could have come off a lathe.
Note where the axis is. These features are made with ``revolve``, described
in :ref:`tutorial_beyond_extrude`.

The bracket has none.

******************************************
Step 3: Select a convenient origin
******************************************

Choose the origin so that as little as possible has to be moved later. The
best place is usually where the planes of symmetry meet, or a point that
other parts will be measured from.

For the bracket, the origin goes where the two planes of symmetry from
step 1 cross, on its front face. The sketch will be drawn on ``Plane.XY``,
the default, so the X axis runs across the front of the bracket and the Z
axis runs along its width. All planes in build123d follow the
`right-hand rule <https://en.wikipedia.org/wiki/Right-hand_rule>`_, which
fixes the direction of Y.

.. image:: /tutorials/assets/design/bracket_with_origin.png
    :align: center

**********************************
Step 4: Name the dimensions
**********************************

Before drawing anything, give every dimension a name. A part written in
terms of names can be resized by changing one number, and can be turned
into a family of parts later. A number typed into the middle of the code
cannot.

The bracket has eight dimensions, in millimetres. They start its file:

.. literalinclude:: /tutorials/tutorial_design.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

Each step below that has code shows the whole of the rest of the file as it
stands at that point.

Dimensions need not be the only parameters. :ref:`tutorial_parametric_part`
describes a part by what it has to do and calculates its size from that.

**********************************
Step 5: Create 2D profiles
**********************************

Draw the flat shapes the part is made from, each on the plane it belongs
to. A profile is very often a cross-section of the part. Draw only the
piece that is unique, and mirror it across the planes of symmetry found in
step 1.

This is where most of the design is done. A shape that can be put into the
sketch should be, for the reasons given in
:ref:`tutorial_combining_solids`.

The profile of the bracket is this:

.. image:: /tutorials/assets/design/bracket_sketch.png
    :align: center

Only half of it is drawn - a base, a rounded corner and one arm - and that
half is drawn as a single line down its outer side, which is then given
thickness.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [profile_builder]
            :end-before: [profile_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [profile_algebra]
            :end-before: [profile_algebra]

* ``FilletPolyline`` draws straight lines through the points it is given,
  like the ``Polyline`` of :ref:`tutorial_beyond_extrude`, and rounds each
  corner between them to ``bend_radius``.
* ``offset`` makes a copy of that line ``thickness`` to its left and joins
  the two at their ends, giving a closed outline. This is the ``offset`` of
  :ref:`tutorial_sketch_then_extrude`, used on a line instead of a shape.
* ``make_face`` fills the outline in, as in
  :ref:`tutorial_drawing_outlines`.
* ``mirror`` reflects the half in ``Plane.YZ`` to make the whole profile,
  as in :ref:`tutorial_beyond_extrude`.

Drawing the centre line of a bent strip and thickening it is much less work
than drawing both sides of it, and the two sides cannot disagree.

******************************************************
Step 6: Use extrusion for prismatic features
******************************************************

Where the part has the same cross-section all the way along, extrude the
profile. A part may need several extrusions, in different directions or of
different lengths.

An extrusion does not have to be given a length. With ``until=Until.NEXT``
or ``until=Until.LAST`` it carries on until it meets another shape - the
rest of the part, or a ``target`` you name - and ends on that shape's
surface, whatever its form. Use this where a feature has to reach
something, so that it still reaches it when the dimensions change.
:ref:`Example 36 <ex 36>` shows it.

The bracket is its profile extruded, and the second plane of symmetry is
used here: the profile is extruded by half the width and the result is
mirrored.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [extrude_builder]
            :end-before: [extrude_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

In builder mode the sketch now sits inside a ``BuildPart``, and ``mirror``
with nothing named reflects the part so far. Mirroring in ``Plane.XY`` puts
the origin at the middle of the bracket's width, where step 3 said it
should be.

******************************************
Step 7: Generate revolved features
******************************************

Make any feature found in step 2 by revolving its profile about its axis,
and join it to, or cut it from, the rest of the part.

The bracket has no revolved features.

***********************************************
Step 8: Combine sub-parts intelligently
***********************************************

A complicated part is often easier to build as several simpler pieces that
are then added together, cut from one another or intersected. Do as much of
that combining as you can in a sketch, and combine solids only for what a
sketch cannot express. Combining solids is much harder work for the CAD
kernel than combining flat shapes, and more likely to fail;
:ref:`tutorial_combining_solids` explains why.

The bracket is a single piece. Further pieces could be made in the same way,
by adding more sketches and extruding or revolving them.

******************************************
Step 9: Apply chamfers and fillets
******************************************

Leave chamfers and fillets on the solid until its main shape is finished.
Use selectors to pick out the edges, and look at what a selector has found
before using it. :ref:`tutorial_selecting_and_finishing` covers both.

The back corners of the bracket are to be rounded, which needs the four
short edges at the ends of its arms.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [fillet_builder]
            :end-before: [fillet_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [fillet_algebra]
            :end-before: [fillet_algebra]

Read the selector from left to right. ``bracket.edges()`` is every edge of
the bracket. ``filter_by(Axis.X)`` keeps the ones that run in the X
direction. ``group_by(Axis.Y)`` gathers those into groups by how far along
Y they are, and ``[-1]`` takes the last group, the edges furthest back.

The selection is given a name, ``corners``, before it is used. That is the
habit recommended in :ref:`tutorial_selecting_and_finishing`: with a name,
the selection can be counted and shown on its own if the fillet does not
come out as expected.

**********************************
Step 10: Design for assembly
**********************************

If the part connects to others, add the holes, slots and other features
that make the connection, and place them from the faces they belong to so
that they stay in the right place when the part changes.

The bracket has a hole in each arm and a slot in its base.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [holes_builder]
            :end-before: [holes_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/tutorial_design.py
            :language: build123d
            :start-after: [holes_algebra]
            :end-before: [holes_algebra]

.. image:: /tutorials/assets/design/bracket.png
    :align: center

Both features start from a selected face, as in
:ref:`tutorial_selecting_and_finishing`.

* The face furthest along X is the outside of one arm. A ``Hole`` created
  there is centred on the face and cuts inwards. In builder mode it is
  given no depth and so goes all the way through the part, which takes it
  through the other arm as well: one ``Hole`` makes both holes. In algebra
  mode it is given ``depth=length`` to do the same.
* The face with the lowest Y is the front of the base. A ``SlotOverall`` is
  sketched on it and extruded by ``-thickness``, the negative amount
  sending it into the part, and ``Mode.SUBTRACT`` (``-=`` in algebra mode)
  cuts it out.

Holes like these can also carry *joints*, which let parts be connected to
one another in code. :ref:`joint_tutorial` introduces them.

****************************************
Step 11: Test fit and tolerances
****************************************

Look at the part in the assembly it is meant for. Allow for how it will be
made: clearance between parts that move, and shrinkage or over-sized
features for a 3D-printed part. Because the dimensions have names, an
allowance can be one more name, added where it is needed.

***********
Summary
***********

The eleven steps, in short:

#. Look at the part from three sides and find its symmetry.
#. Find anything that is a shape turned round an axis.
#. Put the origin where it saves the most work.
#. Name every dimension.
#. Draw the 2D profiles, mirroring where you can.
#. Extrude what is prismatic.
#. Revolve what is round.
#. Combine pieces in the sketch where possible, as solids where necessary.
#. Add chamfers and fillets last, by selecting edges.
#. Add what connects the part to others, placed from its faces.
#. Check the fit and allow for manufacture.

The code of step 10 is the whole bracket: eight named dimensions and, in
builder mode, eighteen lines. To use a design like this in more than one
place, make it a custom object, as described in
:ref:`tutorial_parametric_part`.
