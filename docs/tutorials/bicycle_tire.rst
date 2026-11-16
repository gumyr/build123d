.. _tutorial_bicycle_tire:

###############
A bicycle tire
###############

The shape of a bicycle tire is simple: one cross-section, turned round an
axle. What makes it a tire is on its surface. The road surface carries a
tread, a pattern of blocks repeated all the way round, and the sidewall
carries lettering, the maker's name and the size.

.. image:: /tutorials/assets/bicycle_tire/tire_finished.png
    :align: center
    :width: 75%
    :alt: A length of bicycle tire with a block tread and lettering on the sidewall

Both start as flat sketches and both have to end up on a curved surface,
and build123d has a tool for each. The tread sits on a single face and
has to keep its size so that it repeats evenly, so it is *wrapped* onto
that face with ``wrap_faces``. The lettering crosses from one face of the
sidewall to the next, so it is *projected* onto the whole tire with
``project_to_shape``. In this tutorial you will do both. Along the way
you will:

* revolve a traced cross-section into a tire,
* draw a tread pattern and wrap it onto the road surface with
  ``wrap_faces``,
* turn the pattern into blocks with ``thicken`` and repeat them round the
  tire,
* make text as a sketch, along a path, in a font chosen to give clean
  geometry,
* project the text across several faces with ``project_to_shape`` and
  emboss it, and
* give the tire a material and measure what the tread adds to its mass
  and its moment of inertia.

It takes about forty minutes and follows on from
:ref:`tutorial_projection_chalice`. How the builder and algebra tabs on
this page work is described in :ref:`tutorial_sketch_then_extrude`. The
tire is the one in the :ref:`examples <examples-bicycle_tire>`.

*********************
Step 1: Setup
*********************

Start a new Python file with the imports and the sizes of the wheel, the
tread and the lettering.

.. literalinclude:: /tutorials/bicycle_tire.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

``rubber`` comes from ``bd_materials``, a library of materials that is
installed with build123d. It is used in the last step. The other values
are introduced with the step that uses them. As before, each step below
shows the whole of the rest of the file as it stands at that point.

************************
Step 2: The tire
************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [tire_builder]
            :end-before: [tire_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [tire_algebra]
            :end-before: [tire_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_whole.png
    :align: center
    :width: 55%

The lines ``l00`` to ``l19`` are the cross-section of half the tire,
traced from a real one as twenty Bezier curves. A Bezier curve is given
by its control points, and each curve starts where the one before it
ended, at ``@ 1``. There is no need to type them; copy the block.

Mirroring the twenty curves in ``Plane.YZ`` gives the other half and
closes the outline, and ``make_face`` fills it. The sketch is placed
``wheel_diameter / 2`` below the X axis and
:func:`~operations_part.revolve` turns it round that axis, so the wheel
stands on edge with its axle along X.

Each curve of the profile sweeps out a face of its own, so the tire has
thirty-seven faces. That decides how the rest of the tutorial goes. The
road surface, where the tread belongs, is a single face from one shoulder
to the other. The sidewall, where the lettering belongs, is several faces
joined edge to edge.

The tread comes first, in steps 3 to 5, and the lettering after it, in
steps 6 to 8.

*************************************
Step 3: A tread pattern, flat
*************************************

The tread begins as a flat sketch of one unit of the pattern: a slanted
bar with two grooves cut across it, and its mirror image.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [pattern_builder]
            :end-before: [pattern_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [pattern_algebra]
            :end-before: [pattern_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_pattern.png
    :align: center
    :width: 45%

``Trapezoid(15, 12, 60, 120)`` is 15 wide and 12 high with its left side
at 60 degrees and its right at 120, which makes the two sides parallel
and the bar lean. The grooves are two long thin rectangles taken out of
it, which leaves three faces, and ``mirror`` in ``Plane.XZ`` adds three
more on the other side of the X axis.

Where the pattern is drawn matters, because the next step reads its
position. The sketch's X will run along the tire and its Y across it,
measured from the line round the middle of the road surface. The bar
starts 1 mm from each axis, so the blocks will start 1 mm either side of
that line.

In builder mode the pattern belongs to a new part, ``tread_unit``, and is
drawn inside it with ``mode=Mode.PRIVATE``. A sketch made inside a part
normally waits there to be turned into a solid by the next operation.
This one is only a drawing to be wrapped, and ``Mode.PRIVATE`` keeps it
out of the part: without it the flat pattern would be thickened in step 5
along with the wrapped one, leaving six stray blocks at the middle of the
wheel.

*************************************
Step 4: Onto the road surface
*************************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [wrap_builder]
            :end-before: [wrap_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [wrap_algebra]
            :end-before: [wrap_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_wrapped.png
    :align: center
    :width: 60%

**The face.** ``road_surface`` is the face the tread goes on. It is the
largest face of the tire, so ``sort_by(Face.area)[-1]`` finds it.

**The path.** The pattern is laid along a line on that face, the circle
round the middle of the road surface. The tire has no edge there, since
the road surface is one face from shoulder to shoulder, so the line is
made by cutting: :func:`~operations_part.section` cuts the tire with
``Plane.YZ``, the plane through the middle of the wheel, and the longest
edge of the cut is the one round the outside. In builder mode ``section``
cuts the part being built, which is why these two lines are inside the
tire's block; in algebra mode it is given the tire.

**The wrap.** :meth:`~topology.Face.wrap_faces` lays the flat faces onto
``road_surface`` along the path. It works within the surface itself: a
distance in the sketch becomes the same distance measured along the face.
The six blocks come back within half a percent of their flat areas, on a
surface that curves both ways, and that is what lets a pattern repeat
evenly round a tire.

In builder mode :func:`~operations_generic.insert` puts the wrapped faces
into the part, where they wait for the next step. In algebra mode they
are kept in ``wrapped_pattern``.

*****************************************
Step 5: Blocks, all the way round
*****************************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [tread_builder]
            :end-before: [tread_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [tread_algebra]
            :end-before: [tread_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_tread.png
    :align: center
    :width: 60%

:func:`~operations_part.thicken` makes each wrapped face a solid block
``block_height`` tall, grown along the surface normal so that it follows
the curve of the tire. In builder mode it is given no faces and takes the
ones that are waiting in the part.

The last statement copies the unit round the tire.
``Rot(X=angle) * tread_unit.part`` is a copy of the whole unit, all six
blocks, turned about the axle, and there is one every ``tread_step``
degrees: 180 units, 1080 blocks. In algebra mode the six blocks are
gathered into one part with ``Part() + [...]``, and that part is copied
in the same way.

The units are kept as a list beside the tire, not added to it: fusing a
thousand solids into one is slow, and nothing here needs it.

***********************************
Step 6: The lettering, flat
***********************************

The lettering is the other half of the job, and it begins the same way:
with a flat sketch.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [label_builder]
            :end-before: [label_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [label_algebra]
            :end-before: [label_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_label.png
    :align: center
    :width: 70%

**The font.** The font matters more than it would on paper. Fonts are
drawn to be printed, and many take liberties that ink hides: outlines
that overlap, strokes that cross themselves, slivers thinner than a hair.
A printer fills all of that in. A solid modeller is asked to make an
exact face from it, and then to project and thicken that face, and each
of those can fail on an outline that is not clean.

``font="singleline"`` chooses a font that comes with build123d and avoids
the problem. Each letter is a single stroke, like handwriting or
engraving, and ``single_line_width`` gives the stroke a width so that it
becomes a face. The outlines are simple and do not overlap. Use it
whenever the text is going to become geometry and its exact style does
not matter. :class:`~objects_sketch.Text` makes one face for each
separate piece of each character: seventeen here, one for each of the
sixteen characters and one more for the dot of the ``i``.

**The path.** Lettering on a tire follows the curve of the wheel, so the
text is given a ``path``: an arc of radius ``label_radius`` about the
axle, a quarter of the way round. ``position_on_path=0.5`` puts the text
at the middle of the arc, and the two ``TextAlign.CENTER`` values centre
it there, along the path and across it. The text is set in the direction
the path runs, and ``reversed()`` turns the arc round so that the
lettering reads left to right from outside the wheel.

**The plane.** The sketch is drawn on ``Plane.ZY.offset(label_offset)``,
a plane standing beside the wheel, 25 mm out from its middle. The
sidewall bulges to 20 mm, so the sketch is clear of the tire and facing
it, as the picture shows.

*********************************
Step 7: Onto the sidewall
*********************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [project_builder]
            :end-before: [project_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [project_algebra]
            :end-before: [project_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_projected.png
    :align: center
    :width: 70%

:func:`~operations_part.project_to_shape` casts the flat letters along
``direction``, straight across toward the wheel, and gives back the
places where they land on ``target``, the tire.

Every letter lands across the edge between two faces of the sidewall, so
each comes back in two pieces, thirty-four faces in all. That is what a
projection is for: it lands on the whole shape, however many faces that
takes, where ``wrap_faces`` works on one.

``hit`` says which landings to keep. The tire is hollow, so letters cast
across it meet the outside of the near sidewall, the inside of it, and
then the far sidewall in the same way. ``Hit.NEAREST`` keeps the first,
the outside of the near sidewall.

In builder mode ``project_to_shape`` is given no faces and takes the
sketch that has just been made, and the projected faces replace it as the
ones waiting in the part. In algebra mode it is given the sketch and the
result is kept in ``letters``.

That is why the two jobs get different tools:

.. list-table::
    :header-rows: 1
    :widths: 22 39 39

    * -
      - ``wrap_faces``
      - ``project_to_shape``
    * - Lands on
      - one face
      - a whole shape, on as many faces as each letter covers
    * - Placed by
      - a path on the face
      - where the sketch is drawn and the direction it is cast
    * - Sizes
      - kept, measured along the surface
      - true as seen along the direction; stretched on a slope
    * - Used here for
      - a tread that must repeat evenly on one face
      - lettering that crosses from face to face

**********************
Step 8: Emboss
**********************

The letters are faces lying on the tire, with no thickness. ``thicken``
gives them some, as it did for the tread, so that each letter stands
``relief`` proud of the sidewall and follows its curve.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [emboss_builder]
            :end-before: [emboss_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [emboss_algebra]
            :end-before: [emboss_algebra]

.. image:: /tutorials/assets/bicycle_tire/tire_embossed.png
    :align: center
    :width: 70%

In builder mode ``thicken`` again takes the faces waiting in the part,
which are now the projected letters. In algebra mode each face of
``letters`` is thickened and the pieces are gathered into one part.

.. tip::

    To engrave the lettering instead, thicken the faces the other way,
    into the tire, with a negative ``amount`` such as ``-0.4``, and cut
    the result from the tire. Keep the depth well under the thickness of
    the wall, which is about 1.5 mm at the sidewall.

******************************
Step 9: The whole tire
******************************

The tire is now three things: the smooth tire, a list of tread units,
and the lettering.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [whole_builder]
            :end-before: [whole_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/bicycle_tire.py
            :language: build123d
            :start-after: [whole_algebra]
            :end-before: [whole_algebra]

.. code-block:: text

    mass 1177 g
    volume +8.2%
    moment +8.8%

.. image:: /tutorials/assets/bicycle_tire/tire_finished.png
    :align: center
    :width: 75%

``Compound(children=[...])`` groups the tire, its thousand blocks and
its lettering into one shape without fusing them. A compound can be
shown, exported and measured like any other shape.

Giving the tire a material gives it a density, and ``mass()`` then
returns its mass, in grams unless told otherwise.

A wheel also has to be spun up to speed, and how hard that is depends on
its *moment of inertia* about the axle: how much material there is, and
how far out it sits. ``principal_properties`` gives a shape's three
principal axes, each with the moment of inertia about it. For a wheel the
largest of the three is the one about the axle, which is what ``max``
picks out.

The tread and lettering add 8.2% to the volume of the tire and 8.8% to
its moment of inertia. The moment grows faster because it counts each
piece of material by the square of its distance from the axle, and the
tread is all at the rim. These moments treat the shape as having a
density of one, so it is their ratio that means something here.

Try a ``block_height`` of 5, or a ``tread_step`` of 4, and see how the
three figures move.

************************
What you learned
************************

* A flat sketch can be put onto a curved surface in two ways, and which
  to use depends on how many faces it has to cover and whether its size
  must be kept.
* :meth:`~topology.Face.wrap_faces` lays flat faces onto a single face
  along a path, measured along the surface, so they keep their size.
* :func:`~operations_part.project_to_shape` casts flat faces onto a whole
  shape along a direction. A letter that crosses from one face to another
  comes back in pieces, and ``hit`` chooses among the surfaces in its
  path.
* :class:`~objects_sketch.Text` makes a sketch of one face for each piece
  of each character, it can follow a ``path``, and
  ``font="singleline"`` gives clean single-stroke letters that are safe
  to turn into geometry.
* :func:`~operations_part.section` can make a line on a face where
  the part has no edge.
* :func:`~operations_part.thicken` turns faces on a curved surface into
  solids.
* A sketch drawn inside a part with ``Mode.PRIVATE`` stays out of the
  part.
* A ``Compound`` groups many solids without fusing them. With a material
  it has a mass, and ``principal_properties`` gives its moments of
  inertia.

:ref:`projection_shape` covers ``project_to_shape`` in full, and
:ref:`projection_faces` covers ``wrap_faces`` and its relative
``project_faces``.
