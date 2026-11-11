.. _tutorial_beyond_extrude:

##############
Beyond extrude
##############

``extrude`` pushes a sketch in a straight line, and a surprising number of
parts need nothing else. Some shapes cannot be made that way: one that
changes from an oval at one end to a circle at the other, one that is round
like a turned part, one that is a thin shell. Each has its own operation,
and every one of them still starts from a sketch. In this tutorial you will
build this adapter, which joins an oval nozzle to a round vacuum hose:

.. image:: /tutorials/assets/beyond_extrude/adapter_finished.svg
    :align: center
    :width: 60%

Along the way you will:

* blend one sketch into another with ``loft``,
* turn a profile round an axis with ``revolve``,
* hollow a solid into a thin shell with ``offset``,
* extrude a face of the part itself,
* draw one side of a symmetric feature and ``mirror`` it, and
* cut the part open with ``split`` to look inside.

It takes about twenty-five minutes and follows on from
:ref:`tutorial_selecting_and_finishing`. How the builder and algebra tabs
on this page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the adapter,
in millimetres.

.. literalinclude:: /tutorials/beyond_extrude.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*******************************************
Step 2: Loft, from one shape to another
*******************************************

The hood of the adapter is oval where it meets the nozzle and round where
it meets the hose. No single sketch describes that, but two do: an ellipse
at the bottom and a circle higher up.

``Plane.XY.offset(hood_height)`` is a plane parallel to ``Plane.XY`` and
``hood_height`` above it, which is where the circle is drawn.
:func:`~operations_part.loft` then makes the solid that passes through both
sketches, changing smoothly from one to the other.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [loft_builder]
            :end-before: [loft_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [loft_algebra]
            :end-before: [loft_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_loft.svg
    :align: center
    :width: 55%

In builder mode ``loft`` with no argument takes the sketches that have been
made and not yet used, in the order they were made. In algebra mode it is
given them as a list. A loft is not limited to two: give it three or more
sections and it passes through them all.

*************************************************
Step 3: Revolve, turn a profile round an axis
*************************************************

The collar that the hose pushes onto is round, with a raised barb near the
top to grip the hose. A shape like that - anything that could be turned on
a lathe - is drawn as half of its cross-section and spun round its centre
line by :func:`~operations_part.revolve`.

The profile is drawn on ``Plane.XZ``, the upright plane from
:ref:`tutorial_placing_features`, so that its coordinates read as
*(distance from the centre line, height)*. ``Polyline`` draws a run of
straight lines through a list of points, and ``close=True`` joins the last
point back to the first, which here is quicker than the line-by-line
drawing of :ref:`tutorial_drawing_outlines`.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [revolve_builder]
            :end-before: [revolve_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [revolve_algebra]
            :end-before: [revolve_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_revolve.svg
    :align: center
    :width: 55%

The profile, in red, has one edge lying on the Z axis, and that is the axis
it is revolved about. The collar joins the hood because it starts at the
height and radius where the hood ends. ``revolve`` goes all the way round
unless it is given a smaller ``revolution_arc`` in degrees.

*************************
Step 4: Hollow it out
*************************

So far the adapter is solid. It needs to be a shell ``wall`` thick, open at
the bottom and at the top.

You met :func:`~operations_generic.offset` in the first tutorial, shrinking
an outline to make a rim. Given a solid and a negative amount it moves
every face inwards by that much, and given some faces as ``openings`` it
removes those faces and leaves the space between the old surface and the
new one. The two openings are the lowest and the highest faces, selected as
in :ref:`tutorial_selecting_and_finishing`.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [hollow_builder]
            :end-before: [hollow_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [hollow_algebra]
            :end-before: [hollow_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_hollow.svg
    :align: center
    :width: 55%

One line has turned a solid into a shell with the same wall thickness
everywhere, round the barb included. This is the reason to shape the
outside first and hollow it afterwards: there is no inside surface to
design.

**************************
Step 5: Extrude a face
**************************

The adapter needs a short straight skirt at the bottom, to slide over the
nozzle. Its cross-section is exactly the rim the hollowing left behind - an
oval ring ``wall`` wide - and that rim is a face of the part.

A face can be extruded as well as a sketch. Select the lowest face, and
give it to ``extrude``:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [skirt_builder]
            :end-before: [skirt_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [skirt_algebra]
            :end-before: [skirt_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_skirt.svg
    :align: center
    :width: 55%

Nothing was drawn for this step. The rim, in red, is pushed straight out of
the part, away from the solid, so the skirt grows downwards and matches the
wall above it exactly. In builder mode this is ``extrude`` being given what
to extrude, as mentioned in the first tutorial, instead of taking the last
sketch.

**************************************
Step 6: Mirror, draw one side only
**************************************

Two ears, one each side, take the screws that hold the adapter in place.
The ears are the same, one the reflection of the other, so only one is
drawn: a circle with a screw hole in it, placed just beyond the end of the
skirt. :func:`~operations_generic.mirror` makes the second by reflecting
the first in ``Plane.YZ``, the upright plane through the middle of the
part.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [mirror_builder]
            :end-before: [mirror_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [mirror_algebra]
            :end-before: [mirror_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_mirror.svg
    :align: center
    :width: 55%

The ear that was drawn is in red. The last line of the sketch subtracts the
ellipse of the base, which trims away the part of each ear that would
otherwise reach inside the skirt and block it. The sketch sits on an offset
plane level with the bottom of the skirt, and is extruded up to the same
height as the skirt.

In builder mode ``mirror`` with no shape named reflects everything in the
sketch so far and adds the reflection to it. In algebra mode it is given
the ear and returns the reflected copy, which is added to the original.

Mirroring is not only for sketches: the same ``mirror`` reflects lines,
and whole solids, in the same way.

*********************************
Step 7: Split, to look inside
*********************************

The adapter is finished, and from outside there is no way to see whether
the wall came out as intended. :func:`~operations_generic.split` cuts a
shape in two with a plane and keeps one half, which opens the part
up to inspect.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [split_builder]
            :end-before: [split_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/beyond_extrude.py
            :language: build123d
            :start-after: [split_algebra]
            :end-before: [split_algebra]

.. image:: /tutorials/assets/beyond_extrude/adapter_split.svg
    :align: center
    :width: 50%

The part is cut by ``Plane.XZ``, the upright plane through its middle, and
``keep=Keep.BOTTOM`` chooses the half behind that plane. The result is put
in a new variable, ``back_half``, so the adapter itself is untouched. In
builder mode the line comes after the ``with`` block and is given
``adapter.part``; like any operation, ``split`` can be used on a shape
directly, outside a builder.

The cut half shows what the earlier steps claimed: one wall thickness from
the skirt, up the hood and over the barb, and ears that stop at the outside
of the skirt.

Try a ``collar_radius`` of 20, a ``hood_height`` of 70 or a ``wall`` of 3 at
the top of the file, and look at the cut half again.

********************
What you learned
********************

* Every operation here starts from a sketch or a face, as ``extrude`` does.
  What differs is how the solid is made from it.
* :func:`~operations_part.loft` blends two or more sketches on different
  planes into one solid, and ``Plane.XY.offset()`` puts a plane at a
  height.
* :func:`~operations_part.revolve` spins a profile round an axis to make a
  round part.
* :func:`~operations_generic.offset` with ``openings`` hollows a solid
  into a shell of even thickness.
* ``extrude`` accepts a face of the part as well as a sketch.
* :func:`~operations_generic.mirror` reflects a shape in a plane, so a
  symmetric feature is drawn once.
* :func:`~operations_generic.split` cuts a shape with a plane, which is a
  quick way to look inside one.
* :func:`~operations_generic.sweep`, from
  :ref:`tutorial_drawing_outlines`, belongs to the same family: it carries
  a sketch along a path.
