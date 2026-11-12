.. _stl_reconstruction_tutorial:

##############################
Rebuilding a part from an STL
##############################

Sooner or later you will want to change a part of which all that survives
is an STL file. An STL is a *mesh*: thousands of flat triangles that
together look like the part. Nothing in it says that this patch of
triangles was a hole and that one a fillet, or how big anything was meant
to be. It can be printed, but not edited.

There is no button that turns a mesh back into a design. What build123d
offers is help with doing it by hand:
:func:`~build123d.detect_primitives` looks through the triangles for the
planes, cylinders and spheres they came from and reports what it finds. In
this tutorial you will use that report to recover the dimensions of a part
and rebuild it.

.. image:: /tutorials/assets/stl_reconstruction/stl_leftovers.png
    :align: center
    :width: 70%

.. warning::

    Rebuilding from an STL is slow, approximate and manual. The detector
    gives clues, not a model. Expect to do the designing yourself.

Along the way you will:

* read an STL file with ``Mesher``,
* cut a mesh down by its symmetry, and keep the piece in a faster format,
* run ``detect_primitives`` and look at what it found and what it missed,
* read dimensions out of the code it writes,
* measure what it missed directly from the mesh, and
* check the rebuilt part against the original mesh.

It takes about twenty minutes, and it is the same in builder and algebra
mode apart from one line. So that you can check your answer, the mesh is
one whose design you already have: the bracket of :ref:`design_tutorial`.
Read its first three steps again before starting. Looking for symmetry and
choosing an origin matter even more here than they did there.

***************************
Step 1: Make the STL
***************************

Open the file you ended :ref:`design_tutorial` with, add one line to the
end of it, and run it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/stl_reconstruction.py
            :language: build123d
            :start-after: [stl_builder]
            :end-before: [stl_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/stl_reconstruction.py
            :language: build123d
            :start-after: [stl_algebra]
            :end-before: [stl_algebra]

There is now a file called ``bracket.stl`` beside it. Close that file and
do not look at it again until step 9. From here on, the STL is all you
have.

*****************************
Step 2: Read the mesh
*****************************

Start a new Python file in the same folder.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [mesh]
    :end-before: [mesh]

.. code-block:: text

    2584 triangles
    Vector: (X=50, Y=25, Z=25)

.. image:: /tutorials/assets/stl_reconstruction/stl_mesh.png
    :align: center
    :width: 65%

:class:`~mesher.Mesher` reads mesh files, and ``read`` gives a list of the
shapes in the file, of which this one has one. What comes back is a solid,
but look at it closely: where the bracket had 24 faces this has 2,584,
every one a flat triangle. The round bend is a fan of long thin triangles
and the hole is a ring of them.

The overall size can be had straight away from the bounding box: 50 by 25
by 25. Round numbers are a good sign that the part was designed in
millimetres.

***************************************
Step 3: Cut it down by symmetry
***************************************

Look at the mesh from the front, the top and the side, as in step 1 of
:ref:`design_tutorial`. This part is the same on the left as on the right,
and the same at the front as at the back, and happily its origin is where
those two planes of symmetry meet. So three quarters of the mesh say
nothing that the fourth does not.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [quarter]
    :end-before: [quarter]

.. code-block:: text

    723 triangles

.. image:: /tutorials/assets/stl_reconstruction/stl_quarter.png
    :align: center
    :width: 65%

:func:`~operations_generic.split`, from :ref:`tutorial_beyond_extrude`,
cuts the mesh with ``Plane.YZ`` and then with ``Plane.XY`` and keeps one
side each time. Less mesh is quicker to work on and, more to the point,
gives a shorter report to read.

A mesh from somewhere else will rarely sit so conveniently. If its planes
of symmetry are not the standard planes, move the mesh first, or cut with
planes placed where its symmetry is.

*****************************************
Step 4: Keep the working piece
*****************************************

Reading and cutting a large STL can take a long time, and the next steps
will be run again and again. Save the piece you are working on, once, in
build123d's own BREP format, which loads far faster.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [cache]
    :end-before: [cache]

Then replace the lines of steps 2 and 3, and that one, with a single line,
and carry on from there:

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [reload]
    :end-before: [reload]

For this small bracket the difference is slight. For a mesh of a million
triangles it is the difference between waiting a minute for every
experiment and not waiting.

*************************************
Step 5: Detect the primitives
*************************************

Now ask what the triangles were.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [detect]
    :end-before: [detect]

.. code-block:: text

    7 primitives, 199 triangles left over

.. image:: /tutorials/assets/stl_reconstruction/stl_primitives.png
    :align: center
    :width: 65%

:func:`~build123d.detect_primitives` gives back three things:

* ``primitives`` are the true faces it recognised, shown above: five
  planes, in blue, and two cylinders, in orange. Each stands for a great
  many triangles. A plane comes back as a rectangle as big as the bounding
  box of the flat region it was found in, not as the outline of that
  region, which is why the picture looks like a box and not like a
  bracket.
* ``leftovers`` are the triangles it could not account for.
* ``code_lines`` is a report, written as build123d code.

Show ``primitives`` and ``leftovers`` in your viewer, in different colours.
What was found well, and what was not, decides what to do next.

.. image:: /tutorials/assets/stl_reconstruction/stl_leftovers.png
    :align: center
    :width: 65%

Here the leftovers, in red, are in three places: the bend, the end of the
slot, and the two flat faces where step 3 cut the mesh. The cut faces are
not part of the bracket and can be ignored. The bend and the slot are
real, and are dealt with in step 7.

*******************************
Step 6: Read the report
*******************************

Print the code.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [report]
    :end-before: [report]

.. code-block:: build123d

    r0 = Plane.XY.offset(12.5) * Rectangle(25, 23, align=Align.MIN)
    r1 = Plane.YZ.offset(22) * Pos(5, -0) * Rectangle(20, 12.5, align=Align.MIN)
    c2 = Plane.YZ.offset(22) * Pos(14.9631, -0.00137) * Face.extrude(Circle(2.50137).edge(), (0, 0, 3))
    c3 = Plane.YZ.offset(22) * Pos(23, 10.5) * Face.extrude(Circle(2).edge(), (0, 0, 3))
    r4 = Plane.YZ.offset(25) * Pos(5, -0) * Rectangle(20, 12.5, align=Align.MIN)
    r5 = Plane.ZX * Rectangle(12.5, 20, align=Align.MIN)
    r6 = Plane.ZX.offset(3) * Rectangle(12.5, 20, align=Align.MIN)

Each line would make one of the primitives, and the lines can be run. That
is not what they are for. *Do not build the part out of this code.* Read
it, as a list of clues. It is written in algebra mode, with every shape
placed as a plane, an offset and a position, so that shapes which belong
together show up as lines that start the same way.

Look first at the planes and their offsets:

* ``Plane.YZ`` appears with offsets of 22 and 25. Two parallel faces 3 mm
  apart: this is a wall **3 mm thick**, and its outside is 25 mm from the
  middle, so the part is **50 mm long**.
* ``Plane.ZX`` appears with offsets of 0 and 3. Another wall 3 mm thick, at
  right angles to the first. The part is a strip of one thickness, bent.
* ``Plane.XY.offset(12.5)`` is the edge of the strip, 12.5 mm from the
  middle: the strip is **25 mm wide**.

Then at what sits on them:

* ``c2`` is a cylinder of radius 2.50137, 3 mm long, through the wall on
  ``Plane.YZ``. A cylinder exactly as long as the wall is thick is a
  **hole, 5 mm across**. The stray digits are the mesh speaking: a circle
  made of straight pieces is not quite a circle. Round to the number a
  designer would have chosen.
* ``c3`` is a cylinder of radius 2, also through that wall, with its
  centre 2 mm in from the wall's edges. That is a **corner rounded to
  2 mm**.
* The rectangles on ``Plane.YZ`` begin 5 mm up and run to 25, and those on
  ``Plane.ZX`` stop at 20, which is 5 short of the outside of the other
  wall. The flat faces end 5 mm before the corner where the walls would
  meet, so something fills that corner. The part is **25 mm high**.

Seven lines have given the thickness, the three overall sizes, a hole and
a fillet.

***********************************************
Step 7: Measure what was left over
***********************************************

The detector did not recognise the bend or the slot, so nothing in the
report describes them. The triangles are still there, though, and they can
be measured. Pick out the leftover triangles in each of the two places,
and ask how much room they take up.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [leftovers]
    :end-before: [leftovers]

.. code-block:: text

    bend: Vector: (X=5, Y=5, Z=12.5)
    slot: Vector: (X=9.99922, Y=3, Z=2.5)

``filter_by_position`` keeps the faces whose centres lie between two values
along an axis. The limits come from looking at the picture in step 5: the
bend is in the corner where X is over 20 and Y under 5, and the end of the
slot is in the base, a little way out from the middle.

* The triangles of the bend fill a square 5 by 5: the corner is **rounded
  to a radius of 5 mm**, which agrees with the flat faces stopping 5 mm
  short of it.
* The triangles of the slot reach X = 10 and Z = 2.5. Doubled, because
  this is a quarter of the part, that is a **slot 20 mm long** and 5 mm
  wide, the same width as the hole.

Measuring the mesh like this is always possible when the detector has
nothing to say. The detector only makes it quicker.

*****************************
Step 8: The dimensions
*****************************

Write down what has been found.

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [dimensions]
    :end-before: [dimensions]

With the numbers known, the part has to be designed, and that is the
subject of :ref:`design_tutorial`: a strip of one thickness with a rounded
bend is a line that has been offset; a part with two planes of symmetry is
a quarter, mirrored twice. None of that is in the mesh. It is the step the
detector cannot take, and the reason this is a redesign and not a
conversion.

Now open the bracket file again and compare. These are the eight numbers
it began with.

*****************************************************
Step 9: Check the rebuilt part against the mesh
*****************************************************

Never trust a reconstruction without checking it against what it was
reconstructed from. Read the whole mesh again with the line from step 2,
and with ``rebuilt`` as the part made from these numbers:

.. literalinclude:: /tutorials/stl_reconstruction.py
    :language: build123d
    :start-after: [compare]
    :end-before: [compare]

.. code-block:: text

    mesh      6412.4 mm3   50.0 x 25.0 x 25.0
    rebuilt   6412.7 mm3   50.0 x 25.0 x 25.0

.. image:: /tutorials/assets/stl_reconstruction/stl_rebuilt.png
    :align: center
    :width: 65%

The sizes agree and the volumes differ by a few parts in a hundred
thousand. The mesh is very slightly the smaller, because its flat
triangles cut across the inside of every curve. A wrong dimension would
show up here at once: a hole of the wrong size, or a missing fillet,
changes the volume far more than that. Showing the two on top of one
another in a viewer is a good second check.

*****************************************
When this works, and when it does not
*****************************************

The bracket was a kind case, and even so the detector found two of its
features and missed two. It helps most when:

* the mesh is clean, and fine enough for curves to be recognisable;
* the part is mechanical, made mostly of flat, cylindrical and spherical
  faces;
* there is symmetry, or features that repeat.

Expect to do more by hand when:

* the part has freeform surfaces, which are neither planes, cylinders nor
  spheres;
* the mesh is coarse or noisy;
* most of the mesh ends up in ``leftovers``, or the report is a long list
  of small fragments.

When that happens, try a smaller piece of the mesh. If that does not help,
use the mesh only as something to measure and to look at, as step 7 did,
and build the part from what you measure.

********************
What you learned
********************

* An STL holds triangles, not a design. Rebuilding from one is a redesign
  that the mesh can guide.
* ``Mesher`` reads an STL, ``split`` cuts it down by its symmetry, and
  saving the working piece as BREP makes it quick to reload.
* :func:`~build123d.detect_primitives` returns the faces it recognised,
  the triangles it did not, and a report written as code.
* Read the report for planes that repeat and offsets that pair up; they
  give thicknesses and overall sizes. Cylinders give holes and fillets.
* What the detector misses can be measured from the leftover triangles.
* Round to the numbers a designer would have used, and check the result
  against the mesh.
