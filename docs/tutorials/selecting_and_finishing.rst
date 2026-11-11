.. _tutorial_selecting_and_finishing:

#######################
Selecting and finishing
#######################

A sketch decides the shape of a part. What is left - rounding an edge,
breaking a sharp corner, putting a hole in a face - is done to the solid,
and to do it you have to say *which* edge or *which* face. In a traditional
CAD program you click on it. In build123d you describe it: "the vertical
edges", "the highest face", "the edges that were just made". In this
tutorial you will finish this bearing pedestal that way:

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_lead_in.svg
    :align: center
    :width: 60%

Along the way you will:

* ask a part for its edges and faces,
* narrow them down by direction, by position, by what was last made, and by
  what kind of thing they are,
* round edges with ``fillet`` and bevel them with ``chamfer``,
* use a selected face as the place for the next sketch, and
* put holes into a selected face.

It takes about thirty minutes and follows on from
:ref:`tutorial_placing_features`. How the builder and algebra tabs on this
page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the pedestal,
in millimetres.

.. literalinclude:: /tutorials/selecting_and_finishing.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*********************
Step 2: The block
*********************

The pedestal starts as a plain rectangular block: a sketch, extruded.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [block_builder]
            :end-before: [block_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [block_algebra]
            :end-before: [block_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_block.svg
    :align: center
    :width: 55%

**************************************
Step 3: Ask the part for its edges
**************************************

The four upright corners of the block are to be rounded.
:func:`~operations_generic.fillet` rounds edges, and it needs to be told
which ones.

A part will list what it is made of. ``pedestal.edges()`` gives every edge
of the block, all twelve, and ``pedestal.faces()`` and
``pedestal.vertices()`` do the same for its six faces and eight corners.
Each returns a list, and the list can narrow itself down.
``filter_by(Axis.Z)`` keeps only the edges that run in the Z direction:

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_corners_selected.svg
    :align: center
    :width: 55%

Those four are what ``fillet`` is given.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [corners_builder]
            :end-before: [corners_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [corners_algebra]
            :end-before: [corners_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_corners.svg
    :align: center
    :width: 55%

It is the same ``fillet``, given the same edges, in both modes. In builder
mode it changes the part being built. In algebra mode it returns the
rounded part, which is assigned back to ``pedestal``.

Notice what was *not* written: no coordinates, and no edge numbers. "The
edges that run along Z" stays true if the block is made longer, wider or
taller, so the selection keeps working when the dimensions change.

This matters more than it may seem. Many CAD programs remember "the edge
you clicked" by an internal name or number, and when an earlier step of
the design changes, those names can end up pointing at a different edge or
at nothing. It is known as the *topological naming problem*. A selection
written as a description has no such name to go stale.

For the same reason, do not pick an edge by its position in the list a part
gives you. ``pedestal.edges()[3]`` is some edge today, but the order of
that list is not promised and can change when the part does. Always narrow
the list down by a description first. An index is safe after a ``sort_by``
or a ``group_by``, because then the order means something.

.. tip::

    **Look at a selection before you use it.** A selector that finds the
    wrong edges, or none at all, is the most common problem when starting
    out, and it is hard to spot from the error a ``fillet`` then gives.
    Whenever a selection is not doing what you expect, assign it to a
    variable first and check it:

    .. code-block:: build123d

        corners = pedestal.edges().filter_by(Axis.Z)
        print(len(corners))
        show(pedestal, corners)

    ``print(len(corners))`` says how many edges were found - four here - and
    showing the selection together with the part draws those edges on it,
    much as the picture above does. Once it is right, pass the variable to
    the operation: ``fillet(corners, radius=corner_radius)``. This works for
    every selection in this tutorial, faces included, and in both modes.
    :ref:`hello_world` describes ways to view a model.

.. note::

    Corners like these could have been rounded in the sketch, with
    ``RectangleRounded``, and in your own work that is the better place for
    them. They are rounded on the solid here because they are the simplest
    edges to practise selecting. The rest of this tutorial works on edges
    and faces that no sketch can reach.

***************************
Step 4: Edges by height
***************************

Next, the top edge of the block gets a small bevel so that it is not sharp.
:func:`~operations_generic.chamfer` does that, and again the question is
which edges.

Direction will not pick them out: the top edge runs all the way round. What
they have in common is their height. ``group_by(Axis.Z)`` sorts the edges
into groups by how far up Z they are, lowest first. The block now has three
groups - the bottom edges, the upright ones, and the top edges - and
``[-1]`` takes the last, which is the highest.

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_top_edge_selected.svg
    :align: center
    :width: 55%

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [top_edge_builder]
            :end-before: [top_edge_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [top_edge_algebra]
            :end-before: [top_edge_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_top_edge.svg
    :align: center
    :width: 55%

``filter_by`` and ``group_by`` are two of the three tools a list of edges
or faces has. The third, ``sort_by``, is next.

******************************
Step 5: A face to build on
******************************

A round boss stands on top of the block to carry the bearing. It is a
circle, extruded - the method of the first tutorial - but the circle has to
be drawn on top of the block, not on the floor.

So select the top face. ``sort_by(Axis.Z)`` puts the faces in order of
height, and ``[-1]`` is the highest one. Where ``group_by`` gave a group
of edges, ``sort_by`` gives a single face:

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_boss_selected.svg
    :align: center
    :width: 55%

In :ref:`tutorial_placing_features` a sketch was placed on ``Plane.XZ``. A
face can be used in the same way, and the sketch is then drawn on that
face, centred on it.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [boss_builder]
            :end-before: [boss_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [boss_algebra]
            :end-before: [boss_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_boss.svg
    :align: center
    :width: 55%

The face is given a name, ``top``, because it will be needed again. In
builder mode it is passed to ``BuildSketch``; in algebra mode ``Plane(top)``
makes a plane from it and the circle is placed there with ``*``, as before.
Either way ``extrude`` pushes the circle up out of the face, and the boss
joins the block.

The height of the block was never mentioned. If ``base_height`` changes,
the top face moves and the boss moves with it.

******************************
Step 6: What was just made
******************************

A sharp inside corner where the boss meets the block is a weak point, so it
gets a fillet. This edge is harder to describe by where it is. It is easy
to describe by *when*: it is one of the edges the last step created.

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_blend_selected.svg
    :align: center
    :width: 55%

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [blend_builder]
            :end-before: [blend_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [blend_algebra]
            :end-before: [blend_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_blend.svg
    :align: center
    :width: 55%

``Select.LAST`` is how to ask for them, and it is the same in both modes:
a part remembers which of its edges the last operation made, and
``pedestal.edges(Select.LAST)`` returns only those. ``faces`` and
``vertices`` take it too.

Adding the boss made three new edges: the circle round its top, the circle
round its foot, and a seam up its side. ``sort_by(Axis.Z)[0]`` takes the
lowest of the three, the one at the foot.

***************************
Step 7: Holes on a face
***************************

Two kinds of hole come next: a bore down through the boss for the
bearing, and four counterbored holes in the base for its fixing screws.
Each starts from a face.

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_holes_selected.svg
    :align: center
    :width: 55%

:class:`~objects_part.Hole` and :class:`~objects_part.CounterBoreHole` are
ready-made features that cut downwards from the place they are created at.
The bore goes at the highest face, selected exactly as in step 5 - it is
now the top of the boss. The screw holes go on ``top``, the face named in
step 5, in the two by two grid from :ref:`tutorial_placing_features`.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [holes_builder]
            :end-before: [holes_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [holes_algebra]
            :end-before: [holes_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_holes.svg
    :align: center
    :width: 60%

A face is a place, like the points and patterns of the last tutorial, so it
goes where they went: in a ``Locations`` block in builder mode, and on the
left of a ``*`` in algebra mode. The grid nests inside it, and is laid out
on the face.

One difference between the modes does show here. In builder mode a hole knows
the part it is cutting and goes all the way through it unless told
otherwise. In algebra mode the hole is a shape on its own until it is
subtracted, so it is given a ``depth``.

*************************
Step 8: By what it is
*************************

One detail is left. A bearing is easier to press in if the mouth of the
bore has a small chamfer to guide it. The edge to chamfer is the circle at
the top of the bore.

Where it is does not single it out this time. Two edges are at that height:
the mouth of the bore, and the outer rim of the boss around it. What
separates them is their size, and edges can be selected by what they are
as well as by where they are.

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_lead_in_selected.svg
    :align: center
    :width: 55%

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [lead_in_builder]
            :end-before: [lead_in_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/selecting_and_finishing.py
            :language: build123d
            :start-after: [lead_in_algebra]
            :end-before: [lead_in_algebra]

.. image:: /tutorials/assets/selecting_and_finishing/pedestal_lead_in.svg
    :align: center
    :width: 60%

The selection is built up in three moves, each working on what the one
before it left:

#. ``group_by(Axis.Z)[-1]`` takes the highest edges, as in step 4.
#. ``filter_by(GeomType.CIRCLE)`` keeps those that are circles or arcs of
   circles. ``filter_by`` was given a direction in step 3; here it is given
   a kind of edge. Two are left, and they have the name ``rims``.
#. ``filter_by_value(Edge.radius, bore_radius)`` keeps the one whose radius
   is ``bore_radius``. Where ``sort_by`` and ``group_by`` put things in
   order and leave you to take the first or the last, ``filter_by_value``
   asks for a value outright.

The last move says exactly what is wanted: *the circle with the radius of
the bore*. "The smaller of the two" would have found the same edge today,
and would find the wrong one if the design changed so that something
smaller appeared at that height. Where a dimension you have named
identifies the edge, select by it.

The order of the moves matters. Only a circle has a radius, so asking a
straight edge for one fails, and ``filter_by_value(Edge.radius, ...)``
stops with *Shape could not be reduced to a circle* if one is in the list.
Filtering for circles first makes the list safe to ask. The height comes
into it as well: the bore has a circle of the same radius at its other
end, at the bottom of the pedestal.

The selection is written in two lines, with ``rims`` kept in a variable,
so that each stage can be counted and looked at, as the tip in step 3
suggests. A selection is a Python list as well, so it can be sliced:
``[-2:]`` takes the last two of a sorted list.

Try a ``base_height`` of 20 or a ``length`` of 110 at the top of the file.
Every fillet and chamfer, the boss and all five holes follow, because none
of them was placed by a number: each was placed by describing an edge or a
face.

********************
What you learned
********************

* A part lists its ``edges()``, ``faces()`` and ``vertices()``, and each
  list can be narrowed down: ``filter_by`` keeps those that match,
  ``group_by`` gathers them into groups, and ``sort_by`` puts them in
  order.
* Each of the three takes many measures: a direction such as ``Axis.Z``,
  the kind of edge with ``GeomType``, and others - the area of a face, the
  distance from a point. ``filter_by_value`` keeps the ones with a given
  value of a property, such as ``Edge.radius``. :ref:`selectors` covers
  them all.
* Selections can be chained, each step narrowing the one before, and an
  index or a slice is safe once the list has been sorted or grouped.
* :func:`~operations_generic.fillet` rounds the edges it is given and
  :func:`~operations_generic.chamfer` bevels them.
* A **face is a place**. A sketch can be drawn on it, and features such as
  :class:`~objects_part.Hole` can be created at it.
* The edges an operation has just made can be selected with
  ``Select.LAST``.
* A selection describes what you mean, so it goes on meaning it when the
  dimensions change. That is how build123d avoids the topological naming
  problem.
