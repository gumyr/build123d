.. _tutorial_surface_spitfire_wing:

###############
A Spitfire wing
###############

:ref:`tutorial_surface_heart_token` made a curved face from its boundary
and one point inside it. That is enough for a gentle dome, but not for a
shape whose cross-section matters all the way along. A wing has to be an
exact airfoil at the root, a different, thinner airfoil at the tip, and a
smooth blend between, inside an outline that is curved as well.

A *Gordon surface* is made for this. It is given a grid of curves - some
running one way, the rest crossing them - and makes the surface that
passes through all of them. In this tutorial you will use one to make the
elliptical wing of a Supermarine Spitfire:

.. raw:: html

    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    <model-viewer poster="../_images/wing_finished.png" src="../_static/spitfire_wing.glb" alt="The wing of a Supermarine Spitfire" auto-rotate camera-controls style="width: 100%; height: 50vh;"></model-viewer>

Along the way you will:

* draw the outline of the wing as two elliptical arcs,
* measure a shape by intersecting it with an axis,
* place and scale ready-made NACA airfoils,
* make a surface through a grid of curves with
  ``Face.make_gordon_surface``, and
* close the surface and turn it into a solid.

It takes about twenty minutes, and follows on from
:ref:`tutorial_surface_heart_token`, which introduced faces, shells and
solids. Like that tutorial it works directly with edges and faces, so it
is the same in builder and algebra mode. :ref:`surface_modeling` describes
the ideas behind it.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the wing.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The Spitfire was designed in feet and inches, and the dimensions are
written that way. ``FT`` and ``IN`` are the number of millimetres in a
foot and an inch, so ``36 * FT + 10 * IN`` is the span in millimetres, and
the model is in millimetres like every other.

``wing_span`` is from tip to tip, and one wing is half of it.
``wing_leading`` and ``wing_trailing`` are how far the wing reaches
forward and back from the line the outline is drawn about, and
``wing_leading_fraction`` is how far along each airfoil that line falls.
``wing_tip_section`` is where the last airfoil will sit, an inch short of
the tip.

***********************************************
Step 2: The leading and trailing edges
***********************************************

Seen from above, a Spitfire wing is two quarter-ellipses back to back: a
shallow one for the leading edge and a deeper one for the trailing edge.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [guides]
    :end-before: [guides]

.. image:: /tutorials/assets/surface_spitfire_wing/wing_guides.png
    :align: center
    :width: 70%

An ``EllipticalCenterArc`` is part of an ellipse, given by its centre, its
two radii, the angle it starts at and how far round it goes. Both arcs are
centred on the origin and are half the span long in X. The leading edge
reaches ``wing_leading`` forwards, towards -Y, and the trailing edge
``wing_trailing`` backwards. They meet at the tip.

These two curves run the length of the wing. In a Gordon surface the
curves that run one way are called the *guides*, and these are they.

***************************************
Step 3: How wide is the wing?
***************************************

The curves that cross the guides will be airfoils, and each has to be
exactly as long as the wing is wide at the place it sits. That width - the
*chord* - is measured from the guides.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [chords]
    :end-before: [chords]

.. code-block:: text

    2807 mm at the root, 267 mm near the tip

``across`` is an axis that crosses the wing from front to back, at the
root and then at ``wing_tip_section``. ``intersect`` gives the points where
a curve meets it, and the chord is the distance in Y between the point on
the leading edge and the point on the trailing edge.

Nothing about the ellipses had to be worked out by hand. The shapes were
asked.

***************************
Step 4: The airfoils
***************************

``Airfoil`` draws a standard NACA airfoil from its four-digit code. It is
one unit long, with its nose at the origin. Each one is moved so that the
right point along it is on the centre line, scaled up to its chord, and
stood on its edge.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [airfoils]
    :end-before: [airfoils]

.. image:: /tutorials/assets/surface_spitfire_wing/wing_airfoils.png
    :align: center
    :width: 70%

Read each expression from the inside out:

* ``Airfoil("2213")`` is the airfoil at the root, 13% as thick as it is
  long. The tip is a ``"2205"``, only 5% thick.
* ``.move(Pos(-wing_leading_fraction, 0, 0))`` slides it so that the part
  in front of the centre line is on the negative side.
* ``scale(..., about=(0, 0, 0))`` enlarges it to the chord from step 3,
  about the origin, so the centre line stays where it is.
* ``Plane.YZ *`` stands it up across the wing, and for the tip
  ``Pos(Z=wing_tip_section)`` moves it out along the span first.

The two airfoils, in red, now sit exactly between the guides, each
touching both. These are the *profiles* of the Gordon surface.

***********************************
Step 5: The Gordon surface
***********************************

There are guides running along the wing and profiles crossing them.
Together they are the grid the surface will be stretched over:

.. image:: /tutorials/assets/surface_spitfire_wing/wing_grid.svg
    :align: center
    :width: 85%

The two guides, in blue, are the leading and trailing edges of step 2. The
profiles, in red, are the two airfoils of step 4 and one more thing: the
point where the guides meet at the tip. A profile may be a single point,
and that is how the surface is brought to a close there. The tip airfoil
is the small one beside it, an inch in from the end.

One call makes the surface through them all.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [surface]
    :end-before: [surface]

.. image:: /tutorials/assets/surface_spitfire_wing/wing_surface.png
    :align: center
    :width: 70%

``profiles`` is the list of the three in red, and ``guides`` the two in
blue.

The grid has to be a true one. *Every profile must cross every guide, and
cross it exactly once.* That is why step 3 measured the chords from the
guides instead of calculating them: an airfoil that stopped a little short
of a guide, or ran a little past it, would not be on the grid, and the
surface could not be made.

As in the heart token, the ``-`` turns the face so that its front is
outwards.

*************************************************
Step 6: Close the root and make a solid
*************************************************

The surface is open at the root, where the wing would join the aircraft.
A flat face closes it.

.. literalinclude:: /tutorials/surface_spitfire_wing.py
    :language: build123d
    :start-after: [solid]
    :end-before: [solid]

.. code-block:: text

    True 1.99 cubic metres

.. image:: /tutorials/assets/surface_spitfire_wing/wing_root.png
    :align: center
    :width: 70%

The edge of the opening is taken from the surface itself.
``filter_by(Edge.is_closed)`` keeps the one edge of the surface that is a
closed loop, which is the airfoil at the root, and ``Face`` fills a flat
loop with a flat face, shown in red.

Taking the edge from the surface, instead of using ``airfoil_root`` again,
is the rule of the heart token at work: the two faces must share exactly
the same edge, and the surest way is to take the edge from the face that
already has it. The two faces then make a ``Shell``, and the shell a
``Solid``, as before.

Check it: the solid is valid, and one wing has a volume of about two cubic
metres.

.. image:: /tutorials/assets/surface_spitfire_wing/wing_finished.png
    :align: center
    :width: 70%

Try ``Airfoil("2218")`` at the root for a thicker wing, or a
``wing_leading`` of ``4 * FT`` to move the widest point of the outline
back.

********************
What you learned
********************

* A Gordon surface passes through a grid of curves: *guides* one way and
  *profiles* across them. ``Face.make_gordon_surface`` makes it.
* Every profile must cross every guide exactly once, and a profile can be
  a single point where the surface comes to a tip.
* Measure from the geometry, with ``intersect``, to make curves that are
  sure to meet.
* ``Airfoil`` draws NACA airfoils, one unit long, to be scaled and placed.
* Take the edges for a closing face from the surface it is to close.

:ref:`surface_modeling` lists the other ways of making a surface.
