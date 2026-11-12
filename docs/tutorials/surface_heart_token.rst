.. _tutorial_surface_heart_token:

#############
A heart token
#############

Every solid in the tutorials so far was made *from* something: a sketch
that was extruded, revolved or lofted. The faces of the solid were a
by-product, and their shapes were whatever the operation produced.

Some shapes cannot be reached that way. A surface that swells gently in
two directions at once - a car body, a boat hull, a pebble - is not an
extrusion or a revolution of anything. For shapes like these the work is
done the other way round: make the faces yourself, one by one, and then
join them into a solid. This is *surface modelling*, and in this tutorial
you will use it to make a game token with a domed heart:

.. raw:: html

    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    <model-viewer poster="../_images/heart_finished.png" src="../_static/heart_token.glb" alt="A heart-shaped game token" auto-rotate camera-controls style="width: 100%; height: 50vh;"></model-viewer>

Along the way you will:

* draw the boundary of a face in three dimensions,
* fill it with a curved surface using ``Face.make_surface``,
* make the other faces by mirroring,
* make side faces by extruding edges,
* sew the faces into a ``Shell`` and turn that into a ``Solid``, and
* combine the result with an ordinary extruded part.

It takes about twenty minutes. This is an advanced tutorial: it uses the
lines of :ref:`tutorial_drawing_outlines`, and it works directly with
``Face``, ``Shell`` and ``Solid`` instead of sketches and builders. Steps 2
to 7 are the same in builder and algebra mode for that reason; only the
last step has tabs. :ref:`surface_modeling` describes the ideas behind
it.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the token,
in millimetres.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

``edge_height`` is how thick the heart is at its edge, and ``crown_height``
is how far its middle is lifted above that. The frame round the heart is
``frame_width`` wide and ``frame_height`` high.

***********************************
Step 2: Half of the outline
***********************************

The heart is the same on both sides, so only the right-hand half is drawn.
Its outline is three lines, flat on ``Plane.XY``.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [outline]
    :end-before: [outline]

.. image:: /tutorials/assets/surface_heart_token/heart_outline.png
    :align: center
    :width: 60%

* ``side`` is a long shallow arc from the point at the bottom of the heart
  up its right side. A ``JernArc`` is an arc given by where it starts, the
  direction it sets off in, its radius and how far round it goes.
* ``lobe`` is the round top. It starts where ``side`` ends, ``side @ 1``,
  and in the direction ``side`` was going, ``side % 1``, so the two join
  smoothly.
* ``dip`` runs from the end of the lobe, in the direction the lobe was
  going, until it reaches the centre line of the heart. Giving ``PolarLine``
  a shape as its ``length`` makes it run until it meets that shape.

These are lines on their own, not lines in a ``BuildLine``. Nothing is
being collected into a sketch; each line is kept in a variable, and the
variables are what the next steps use.

***************************************
Step 3: The ridge down the middle
***************************************

A flat outline would give a flat face. To make the surface rise, one of
its edges has to leave the plane. The fourth edge runs down the centre
line of the heart, from the dip back to the point, and arches up as it
goes.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [ridge]
    :end-before: [ridge]

.. image:: /tutorials/assets/surface_heart_token/heart_ridge.png
    :align: center
    :width: 60%

``ThreePointArc`` draws an arc through three points. The first and last
are the two ends of the centre line, and the middle one is the point
half-way between them lifted by ``crown_height``. Points can be added and
averaged like numbers, which is how ``middle`` is found.

The four edges now meet end to end, and ``Wire`` joins them into one closed
loop: the boundary of the face to be made.

***********************
Step 4: A surface
***********************

``Face.make_surface`` fills a closed boundary with a smooth surface. Given
only the boundary it makes a surface that spans it. Given points as well,
it makes the surface pass through them.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [surface]
    :end-before: [surface]

.. image:: /tutorials/assets/surface_heart_token/heart_surface.png
    :align: center
    :width: 60%

``crown`` is a point above the centre of the lobe, and the surface is
pulled up through it, which is what gives the heart its domed look. This
one face is something no extrusion could have made: it curves in every
direction, and its edge is partly flat and partly arched.

Two more things happen on that line:

* The ``-`` in front of ``Face`` turns the face over. Every face has a
  front and a back, and a viewer colours the front. It makes no difference
  to the shape.
* ``Pos(Z=edge_height / 2) *`` lifts the face by half the thickness of the
  heart's edge, to leave room for the sides.

*************************
Step 5: Mirror it
*************************

One quarter of the heart's skin is made. The other three are reflections
of it.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [mirror]
    :end-before: [mirror]

.. image:: /tutorials/assets/surface_heart_token/heart_mirror.png
    :align: center
    :width: 60%

Mirroring in ``Plane.YZ`` gives the left half of the top, and mirroring in
``Plane.XY`` gives the bottom. ``mirror`` is used here as a method of the
face, ``face.mirror(plane)``, which is the same reflection as the
``mirror`` of :ref:`tutorial_beyond_extrude`.

The top and bottom do not touch. There is a gap of ``edge_height`` between
them all the way round.

*************************
Step 6: The sides
*************************

The gap is closed by a wall: the flat outline of step 2, pushed straight
up.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [sides]
    :end-before: [sides]

.. image:: /tutorials/assets/surface_heart_token/heart_sides.png
    :align: center
    :width: 60%

Extruding a sketch gives a solid. Extruding a *line* gives a face, and
``Shell.extrude`` does that to each edge of a wire, giving a strip of
faces. ``rim`` is the three flat edges of step 2 - not the ridge, which is
inside the heart - and the strip is started half the thickness below the
plane, so that it reaches from the bottom faces to the top ones.

Notice that ``rim`` is built from the very same ``side``, ``lobe`` and
``dip`` that the surface was. That matters for the next step.

*******************************************
Step 7: From faces to a solid
*******************************************

Six faces now enclose a space. Two more lines make that space a solid.

.. literalinclude:: /tutorials/surface_heart_token.py
    :language: build123d
    :start-after: [solid]
    :end-before: [solid]

.. code-block:: text

    True 555.8200293703513

.. image:: /tutorials/assets/surface_heart_token/heart_solid.png
    :align: center
    :width: 60%

A :class:`~topology.Shell` is a set of faces joined along their edges. If
it has no gaps it is said to be *watertight*, and a watertight shell is
the boundary of a volume. :class:`~topology.Solid` takes it and makes that
volume.

Always check the result. ``is_valid`` is ``True`` and the heart has a
volume, so the faces did close up. Had there been a gap, there would be no
solid to measure.

.. note::

    Faces only join where their edges are exactly the same. The surest way
    to get that is the one used here: make each edge once, keep it in a
    variable, and build every face that shares it from that variable. Two
    edges that were calculated separately and merely look the same are the
    usual reason a shell will not close.

***********************
Step 8: A frame
***********************

The heart is a solid like any other now, and everything from the earlier
tutorials works on it. Give it a frame: a ring round the outline, extruded
to both sides, with the heart added to it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/surface_heart_token.py
            :language: build123d
            :start-after: [frame_builder]
            :end-before: [frame_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/surface_heart_token.py
            :language: build123d
            :start-after: [frame_algebra]
            :end-before: [frame_algebra]

.. image:: /tutorials/assets/surface_heart_token/heart_finished.png
    :align: center
    :width: 60%

The outline of the heart is drawn a third time from the same three lines,
closed with a straight line down the middle and mirrored. ``offset``
grows it by ``frame_width``, and taking the heart's own outline back out
leaves a ring. ``extrude`` with ``both=True`` pushes the ring up and down
from the plane, so that the frame is centred on the heart.

In builder mode ``insert`` brings an existing shape into the builder: the
three lines into the ``BuildLine``, the outline back into the sketch to be
subtracted, and at the end the heart itself into the part.

Try a ``crown_height`` of 3 for a plumper heart, or 0.5 for a flatter one.

********************
What you learned
********************

* Surface modelling builds a solid from its skin: make the faces, join
  them into a ``Shell``, make the shell a ``Solid``.
* A curved face starts from its boundary, a closed ``Wire`` of edges that
  need not be flat.
* ``Face.make_surface`` fills a boundary, and can be made to pass through
  given points.
* Faces can be mirrored, and ``Shell.extrude`` turns edges into side
  faces.
* A shell only closes if neighbouring faces share exactly the same edges,
  so make each edge once and reuse it.
* The result is an ordinary solid that can be combined with anything
  else.

:ref:`tutorial_drawing_outlines` introduced lines, and :ref:`topology`
describes how vertices, edges, faces, shells and solids fit together.
