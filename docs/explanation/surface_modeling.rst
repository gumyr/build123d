.. _surface_modeling:

################
Surface modeling
################

Most parts are made from volumes. A sketch is extruded or revolved, the
result fills a region of space, and its faces are whatever the operation
left behind. *Surface modeling* goes the other way: the faces are made
first, each one deliberately, and the solid is what they enclose.

***********************
Why build from faces
***********************

A solid in build123d, as in any CAD system based on boundary
representation (BREP), is defined by its boundary: a hierarchy of faces,
edges and vertices, described in :ref:`topology`. Each face is a bounded
patch of a geometric surface - a plane, a cylinder, a freeform spline. An
operation such as ``extrude`` creates those faces for you, and for most
parts that is all that is wanted.

It stops being enough when the shape of a face is the point. The skin of
an aircraft, the hull of a boat, a hand grip, a smooth transition between
two unlike shapes: none of these is a sketch pushed along a line or turned
about an axis. They are surfaces that curve in two directions at once, and
they have to be described as surfaces. Surface modeling gives direct
control over each face, and over how neighbouring faces meet.

*******************************
From faces to a solid
*******************************

Faces become a solid in two steps.

A :class:`~topology.Shell` is a set of faces joined along shared edges.
When every edge of every face is shared with exactly one neighbour, the
shell has no openings; it is *watertight*, or *manifold*.

A watertight shell encloses a region of space, and a
:class:`~topology.Solid` made from it is that region. From then on it is a
solid like any other and can be combined, filleted and exported in the
usual ways.

The step that causes trouble is the joining of edges. ``Shell`` *sews* the
faces it is given: wherever the edges of two faces lie on top of one
another, they are merged into one shared edge. The edges need not be the
same object, or have been made together. They need to coincide, to within a
tolerance of one millionth of a unit.

Faces whose edges are further apart than that are not joined, and if the
faces do not all join up ``Shell`` raises a ``ValueError`` instead of
returning something with a gap in it. A gap of that kind is rarely a
mistake in the numbers. It usually comes from an edge that is an
*approximation* of its neighbour: a surfacing method that fits a spline to
its boundary returns a face whose edge is very close to the curve it was
given, and not exactly on it. There are two remedies:

* Take the edge from the face. Build the neighbouring face from
  ``face.edges()`` and not from the original curve, and the two coincide
  exactly. This is the dependable practice, and both tutorials below use
  it.
* Raise the tolerance, ``Shell(faces, tolerance=0.001)``, to something
  above the error of the approximation. The faces are then joined across
  the gap.

Checking the result
===================

A shell and a solid can each be asked whether they came out as intended:

* ``shell.is_manifold`` is true when the shell has no openings.
* ``solid.is_valid`` is true when the solid is well formed. Check it after
  making a solid from a shell: an open shell is not refused, and gives a
  solid that is not valid.
* ``solid.volume`` should be the positive number expected.

**************************
Ways to make a surface
**************************

A curved face can be made by moving a curve, which is enough for a surface
that curves in one direction, such as a side wall. These are methods of
the :class:`~topology.Face` and :class:`~topology.Shell` classes, written
with the class name, as in ``Face.extrude(edge, direction)``. They are not
the operations ``extrude``, ``revolve`` and ``sweep``, which make parts
from sketches. The ``Face`` method takes a single edge and returns one
face; the ``Shell`` method takes a wire of several edges and returns a
shell with a face for each.

.. list-table::
    :header-rows: 1
    :widths: 28 28 44

    * - From one edge
      - From a wire
      - What it does
    * - :meth:`Face.extrude <topology.Face.extrude>`
      - :meth:`Shell.extrude <topology.Shell.extrude>`
      - pushes the curve along a direction
    * - :meth:`Face.revolve <topology.Face.revolve>`
      - :meth:`Shell.revolve <topology.Shell.revolve>`
      - turns the curve about an axis
    * - :meth:`Face.sweep <topology.Face.sweep>`
      - :meth:`Shell.sweep <topology.Shell.sweep>`
      - carries the curve along a path

Before building a shape face by face, consider whether the
:func:`~operations_part.loft` operation will make it. ``loft`` takes a
series of flat sections and returns the solid that passes through them,
which covers many shapes that curve in two directions without any surface
having to be made by hand.

For a surface that curves in two directions, there are further methods of
``Face``, which differ in what they start from:

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - Method
      - Starts from
    * - :meth:`Face.make_surface <topology.Face.make_surface>`
      - a closed boundary, with optional points for the surface to pass
        through
    * - :meth:`Face.make_surface_patch <topology.Face.make_surface_patch>`
      - a boundary, with constraints on how it meets its neighbours
    * - :meth:`Face.make_surface_from_curves <topology.Face.make_surface_from_curves>`
      - two curves, joined by a ruled surface
    * - :meth:`Face.make_gordon_surface <topology.Face.make_gordon_surface>`
      - a grid of crossing curves: profiles and guides
    * - :meth:`Face.make_bezier_surface <topology.Face.make_bezier_surface>`
      - a grid of control points
    * - :meth:`Face.make_surface_from_array_of_points <topology.Face.make_surface_from_array_of_points>`
      - a grid of points for the surface to follow closely

***************
Where to start
***************

Two tutorials work through complete examples:

* :ref:`tutorial_surface_heart_token` covers the fundamentals: a boundary,
  a surface, mirrored copies, side faces, a shell and a solid.
* :ref:`tutorial_surface_spitfire_wing` builds a wing as a Gordon surface
  through airfoil profiles.
