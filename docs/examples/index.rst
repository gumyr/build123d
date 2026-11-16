.. _examples:

########
Examples
########

Finished models with their code. Every example is written twice, in builder
mode and in algebra mode, and the two versions make the same model: open
"Code" under an example and choose a tab. :ref:`builder_and_algebra`
describes the two modes.

The scripts are in the `examples folder
<https://github.com/gumyr/build123d/tree/dev/examples>`_ of the GitHub
repository, as ``name.py`` for builder mode and ``name_algebra.py`` for
algebra mode. The folder holds further scripts that are not shown here.

.. ----------------------------------------------------------------------------------------------
.. Index Section
.. ----------------------------------------------------------------------------------------------


.. grid:: 3

    .. grid-item-card:: Benchy
        :img-top:  /examples/assets/thumbnail_benchy_01.png
        :link: examples-benchy
        :link-type: ref

    .. grid-item-card:: Bicycle Tire
        :img-top:  /examples/assets/bicycle_tire.png
        :link: examples-bicycle_tire
        :link-type: ref

    .. grid-item-card:: Bracelet
        :img-top:  /examples/assets/bracelet.png
        :link: examples-bracelet
        :link-type: ref

    .. grid-item-card:: Canadian Flag Blowing in The Wind
            :img-top: /examples/assets/example_canadian_flag_01.png
            :link: examples-canadian_flag
            :link-type: ref

    .. grid-item-card:: Cast Bearing Unit
            :img-top: /examples/assets/cast_bearing_unit.png
            :link: examples-cast_bearing_unit
            :link-type: ref

    .. grid-item-card:: Circuit Board With Holes
            :img-top: /examples/assets/thumbnail_circuit_board_01.png
            :link: examples-circuit_board
            :link-type: ref

    .. grid-item-card:: Clock Face
            :img-top: /examples/assets/clock_face.png
            :link: clock_face
            :link-type: ref

    .. grid-item-card:: Fast Grid Holes
            :img-top: /examples/assets/fast_grid_holes.png
            :link: fast_grid_holes
            :link-type: ref

    .. grid-item-card:: Handle
            :img-top: /examples/assets/handle.png
            :link: handle
            :link-type: ref

    .. grid-item-card:: Heat Exchanger
            :img-top: /examples/assets/heat_exchanger.png
            :link: heat_exchanger
            :link-type: ref

    .. grid-item-card:: Key Cap
            :img-top: /assets/examples/key_cap.png
            :link: key_cap
            :link-type: ref

    .. grid-item-card:: (former) build123d Logo
            :img-top: /examples/assets/thumbnail_build123d_logo_01.png
            :link: examples-build123d_logo
            :link-type: ref

    .. grid-item-card:: Maker Coin
            :img-top: /examples/assets/maker_coin.png
            :link: maker_coin
            :link-type: ref

    .. grid-item-card:: Multi-Sketch Loft
            :img-top: /examples/assets/loft.png
            :link: multi_sketch_loft
            :link-type: ref

    .. grid-item-card:: Peg Board J Hook
            :img-top: /examples/assets/peg_board_hook.png
            :link: peg_board_hook
            :link-type: ref

    .. grid-item-card:: Platonic Solids
            :img-top: /examples/assets/platonic_solids.png
            :link: platonic_solids
            :link-type: ref

    .. grid-item-card:: Playing Cards
            :img-top: /examples/assets/playing_cards.png
            :link: playing_cards
            :link-type: ref

    .. grid-item-card:: Spring
            :img-top: /examples/assets/spring.svg
            :link: spring
            :link-type: ref

    .. grid-item-card:: Stud Wall
            :img-top: /examples/assets/stud_wall.png
            :link: stud_wall
            :link-type: ref

    .. grid-item-card:: Tea Cup
            :img-top: /examples/assets/tea_cup_example.png
            :link: tea_cup
            :link-type: ref

    .. grid-item-card:: Toy Truck
            :img-top: /assets/examples/toy_truck.png
            :link: toy_truck
            :link-type: ref

    .. grid-item-card:: Vase
            :img-top: /examples/assets/vase.png
            :link: vase
            :link-type: ref

.. NOTE 01: insert new example thumbnails above this line

.. To add an example, copy this card above the NOTE 01 line:

    .. grid-item-card:: {Name Of Your Example}
            :img-top: /examples/assets/{name_of_your_example}.png
            :link: examples-{name_of_your_example}
            :link-type: ref

.. ----------------------------------------------------------------------------------------------
.. Details Section
.. ----------------------------------------------------------------------------------------------

.. _examples-benchy:

Benchy
------
.. image:: /examples/assets/example_benchy_01.png
    :align: center

An STL model imported as a solid and then modified. :class:`~mesher.Mesher`
reads the mesh and returns a ``Solid``, so everything that works on a
solid works on it: here the faceted chimney is cut off with
:func:`~operations_generic.split` at a plane found from the roof's
vertices, and a round one is built in its place from the position and size
of the old one. :ref:`import_export` covers importing meshes.

- Benchy STL model: :download:`low_poly_benchy.stl </../examples/low_poly_benchy.stl>`

.. note::

     *Attribution:*
     The low-poly-benchy used in this example is by `reddaugherty`, see
     https://www.printables.com/model/151134-low-poly-benchy.

.. dropdown:: More images

    .. image:: /examples/assets/example_benchy_02.png
        :align: center

    .. image:: /examples/assets/example_benchy_03.png
        :align: center

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/benchy.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/benchy_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. ----------------------------------------------------------------------------------------------

.. _examples-bicycle_tire:

Bicycle Tire
------------
.. image:: /examples/assets/bicycle_tire.png
    :align: center

A bicycle tire with a patterned tread. The key technique is
``Face.wrap_faces``, which lays flat geometry onto a curved surface.
Wrapping writes the flat tread blocks into the tire surface's own parameter
space, so it is exact and respects the surface's seam; it works on one face
at a time. The wrapped faces are thickened into blocks, and one unit of the
tread is copied round the tire. Compare the Bracelet below, where a label
runs over several faces of a solid and is projected instead.

:ref:`tutorial_bicycle_tire` builds this tire step by step, and goes on to
add lettering to the sidewall.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/bicycle_tire.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/bicycle_tire_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _examples-bracelet:

Bracelet
--------
.. image:: /examples/assets/bracelet.png
    :align: center

A doubly-curved bracelet with an optional embossed label.

This model is a good stress test for the geometric kernel because most of
its boundary surfaces are *freeform*, not planes, cylinders or spheres. It
is assembled from:

- a swept centre section, using a curved solid end-face as the sweep profile
- two freeform tip caps built as Gordon surfaces, from a network of curves
- an optional text label projected onto the curved solid and thickened
- alignment holes for splitting, printing and assembly

Key techniques:

- ``location_at``, ``position_at`` and the tangent operator ``%`` to take
  local frames and tangents from a curve
- projecting a curve onto a surface that is not flat, to make a true 3D
  guide curve
- ``Face.make_gordon_surface`` to build a doubly-curved skin;
  :ref:`surface_modeling` explains making a solid from faces
- ``Shape.project_faces`` to put text onto a solid; the label spans more
  than one face of the solid, which a wrap of a single face cannot do

The curves and surfaces of the tip are made one at a time from one another,
so that part of the script is the same in both modes. They differ in how
the pieces are put together.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/bracelet.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/bracelet_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _examples-build123d_logo:

Former build123d Logo
---------------------
.. image:: /examples/assets/example_build123d_logo_01.png
    :align: center

The logo build123d used until the end of 2023, made from text and lines.
The lettering is :class:`~objects_sketch.Text`, with the "3d" extruded and
the "1" drawn as a line and an arc. Beneath it is a dimension line in the
style of a drawing: two extension lines, and arrowheads made from one arc
and its :func:`~operations_generic.mirror` image. The builder version also
writes the result to ``logo.svg`` with :class:`~exporters.ExportSVG`.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/build123d_logo.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/build123d_logo_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _examples-cast_bearing_unit:

Cast Bearing Unit
-----------------
.. image:: /examples/assets/cast_bearing_unit.png
    :align: center

A flanged bearing housing designed to be cast. The outline of the flange is
the :func:`~operations_sketch.make_hull` of the housing and the two bolt
bosses, and :func:`~operations_part.draft` leans the upright faces by four
degrees so that the part will release from its mould. The bolt holes are
placed with the same :class:`~build_common.GridLocations` that placed the
bosses. :ref:`why_build123d` discusses this part.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/cast_bearing_unit.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/cast_bearing_unit_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _examples-canadian_flag:

Canadian Flag Blowing in The Wind
---------------------------------
.. image:: /examples/assets/example_canadian_flag_01.png
    :align: center

A flag blowing in the wind, made by projecting flat faces onto a curved one.

* The wind is a surface through a grid of calculated points, made with
  ``Face.make_surface_from_array_of_points``.
* The maple leaf is half an outline of lines and arcs, each starting where
  the last ended (``@``) and several leaving in its direction (``%``), then
  mirrored. :ref:`drawing_with_constraints` covers this way of drawing.
* The two red fields, the white field and the leaf are each projected onto
  the wind with ``Face.project_to_shape``. :ref:`projection_shape` explains
  projection onto a shape.

.. dropdown:: More images

    .. image:: /examples/assets/example_canadian_flag_02.png
        :align: center

    .. image:: /examples/assets/example_canadian_flag_03.png
        :align: center

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/canadian_flag.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/canadian_flag_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _examples-circuit_board:

Circuit Board With Holes
------------------------
.. image:: /examples/assets/example_circuit_board_01.png
    :align: center

A board with rows of holes round its edge and a mounting hole in each
corner. The interest is in how the positions of the holes are produced:

* Builder mode names them with :class:`~build_common.Locations`, and every
  ``Circle`` made inside the block is made at each one.
* Algebra mode works them out with ``itertools.product`` and ``range``, and
  subtracts a list of placed circles.
* Both use :class:`~build_common.GridLocations` for the four corner holes.

The holes are cut from the sketch, which is then extruded once.
:ref:`tutorial_placing_features` teaches the patterns used here.

.. dropdown:: More images

    .. image:: /examples/assets/example_circuit_board_02.png
        :align: center

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/circuit_board.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/circuit_board_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _clock_face:

Clock Face
----------
.. image:: /examples/assets/clock_face.png
    :align: center

A clock face as a sketch: a circular outline, hour numerals, slots, and a
minute indicator drawn from arcs and lines and turned into a face with
:func:`~operations_sketch.make_face`, with its corners filleted.

:class:`~build_common.PolarLocations` places the numerals, the slots and
the indicators round the face. :ref:`tutorial_placing_features` covers
polar patterns.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/clock.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/clock_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _fast_grid_holes:

Fast Grid Holes
---------------
.. image:: /examples/assets/fast_grid_holes.png
    :align: center

An efficient way to make a large number of holes, 625 here, in a flat part.

Cutting each hole from the part, or even from the sketch, means a boolean
operation that has to consider every hole. This example avoids the boolean
altogether: it makes a ``Face`` directly from an outer wire and a list of
hole wires, and extrudes that face once.

The hexagonal pattern comes from :class:`~build_common.HexLocations`, and a
hexagonal wire is placed at each location. In builder mode the shapes the
wires are taken from are made with ``Mode.PRIVATE``, so that they do not
join the sketch, and the finished face is put into it with ``insert``.
:ref:`algebra_performance` discusses the cost of combining many objects.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/fast_grid_holes.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/fast_grid_holes_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _handle:

Handle
------
.. image:: /examples/assets/handle.png
    :align: center

A drawer handle made with a multisection sweep. The path is a
:class:`~objects_curve.Spline`. Cross sections are placed along it with the
``^`` operator, which gives a location on the path facing along it: circles
at the two ends and rounded rectangles between. ``sweep(multisection=True)``
then blends from each section to the next as it follows the path.
:ref:`tutorial_beyond_extrude` introduces ``sweep``.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/handle.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/handle_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _heat_exchanger:

Heat Exchanger
--------------
.. image:: /examples/assets/heat_exchanger.png
    :align: center

A parametric heat exchanger core. The tubes are placed with
:class:`~build_common.HexLocations`, and the pattern is then limited to the
tubes that fit within the circular end plates. The ends of the tubes are
filleted to the plates to simulate welding, and one half is mirrored to
make the other.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/heat_exchanger.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/heat_exchanger_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _key_cap:

Key Cap
-------
.. image:: /assets/examples/key_cap.png
    :align: center

A Cherry MX key cap. The body is an extrusion with a ``taper``, hollowed
with :func:`~operations_generic.offset`, and the stem that fits the switch
is extruded up to the inside of the cap with ``until=Until.NEXT``.

:ref:`tutorial_key_cap` builds this part step by step and explains each
choice.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/key_cap.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/key_cap_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _maker_coin:

Maker Coin
----------
.. image:: /examples/assets/maker_coin.png
    :align: center

The maker coin defined by Angus on the Maker's Muse YouTube channel. There
are two key features:

#. :class:`~objects_curve.DoubleTangentArc` makes the smooth transition
   from the central dish to the arc of the rim, and

#. the text is embossed into the top of the coin not by a simple extrude
   but from a projection onto the dished surface, which gives lettering of
   even depth. :ref:`projection_shape` explains projecting onto a shape.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/maker_coin.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/maker_coin_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _multi_sketch_loft:

Multi-Sketch Loft
-----------------
.. image:: /examples/assets/loft.png
    :align: center

A hollow form lofted through a series of sketches on offset planes with
:func:`~operations_part.loft`. The flat top and bottom faces are selected
by their type, with ``filter_by(GeomType.PLANE)``, and given to
:func:`~operations_generic.offset` as openings, which shells the part and
leaves both ends open. :ref:`tutorial_beyond_extrude` introduces ``loft``.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/loft.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/loft_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _peg_board_hook:

Peg Board Hook
--------------
.. image:: /examples/assets/peg_board_hook.png
    :align: center

A J-shaped hook for a pegboard, of the kind used to hang tools in a
workshop. The hook is one path, built from lines and
:class:`~objects_curve.JernArc` arcs that each continue from the end of the
last, with a circle swept along it. The sides are then cut flat with
:func:`~operations_generic.split`, so that the hook can be 3D printed lying
down.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/pegboard_j_hook.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/pegboard_j_hook_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _platonic_solids:

Platonic Solids
---------------
.. image:: /examples/assets/platonic_solids.png
    :align: center

A custom part object, ``PlatonicSolid``.

The Platonic solids are the five convex solids whose faces are all the same
regular polygon, with the same number meeting at each vertex: the
tetrahedron (4 triangular faces), cube (6 square faces), octahedron (8
triangular faces), dodecahedron (12 pentagonal faces) and icosahedron (20
triangular faces).

The class finds the faces of each solid as the convex hull of its vertices,
builds a ``Face`` for each, and sews them into a ``Shell`` and a ``Solid``.
It derives from ``BasePartObject``, so it takes ``rotation``, ``align`` and
``mode`` like any built-in part and works in both modes. The class is the
same in both versions; they differ in how the five solids are placed.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/platonic_solids.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/platonic_solids_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _playing_cards:

Playing Cards
-------------
.. image:: /examples/assets/playing_cards.png
    :align: center

Custom sketch objects: ``Club``, ``Spade``, ``Heart``, ``Diamond`` and
``PlayingCard``, together with a two-part box for a deck of cards with the
suits cut out of its lid. The four suits are drawn with Bézier curves that
were imported as code from an SVG file and then edited.

Each suit draws half its outline and mirrors it. ``PlayingCard`` uses the
suit objects in turn, subtracting them and the rank from a rounded
rectangle, with :class:`~build_common.PolarLocations` arranging the pips in
the middle.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/playing_cards.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/playing_cards_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _spring:

Spring
------
.. image:: /examples/assets/spring.svg
    :align: center

A compression spring made by sweeping a circular profile along a
:class:`~objects_curve.Helix`. ``path ^ 0`` is the location at the start of
the path, facing along it, and placing the profile there sets it square to
the helix before the sweep.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/spring.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/spring_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _stud_wall:

Stud Wall
---------
.. image:: /examples/assets/stud_wall.png
    :align: center

Custom part objects put together into assemblies. ``Stud`` is a framing
stud as used in building, and ``StudWall`` is an assembly made from copies
of one ``Stud``, which share their geometry. Both carry
:class:`~joints.RigidJoint` objects as snap points, and every piece is
positioned by attaching one joint to another: the studs to the sole plate,
the top plate to a stud, and one wall to the other. :ref:`joints` covers
joints, and :ref:`assembly` covers assemblies and shared copies.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/stud_wall.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/stud_wall_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _tea_cup:

Tea Cup
-------
.. image:: /examples/assets/tea_cup_example.png
    :align: center

A tea cup, as an example of a shape with no flat sides made in a short
script.

* **Revolve.** Half the outline of the bowl is drawn with a
  :class:`~objects_curve.Spline` and revolved about the Z axis.
* **Offset.** The bowl is hollowed with
  :func:`~operations_generic.offset`, leaving the top open.
* **Fillet.** Every edge is rounded in one call.
* **Sweep.** The handle is a rounded rectangle swept along a spline whose
  ends are found by intersecting the bowl with two horizontal axes, so the
  handle follows the bowl if the bowl changes.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/tea_cup.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/tea_cup_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _toy_truck:

Toy Truck
---------
.. image:: /assets/examples/toy_truck.png
    :align: center

.. image:: /examples/assets/toy_truck_picture.jpg
    :align: center

A toy truck made of two parts, a body and a cab, joined with joints. The
body includes fenders, wheel wells, a grill and a bumper. The example shows
a sketch used twice, tapered extrusions, work on one half followed by a
mirror, fillets applied to edges selected by position, and
:class:`~joints.RigidJoint` to mount the cab on the body.
:ref:`tutorial_selecting_and_finishing` covers selecting edges this way.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/toy_truck.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/toy_truck_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. _vase:

Vase
----
.. image:: /examples/assets/vase.png
    :align: center

A vase, showing a revolved profile, shelling, and selecting edges for
fillets.

* **Sketch and revolve.** The side view of the vase is drawn as an outline
  and revolved into a solid.
* **Shell.** :func:`~operations_generic.offset` removes the inside, with
  the top face as the opening.
* **Fillet.** The edges to round are selected by where they are and what
  they are, with ``filter_by_position`` and ``filter_by``, and not by
  number. :ref:`selecting_features` covers selecting this way.

.. dropdown:: Code

    .. tab-set::

        .. tab-item:: Builder
            :sync: builder

            .. literalinclude:: /../examples/vase.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

        .. tab-item:: Algebra
            :sync: algebra

            .. literalinclude:: /../examples/vase_algebra.py
                :language: build123d
                :start-after: [Code]
                :end-before: [End]

.. NOTE 02: insert new example entries above this line


.. and copy this entry above the NOTE 02 line. Every example has a builder
   version, examples/{name}.py, and an algebra version,
   examples/{name}_algebra.py, that make the same model. Each marks the code
   to show, imports included, with "# [Code]" and "# [End]" comments.

    .. _examples-{name_of_your_example}:

    {Name Of Your Example}
    ----------------------
    .. image:: /examples/assets/{name_of_your_example}.png
        :align: center

    What the example shows, and the techniques it uses, with links to the
    tutorial or how-to guide that covers each.

    .. dropdown:: Code

        .. tab-set::

            .. tab-item:: Builder
                :sync: builder

                .. literalinclude:: /../examples/{name_of_your_example}.py
                    :language: build123d
                    :start-after: [Code]
                    :end-before: [End]

            .. tab-item:: Algebra
                :sync: algebra

                .. literalinclude:: /../examples/{name_of_your_example}_algebra.py
                    :language: build123d
                    :start-after: [Code]
                    :end-before: [End]
