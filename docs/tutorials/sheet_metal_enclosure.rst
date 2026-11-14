.. _sheet_metal_tutorial:
.. _tutorial_sheet_metal_enclosure:

########################
A sheet metal enclosure
########################

A great many parts are not carved from a block or printed in layers. They
are cut from flat sheet and folded: brackets, boxes, covers, chassis. A
sheet metal part has one thickness everywhere, and its shape is a flat
outline plus a set of folds.

build123d models such a part the way it is made. You draw the flat blank,
fold walls up from its edges, relieve the corners so that the folds can
form, and finish the raw edges. At the end the model can be given its
thickness, to be a solid like any other, or unfolded again into the flat
pattern to cut. In this tutorial you will make the base of an enclosure
that way:

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_thicken.svg
    :align: center
    :width: 60%

Along the way you will:

* start a sheet metal part from a flat blank,
* fold walls with ``flange``,
* cut relief at the corners with ``corner_relief``,
* cut holes in a flat face, and a slot that runs through a bend,
* fold the raw rims back with ``hem``,
* give the sheet its thickness with ``thicken``, and
* ``unfold`` it into a flat pattern and export that for cutting.

It takes about twenty-five minutes. How the builder and algebra tabs on
this page work is described in :ref:`tutorial_sketch_then_extrude`.
:ref:`sheet_metal` has a page on each operation used here, with the
options this tutorial does not use.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions, in
millimetres.

.. literalinclude:: /tutorials/sheet_metal_enclosure.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The floor of the enclosure is ``length`` by ``width``, with walls
``wall_height`` high standing round it. Two numbers describe the material: the ``thickness`` of the sheet and
the ``bend_radius``, the inside radius of every fold, which depends on the
tooling used to bend it. The other values are introduced with the step
that uses them.

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*************************
Step 2: The blank
*************************

A sheet metal part starts as a flat blank: here, a rectangle the size of
the floor of the enclosure.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [blank_builder]
            :end-before: [blank_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [blank_algebra]
            :end-before: [blank_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_blank.svg
    :align: center
    :width: 50%

The two modes set the scene differently.

In builder mode a sheet is made inside a :class:`~build_sheet.BuildSheet`.
It is given the material once, and every operation inside it uses that.
The blank is a sketch inside the ``BuildSheet``. The ``BuildSheet`` is
itself inside a ``BuildPart``, which is not needed yet: it is there so
that step 7 can turn the finished sheet into a solid.

In algebra mode the material is a ``SheetMetalParameters``
object, which is passed to each operation. The blank is drawn as an
ordinary sketch object and made into a :class:`~topology.Shell`, a set of
faces joined along their edges, which is what a sheet is. Every operation
from here on takes a sheet and gives back a new one.

What is being built, in both modes, is a *surface* with no thickness. The
sheet is modelled by one of its faces, and the material is imagined on one
side of it. By default that is the side below the blank, so the rectangle
is the top of the finished floor. Step 8 comes back to this.

******************************
Step 3: Fold the walls
******************************

:ref:`flange <sheet_metal_flange>` folds a wall up from an edge. Fold one up
from each of the four edges of the blank.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [walls_builder]
            :end-before: [walls_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [walls_algebra]
            :end-before: [walls_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_walls.svg
    :align: center
    :width: 60%

The free edges of a sheet are its *rims*, and ``rims()`` gives them: for
the blank, its four sides. The builder has the method, and so does the
sheet itself in algebra mode.

``length=wall_height`` is how far the flat part of the wall runs beyond
the bend, and the fold is 90 degrees, towards the upper side of the blank,
unless an ``angle`` says otherwise. Each wall is joined to the floor by a
bend of ``bend_radius``, which ``flange`` makes for you.

``gaps=corner_gap`` shortens each wall at both ends. Without it, the walls
would run the full length of their edges and meet in the corners, and
metal cannot be folded into a closed corner from a single sheet.

**************************************
Step 4: Relieve the corners
**************************************

The gaps keep the walls apart, but there is still a problem at each corner
of the floor. Two bends end there, one from each side, and the metal
between them is being asked to bend two ways at once. On a real part it
would tear or bulge. The remedy is to remove a little material at the
corner before bending: a *relief*.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [relief_builder]
            :end-before: [relief_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [relief_algebra]
            :end-before: [relief_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_relief.svg
    :align: center
    :width: 60%

:ref:`corner_relief <sheet_metal_corner_relief>` cuts a relief at each vertex it is
given, here a round one of ``relief_radius``. The vertices are found by
selection, as in :ref:`tutorial_selecting_and_finishing`:

* ``flats()`` are the flat faces of the sheet, as opposed to its bends, and
  the lowest of them is the floor;
* ``filter_by(Convexity.CONVEX)`` keeps the four outer corners of the
  floor. The floor's outline has other vertices too, where each bend
  begins, but those lie on straight runs of the outline and are not
  corners.

*********************************
Step 5: Holes and a slot
*********************************

The floor needs four mounting holes, and one long wall needs a slot for a
cable, low down, so that it runs through the bend and a little way into
the floor.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [cuts_builder]
            :end-before: [cuts_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [cuts_algebra]
            :end-before: [cuts_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_cuts.svg
    :align: center
    :width: 60%

A sheet is cut in two ways, and this step uses both.
:ref:`sheet_metal_cutouts` has more on each.

**A flat shape cuts the face it lies on.** The holes are circles on the
floor. In builder mode a sketch object inside a ``BuildSheet`` with
``Mode.SUBTRACT`` is a cutter. In algebra mode the four circles are
subtracted from the sheet with ``-=``, as they would be from a sketch.

**A solid cuts everything it passes through.** The slot crosses from the
floor, round the bend and up the wall, so no flat shape could cut it. A
``Box`` centred on the edge of the floor does: ``slot_length`` along the
wall, ``slot_width`` across the bend, and reaching ``slot_height`` up the
wall.

Neither cutter removes material in the way ``Mode.SUBTRACT`` does on a
solid. The sheet is still a surface, and the cutters trim its faces.

***********************************
Step 6: Hem the rims
***********************************

The top edges of the walls are raw, sheared edges: sharp, and easily bent.
A *hem* folds an edge back on itself, which makes it safe to handle and
much stiffer. Hem the two long walls.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [hem_builder]
            :end-before: [hem_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [hem_algebra]
            :end-before: [hem_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_hem.svg
    :align: center
    :width: 60%

The rims have changed. There are now many free edges: the tops and ends of
four walls, and the outlines of the holes and the slot. The selector reads
from left to right: of all the rims, those that run along X, and of those,
the highest group, which is the top edges of the two long walls.

:ref:`hem <sheet_metal_hem>` with ``HemType.OPEN`` folds each back through
180 degrees, leaving a gap of ``hem_opening`` between the folded strip and
the wall, with ``hem_width`` of strip folded over. An open hem is easier to
form than one pressed flat, and the gap is somewhere for a lid to locate.

*************************
Step 7: Thicken
*************************

Everything so far has been a surface. One operation gives it its material.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [thicken_builder]
            :end-before: [thicken_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [thicken_algebra]
            :end-before: [thicken_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_thicken.svg
    :align: center
    :width: 60%

:ref:`thicken <sheet_metal_thicken>` turns the sheet into a solid of the
sheet's thickness. In builder mode this is why the ``BuildSheet`` was
placed inside a ``BuildPart``: when the ``BuildSheet`` ends it hands its
sheet, and its material, to the part, and ``thicken()`` with nothing named
uses them. In algebra mode it is given both.

``enclosure_part`` is now an ordinary solid, to be shown, exported or put
in an assembly. Every bend has its true inside and outside radius, and the
hems are real folded metal.

***********************************
Step 8: The flat pattern
***********************************

A sheet metal part is made from a flat piece, so the last thing to produce
is the outline of that piece. :ref:`unfold <sheet_metal_unfold>` works it
out from the same sheet that was thickened.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [flat_builder]
            :end-before: [flat_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/sheet_metal_enclosure.py
            :language: build123d
            :start-after: [flat_algebra]
            :end-before: [flat_algebra]

.. image:: /tutorials/assets/sheet_metal_enclosure/enclosure_flat.svg
    :align: center
    :width: 55%

``unfold`` flattens every bend and gives back, as ``.flat``, the pattern to
cut: the outline, the holes, and a pair of lines for each bend showing
where it is to be made. ``Align.MIN`` puts the pattern's corner at the
origin, which is what a cutting machine expects.
:class:`~exporters.ExportDXF` writes it to a DXF file, the format laser
cutters and punch presses read.

This is not the outline that was drawn in step 2. The blank has grown: by
the walls, by the hems, and by the right amount for each bend. A bend
stretches the metal on its outside and squeezes it on its inside, and how
much flat sheet a bend uses up depends on the thickness, the radius and
the material. ``unfold`` works that out, so a blank cut to this pattern
folds up into the enclosure of step 7. The corner reliefs are plain to see
here, and the slot shows as the one opening that lies across a bend line.

What decides the size of the pattern
====================================

When metal is bent, the outside of the bend is stretched and the inside is
squeezed. Somewhere between the two is a layer that is neither, and keeps
its length: the *neutral axis*. The flat sheet a bend uses up is the length
of that layer round the bend.

Where the neutral axis lies depends on the metal and on how it is bent, and
it is given as the **K-factor**: a fraction of the thickness, measured from
the inside of the bend. build123d assumes 0.5, the middle of the sheet,
unless told otherwise. Real values are usually smaller, between about 0.3
and 0.5, and come from the supplier of the material or from a test bend.
The K-factor is set with the rest of the material, as
``BuildSheet(..., k_factor=0.33)`` or
``SheetMetalParameters(..., k_factor=0.33)``.

It makes a difference that matters. The pattern above is 178.6 by
155.6 mm. With a K-factor of 0.33 it is 177.8 by 153.2 mm: every bend
uses up a little less sheet, and the hems, which are bent right over, use
up a good deal less. The folded part is exactly the same either way. The
K-factor changes only what has to be cut to make it, and a blank cut with
the wrong one folds up to the wrong size.

The other setting to know about is ``sheet_surface``, which says which
face of the metal the modelled surface is. With the default,
``SheetSurface.INSIDE``, it is the face on the inside of the folds, here
the top of the floor; ``OUTSIDE`` makes it the underside, and ``MID`` the
middle of the sheet. This one does *not* change the flat pattern. The bend
radius is always the true inside radius of the metal, whichever face is
modelled, so the part and its pattern come out the same, and only where
the thickness lies relative to what you drew is different. Choose the
surface that matches how your drawing is dimensioned.
:ref:`sheet_metal_concepts` goes into both.

Try a ``wall_height`` of 40 or a ``thickness`` of 2 at the top of the file,
and compare the flat patterns.

********************
What you learned
********************

* A sheet metal part is a flat blank plus folds. It is modelled as a
  surface, in a ``BuildSheet`` or with ``SheetMetalParameters``, and given
  its thickness at the end.
* :ref:`flange <sheet_metal_flange>` folds a wall from an edge, with the bend
  included, and ``gaps`` keep neighbouring walls apart.
* :ref:`corner_relief <sheet_metal_corner_relief>` removes the material that two
  bends would fight over.
* A flat shape cuts the face it lies on; a solid cuts through bends as
  well.
* :ref:`hem <sheet_metal_hem>` folds a raw rim back on itself.
* ``rims()`` and ``flats()`` select the free edges and the flat faces of a
  sheet.
* :ref:`thicken <sheet_metal_thicken>` makes the solid and
  :ref:`unfold <sheet_metal_unfold>` makes the flat pattern, both from the
  same sheet.
* The K-factor decides how much flat sheet each bend uses, and so the size
  of the pattern. Which face of the metal is modelled does not.

:ref:`tutorial_sheet_metal_lid` carries on from here and makes a lid to
fit this base, using the operations it did not need.

:ref:`sheet_metal_concepts` explains which face of the sheet is modelled,
how bends are allowed for, and how to take dimensions from a drawing.
:ref:`sheet_metal_recipes` has short answers to common needs, such as a
tab folded up out of a slot.
