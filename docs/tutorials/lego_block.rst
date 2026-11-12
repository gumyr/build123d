.. _tutorial_lego_block:

############
A Lego block
############

The tutorials before this one each introduced something new. This one does
not. It takes what they taught and uses it to build one familiar object from
start to finish: a Lego block of any size - a 2x4, a 1x8, a brick or a
plate - which ends up as a ``LegoBlock`` object of your own.

.. image:: /tutorials/assets/lego_block/brick_finished.svg
    :align: center
    :width: 60%

The block looks simple from above. Nearly all of its detail is underneath -
thin walls, small ridges on the inside of them, and a row of tubes that the
studs of the block below push against:

.. image:: /tutorials/assets/lego_block/brick_underside.svg
    :align: center
    :width: 60%

All of that detail is the same from the bottom of the walls to the top, so
all of it can be drawn flat, in one sketch, and extruded once. Most of this
tutorial is the making of that sketch. It uses:

* a sketch and ``extrude``, and ``offset`` to make a wall, from
  :ref:`tutorial_sketch_then_extrude`;
* ``GridLocations``, from :ref:`tutorial_placing_features`;
* a sketch on a selected face, from
  :ref:`tutorial_selecting_and_finishing`;
* a sketch on a plane at a height, from :ref:`tutorial_beyond_extrude`; and
* a custom object, from :ref:`tutorial_parametric_part`.

It takes about twenty-five minutes. How the builder and algebra tabs on this page
work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the block, in
millimetres.

.. literalinclude:: /tutorials/lego_block.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The first line says which block to make, in the terms Lego builders use:

* A block is named by its **studs**, the round bumps on its top, with the
  smaller number first. ``studs_wide, studs_long = 2, 6`` is a 2x6.
* Its height is counted in **plates**. A *plate* is the thin block, 3.2 mm
  high, and a *brick* is three plates high, so ``plates`` is 3 for a brick
  and 1 for a plate.

The lines after it are the sizes that every block shares, whatever its
shape. ``unit_size`` is the distance from one stud to the next and
``plate_height`` is the height of one plate; the rest are the sizes of the
features, which the steps below introduce one at a time. The last two lines
calculate the length, width and height of this block from all of that.

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*****************************************
Step 2: The outline and its walls
*****************************************

Begin with the block seen from above: a rectangle, with a smaller one taken
out of it to leave a wall.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [walls_builder]
            :end-before: [walls_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [walls_algebra]
            :end-before: [walls_algebra]

.. image:: /tutorials/assets/lego_block/brick_walls.svg
    :align: center
    :width: 70%

This is the rim of the first tutorial again. ``offset`` with a negative
amount makes a copy of the rectangle that is ``wall_thickness`` smaller all
round, and subtracting the copy leaves the walls.

***************************************
Step 3: Bars across the block
***************************************

The inside of each wall has small ridges on it, in line with the studs. There
are a lot of them and they sit on four different walls, which sounds like a
lot of positioning. It is not, if they are drawn as something simpler
first: thin bars running right across the block.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [bars_builder]
            :end-before: [bars_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [bars_algebra]
            :end-before: [bars_algebra]

.. image:: /tutorials/assets/lego_block/brick_bars.svg
    :align: center
    :width: 70%

Two grids of bars are added, shown in red. A ``GridLocations`` with a count
of 1 in one direction is a row:

* the first is one column of ``studs_wide`` places, ``unit_size`` apart in
  Y, and a long thin rectangle at each makes the lengthwise bars;
* the second is one row of ``studs_long`` places along X, and a tall thin
  rectangle at each makes the bars across.

Each bar is ``ridge_width`` thick and crosses the whole block, so both of
its ends are buried in a wall.

*********************************************
Step 4: Cut the bars back to ridges
*********************************************

Now take the middle out. One rectangle, a little smaller than the inside of
the walls, removes all of each bar except its two ends.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [ridges_builder]
            :end-before: [ridges_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [ridges_algebra]
            :end-before: [ridges_algebra]

.. image:: /tutorials/assets/lego_block/brick_ridges.svg
    :align: center
    :width: 70%

The rectangle is smaller than the inside of the block by ``ridge_depth`` on
every side, and that is how far each ridge is left standing out from its
wall.

Sixteen ridges on four walls have been made with three rectangles and two
grids, and not one of them was positioned by hand. *Draw more than you
need, then cut back* is worth remembering: it is very often less work than
drawing exactly what you need.

*****************************
Step 5: Tubes, or posts
*****************************

What grips the studs of the block below depends on the block. One that is
two or more studs wide has tubes: rings, each a circle with a smaller
circle taken out, sitting in the middle of every square of four studs. That
is one fewer than the studs in each direction. A block one stud wide has no
room for tubes and has small solid posts between its studs instead. A 1x1
has neither.

That is a choice, and a choice in build123d is made in plain Python, with
``if``.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [supports_builder]
            :end-before: [supports_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [supports_algebra]
            :end-before: [supports_algebra]

.. image:: /tutorials/assets/lego_block/brick_supports.svg
    :align: center
    :width: 70%

A 2x6 takes the first branch. In builder mode both circles are inside the
one ``GridLocations``, so each is made at every place: five circles added,
then five subtracted. In algebra mode the grid is given a name, ``tubes``,
and used twice.

The second branch is not used by this block, but it is drawn all the same,
so that the plan is right for any block. A sketch does not have to be a
fixed list of shapes: the code that draws it can decide what to draw. This
is the underside of a 1x4, which takes that branch:

.. image:: /tutorials/assets/lego_block/brick_posts.svg
    :align: center
    :width: 55%

The plan of the block is now complete.

*********************************
Step 6: Extrude the plan
*********************************

One ``extrude`` turns the whole plan into the walls, ridges and tubes. They
are ``wall_thickness`` shorter than ``base_height``, the height of the
block without its studs, to leave room for its top.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [extrude_builder]
            :end-before: [extrude_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [extrude_algebra]
            :end-before: [extrude_algebra]

.. image:: /tutorials/assets/lego_block/brick_extrude.svg
    :align: center
    :width: 60%

In builder mode the sketch has moved inside a ``BuildPart``, as in the
earlier tutorials.

Everything in this picture came from the one sketch. To make these features
as solids - a hollowed box, sixteen small blocks for ridges, five tubes -
would have taken a good deal more code and many more operations on solids,
which, as :ref:`tutorial_combining_solids` explained, is the harder and
less reliable way round.

***************************
Step 7: Close the top
***************************

The top of the block is a plain slab. It is one more sketch - the outline
of the block again - drawn on a plane at the height where the walls end,
and extruded by ``wall_thickness``.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [lid_builder]
            :end-before: [lid_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [lid_algebra]
            :end-before: [lid_algebra]

.. image:: /tutorials/assets/lego_block/brick_lid.svg
    :align: center
    :width: 60%

``Plane.XY.offset(...)`` is the plane at a height from
:ref:`tutorial_beyond_extrude`. Its height is written in terms of the same
two names as the extrusion in step 6, so the slab always sits exactly on
top of the walls.

**********************
Step 8: The studs
**********************

Last, the studs. They stand on the top of the block, so select the top face
and sketch on it: a grid of circles, ``studs_long`` by ``studs_wide``.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [studs_builder]
            :end-before: [studs_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [studs_algebra]
            :end-before: [studs_algebra]

.. image:: /tutorials/assets/lego_block/brick_finished.svg
    :align: center
    :width: 60%

The top face is the highest one, ``faces().sort_by(Axis.Z)[-1]``, exactly
as in :ref:`tutorial_selecting_and_finishing`. A sketch on that face has
its origin at the middle of the face, which is where the grid needs to be
centred, and ``extrude`` raises the circles out of it by ``stud_height``.

In algebra mode ``Plane(top) * GridLocations(...) * Circle(...)`` makes a
list of twelve circles, and ``Sketch(...)`` gathers them into one sketch to
extrude.

The shape is finished. Turn it over in your viewer and look at the
underside.

Change the first line of the file to ``1, 8, 3`` for a 1x8 brick, or to
``2, 4, 1`` for a 2x4 plate. The walls, the ridges, the tubes or posts and
the studs all follow, because every one of them was placed by a grid that
counts from those three numbers.

**********************************
Step 9: Make it an object
**********************************

The file makes one block, and to make another you have to edit it. A Lego
block is the very model of a part that is wanted more than once, so finish
the job as :ref:`tutorial_parametric_part` did: make it a custom object,
with its parameters passed in. Replace everything below the import with
this:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [object_builder]
            :end-before: [object_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/lego_block.py
            :language: build123d
            :start-after: [object_algebra]
            :end-before: [object_algebra]

These are the four parts that every custom object has:

#. ``class LegoBlock(BasePartObject)`` says that a ``LegoBlock`` is a part.
#. The arguments of ``__init__`` are the three numbers that name a block -
   ``studs_wide``, ``studs_long`` and ``plates`` - followed by ``rotation``,
   ``align`` and ``mode``, as on every built-in object. ``plates`` is 3
   unless you say otherwise, so ``LegoBlock(2, 4)`` is a 2x4 brick and
   ``LegoBlock(2, 4, plates=1)`` is a 2x4 plate.
   Each argument is given its type, as in
   :ref:`tutorial_parametric_part`; the three numbers are ``int``, because
   a block cannot have half a stud.
#. The body is the code of step 8.
#. ``super().__init__`` is handed the finished shape, with ``rotation``,
   ``align`` and ``mode``.

The sizes that every block shares are not arguments. A stud is 4.8 mm
across on every Lego block there is, and nobody making a block should be
asked for it. Those sizes are written once, directly under the ``class``
line, which makes them **class attributes**: values that belong to
``LegoBlock`` itself and not to any one block. Inside ``__init__`` each is
read with ``self.`` in front, as in ``self.unit_size``, and that is the only
change to the code of step 8.

The rule is a general one. *What varies from one part to the next is an
argument; what is fixed for the whole family belongs to the class.*

Two more things are new:

* The ``if`` at the top of ``__init__`` refuses a block whose numbers are
  the wrong way round. An object that other code will use should check what
  it is given.
* The last lines record what the block is - its three numbers, its
  ``base_height``, and a ``label`` such as ``Lego brick 2x6`` for a viewer
  to show beside it.

Everything a ``LegoBlock`` needs is now inside it, which is why the names
at the top of the file could be deleted.

*********************
Step 10: Use it
*********************

A block is now one short line, and three of them make a stack. This step is
the same in both modes.

.. literalinclude:: /tutorials/lego_block.py
    :language: build123d
    :start-after: [stack]
    :end-before: [stack]

.. code-block:: text

    Lego brick 2x6
    Lego plate 2x4
    Lego brick 1x4

.. image:: /tutorials/assets/lego_block/brick_stack.svg
    :align: center
    :width: 60%

A 2x4 plate sits on a 2x6 brick, and a 1x4 brick sits on the plate. Every
distance is read back, none is typed in: ``LegoBlock.unit_size`` is the
class attribute, asked for from the class itself, and ``base_height`` is
the value each block stored. Moving a ``LegoBlock`` gives a ``LegoBlock``,
so the moved blocks still have their labels.

The blocks are not added together. They are separate parts that happen to
touch, so they are gathered into an assembly with
``Compound(children=[...])``, in which each keeps its own shape and label.

Because ``LegoBlock`` is built on ``BasePartObject`` it also works wherever
a ``Box`` would: inside a ``BuildPart``, at every place of a ``Locations``
or ``GridLocations``, and with ``mode=Mode.SUBTRACT`` to cut a block-shaped
pocket.

Class attributes have one more use. A different system of blocks is a
subclass that changes them and nothing else:

.. literalinclude:: /tutorials/lego_block.py
    :language: build123d
    :start-after: [subclass]
    :end-before: [subclass]

``BigBlock`` has no ``__init__`` of its own. It uses the one in
``LegoBlock``, which reads every size through ``self`` and so finds the new
values.

********************
What you learned
********************

Nothing here was new, and that is the point: a part with this much detail,
and an object to make it with, needed only the tools of the earlier
tutorials.

* Look for the direction in which a part does not change. Everything that
  is constant along it belongs in one sketch.
* Draw more than you need and cut back. Bars across the block, trimmed by
  one rectangle, were less work than sixteen separate ridges.
* A ``GridLocations`` with a count of 1 is a row or a column.
* Count features from a parameter, and the part follows when the parameter
  changes.
* Where the part itself differs from one size to another, a plain ``if``
  in the sketch chooses what to draw.
* Build upwards from faces and planes that the part itself defines, so that
  each feature lands on the one below it.
* When the part works, make it a custom object. What varies from one part
  to the next becomes an argument, what is fixed for the whole family
  becomes a class attribute, and a subclass can change the family.
