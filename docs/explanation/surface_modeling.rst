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

The one requirement that causes trouble is the sharing of edges. Two faces
are joined only where their edges are the same edge. Edges that were made
separately and merely coincide leave a gap too small to see and large
enough to stop the shell from closing. The dependable practice is to make
each edge once and build every face that uses it from that one edge, or to
take the edge from a face that already has it.

**************************
Ways to make a surface
**************************

The methods of :class:`~topology.Face` for making a surface that is not
flat differ in what they start from:

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - Method
      - Starts from
    * - :meth:`~topology.Face.make_surface`
      - a closed boundary, with optional points for the surface to pass
        through
    * - :meth:`~topology.Face.make_surface_patch`
      - a boundary, with constraints on how it meets its neighbours
    * - :meth:`~topology.Face.make_surface_from_curves`
      - two curves, joined by a ruled surface
    * - :meth:`~topology.Face.make_gordon_surface`
      - a grid of crossing curves: profiles and guides
    * - :meth:`~topology.Face.make_bezier_surface`
      - a grid of control points
    * - :meth:`~topology.Face.make_surface_from_array_of_points`
      - a grid of points for the surface to follow closely

***************
Where to start
***************

Two tutorials work through complete examples:

* :ref:`tutorial_surface_heart_token` covers the fundamentals: a boundary,
  a surface, mirrored copies, side faces, a shell and a solid.
* :ref:`tutorial_surface_spitfire_wing` builds a wing as a Gordon surface
  through airfoil profiles.
