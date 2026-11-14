.. _tutorial_combining_solids:

################
Combining solids
################

Every part so far began as a sketch. There is another way to work: start
from ready-made solids - a cylinder, a box, a sphere - and add them
together, cut one out of another, or keep only the place where two
overlap. It is called constructive solid geometry, or CSG, and it is the
first thing many people try because it is so easy to picture.

It is worth knowing well, both for what it does best and for where it
leads you astray. In this tutorial you will build this control knob
entirely from ready-made solids, and then look honestly at the result:

.. image:: /tutorials/assets/combining_solids/knob_finished.svg
    :align: center
    :width: 55%

Along the way you will:

* create ready-made solids and say which part of them sits at the origin,
* add one solid to another,
* subtract a pattern of solids,
* keep only the overlap of two solids,
* shape a cutting tool on its own before using it, and
* rebuild the knob from a sketch and compare the two.

It takes about twenty-five minutes and follows on from
:ref:`tutorial_beyond_extrude`. How the builder and algebra tabs on this
page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the knob, in
millimetres.

.. literalinclude:: /tutorials/combining_solids.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The last line is explained in the next step. As before, each step below
shows the whole of the rest of the file as it stands at that point.

**************************
Step 2: A ready-made solid
**************************

The body of the knob is a :class:`~objects_part.Cylinder`, given its
radius and its height. No sketch is involved.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [body_builder]
            :end-before: [body_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [body_algebra]
            :end-before: [body_algebra]

.. image:: /tutorials/assets/combining_solids/knob_body.svg
    :align: center
    :width: 45%

Left to itself a ready-made solid is centred on the origin in all three
directions, so half of this cylinder would be below the floor. ``align``
changes that. It takes one setting for each of X, Y and Z, and
``on_floor`` - defined in the setup as
``(Align.CENTER, Align.CENTER, Align.MIN)`` - keeps the cylinder centred
in X and Y and puts its lowest point, its ``MIN``, at Z = 0. Every solid
in this tutorial that stands on something is given it.

``Cylinder`` is one of six such solids. The others are ``Box``, ``Sphere``,
``Cone``, ``Torus`` and ``Wedge``.

*****************
Step 3: Add
*****************

The knob has a wider flange at the bottom. It is a second, shorter
cylinder, joined to the first.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [add_builder]
            :end-before: [add_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [add_algebra]
            :end-before: [add_algebra]

.. image:: /tutorials/assets/combining_solids/knob_add.svg
    :align: center
    :width: 45%

This is what you have been doing with shapes in a sketch since the first
tutorial, one dimension up. In builder mode a new solid is added to the
part unless it is told otherwise; in algebra mode ``+`` adds it. The two
cylinders overlap, and the result is a single solid with no seam inside
it.

*********************
Step 4: Subtract
*********************

Flutes round the body give fingers something to grip. Each is a thin
cylinder standing on the flange with its centre on the surface of the
body, and all twelve are cut away.

.. image:: /tutorials/assets/combining_solids/knob_subtract_tools.svg
    :align: center
    :width: 45%

They are placed with the tools of :ref:`tutorial_placing_features`: a
polar pattern, nested inside a move up to the top of the flange.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [subtract_builder]
            :end-before: [subtract_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [subtract_algebra]
            :end-before: [subtract_algebra]

.. image:: /tutorials/assets/combining_solids/knob_subtract.svg
    :align: center
    :width: 45%

``mode=Mode.SUBTRACT`` in builder mode, and ``-`` in algebra mode, remove
the cylinders instead of adding them - again exactly as in a sketch.

Look at what had to be worked out by hand, though. The flutes must not cut
the flange, so they start at ``flange_height`` and are
``height - flange_height`` long. Nothing in the code says "the flutes
belong to the body and not to the flange"; that is carried by two sums
which have to be kept right. Hold that thought until step 7.

**********************
Step 5: Intersect
**********************

The top of the knob should be gently domed. Here combining solids does
something no sketch-and-extrude can: a large :class:`~objects_part.Sphere`
is placed so that its top just touches the top of the knob, and only what
lies inside *both* the knob and the sphere is kept.

.. image:: /tutorials/assets/combining_solids/knob_intersect_tool.svg
    :align: center
    :width: 45%

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [intersect_builder]
            :end-before: [intersect_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [intersect_algebra]
            :end-before: [intersect_algebra]

.. image:: /tutorials/assets/combining_solids/knob_intersect.svg
    :align: center
    :width: 45%

``mode=Mode.INTERSECT`` and the ``&`` operator keep the overlap. The
sphere's centre is ``dome_radius`` below the top of the knob, so the middle
of the top is untouched and the edge is trimmed away, flutes and all.

Add, subtract and intersect are the three ways of combining solids. They
are called *boolean* operations, and everything else in this tutorial is
made from them.

*******************************
Step 6: Make the tool first
*******************************

The knob fits a shaft with a flat on one side, so the hole for it is a
circle with a piece missing. No ready-made solid cuts a hole that shape,
but one is easily made: a cylinder, with the piece beyond the flat cut off
by ``split``, the operation that opened up the adapter in
:ref:`tutorial_beyond_extrude`.

.. image:: /tutorials/assets/combining_solids/knob_cutter.svg
    :align: center
    :width: 22%

The cutter is built on its own first, and then subtracted from the knob.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [cutter_builder]
            :end-before: [cutter_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [cutter_algebra]
            :end-before: [cutter_algebra]

Seen from below, the knob now has its hole:

.. image:: /tutorials/assets/combining_solids/knob_shaft.svg
    :align: center
    :width: 45%

``Plane.YZ.offset(shaft_flat - shaft_radius)`` is an upright plane at the
position of the flat, and ``keep=Keep.BOTTOM`` keeps the side of the
cylinder behind it, the side with the centre in.

In builder mode the cutter is a second ``BuildPart`` of its own, written
before the knob, because a ``split`` inside the knob's builder would split
the knob. :func:`~operations_generic.insert` then brings the finished
cutter into the part being built, and takes a ``mode`` like everything
else. In algebra mode the cutter is one more value, and ``-=`` subtracts
it.

A solid being combined does not have to be a ready-made one. It can be
anything you have built, by any means - including every part made in the
earlier tutorials.

********************************************
Step 7: The same knob, from a sketch
********************************************

The knob is finished, and it was quick to write. Now for the honest look.

Seen from above, the fluted body is one flat shape pushed straight up:

.. image:: /tutorials/assets/combining_solids/knob_plan.svg
    :align: center
    :width: 35%

That is a sketch and an ``extrude``, the method of the first tutorial. So
is the flange, and so is the shaft hole: a circle, split at the flat, and
extruded with ``mode=Mode.SUBTRACT`` - or ``-=`` in algebra mode - so that
it is cut out of the knob instead of added to it.

.. image:: /tutorials/assets/combining_solids/knob_shaft_plan.svg
    :align: center
    :width: 15%

Here is the knob again made that way. Only the dome is unchanged.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [sketch_builder]
            :end-before: [sketch_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/combining_solids.py
            :language: build123d
            :start-after: [sketch_algebra]
            :end-before: [sketch_algebra]

.. image:: /tutorials/assets/combining_solids/knob_sketch.svg
    :align: center
    :width: 55%

It is exactly the same solid. Compare how the two were written:

* **The sums have gone.** The flutes no longer need a starting height or a
  length. They are part of the outline, the outline is extruded, and the
  flange is extruded afterwards and fills their lower ends. ``on_floor``
  is not needed either: a sketch is already on the floor.
* **The design can be seen.** ``plan`` is a flat drawing of the body that
  you can show and check on its own. In the first version the same shape
  existed only as the outcome of thirteen solids.
* **There is less of it.** One extrusion does the work of twelve cuts, and
  the second builder and the ``insert`` have gone, because the shaft hole
  is drawn where it is used. There are fewer positions and lengths to get
  wrong.
* **It is far easier on the CAD kernel.** The kernel is the geometry
  engine underneath build123d that works out every combination. Combining
  flat shapes means finding where lines and arcs cross in a plane.
  Combining solids means finding where curved surfaces meet in space, then
  cutting and stitching those surfaces back into a closed solid. That is
  much, much harder work, and it is where a kernel is most likely to fail,
  with an error or with a solid that is not valid. A knob like this one is
  well within what it can do; a large model built from hundreds of solid
  cuts is where the trouble starts. The more of the combining that is done
  in a sketch, the less there is to go wrong.

Notice that the booleans themselves have not gone anywhere. The flutes are
still subtracted and the shaft hole is still cut. What changed is *where*:
shapes are combined in the flat sketch, where it is simple, and the
extrusion carries the result into the solid. ``mode=`` on ``extrude`` is
the same ``mode=`` as on a ``Cylinder``.

This is why the series began with sketches and came to combining solids
only now, and it is the same order the mainstream graphical CAD programs
work in: sketch first, then make the solid. Building with ready-made solids is quick to start and easy to
picture, and on a part this small it does no harm. As a part grows, each
solid has to be positioned by arithmetic against all the others, and the
shape you had in mind is written down nowhere.

The dome stayed as it was, because that is where combining solids is the
right tool:

* trimming to a shape that comes from another direction, as the sphere
  does;
* cutting with a tool that is easier to build separately than to draw; and
* joining or cutting solids that were each made in their own way.

Try a ``flute_count`` of 8 or a ``dome_radius`` of 40 at the top of the
file. Both versions follow.

********************
What you learned
********************

* ``Box``, ``Cylinder``, ``Sphere``, ``Cone``, ``Torus`` and ``Wedge`` are
  ready-made solids. Each is centred on the origin unless ``align`` says
  otherwise.
* Solids are **added, subtracted and intersected** just as shapes in a
  sketch are: with ``mode=`` in builder mode and with ``+``, ``-`` and
  ``&`` in algebra mode.
* Intersecting keeps only the overlap, which trims a part to a shape that
  could not be extruded.
* A tool can be shaped on its own before it is used, and
  :func:`~operations_generic.insert` brings a finished shape into a
  builder.
* ``extrude`` takes a ``mode`` too, so a sketch can be cut out of a part as
  well as added to it.
* Any solid can be combined with any other, however each was made.
* Combining solids is much harder work for the CAD kernel than combining
  flat shapes, and more likely to fail.
* Reach for a **sketch first**. Use ready-made solids and boolean
  operations for what a sketch cannot say, not in place of one.
