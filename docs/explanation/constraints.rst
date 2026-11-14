.. _constraints_explained:

############################
Constraints without a solver
############################

CAD constraints are geometric and dimensional rules that define how the
entities of a sketch or an assembly relate to one another. They control
degrees of freedom - parallel, perpendicular, tangent, coincident, distance,
angle - so that edits preserve design intent instead of introducing
unintended changes of shape. This is the foundation of parametric modelling:
behaviour is driven by explicit relationships, not by fixed, manually drawn
geometry. This page is about sketch constraints only.

*********************
Two ways of working
*********************

In graphical CAD systems, sketching is usually a two-step workflow: first
draw approximate geometry, then add dimensions and constraints so that a
global solver can infer exact positions. That model works well for
interactive drawing, but it also encourages tightly coupled constraint
networks that can become difficult to predict and maintain as a design
evolves. It is also typically strongest for lines and circular arcs, with
more limited and less robust behaviour for ellipses, splines and other
higher-order curves.

In build123d the primary workflow is different. Geometry is defined
precisely at creation time using coordinates, parameters and explicit
geometric relationships in code. Instead of building a large interdependent
constraint graph and asking a global solver to resolve it, you express
intent directly: mirror about a plane, construct tangent features, derive
points and frames from existing topology, and compose operations
deterministically.

This does not eliminate constrained construction; it scopes it. build123d
provides targeted, local geometric solvers for common high-value problems,
and a growing family of objects whose extent can be determined by other
geometry. Each solves one specific pattern of constraint while keeping the
behaviour of the model explicit, deterministic and readable in code.

The result is a practical hybrid: precise programmatic modelling by
default, with specialised constrained objects where they provide clear
leverage. For most production parts this yields robust, maintainable
sketches without the overhead and fragility of a general-purpose sketch
solver.

**************************
The kinds of constraint
**************************

Rather than one solver for everything, there is a tool for each kind of
relationship.

.. list-table::
    :header-rows: 1
    :widths: 25 35 40

    * - Kind
      - The relationship
      - Tools
    * - Geometric relationship
      - Coincident, tangent, perpendicular, symmetric
      - The ``@`` and ``%`` operators; :func:`~operations_generic.mirror`
    * - Extent
      - "Go in this direction until you meet that"
      - :class:`~objects_curve.PolarLine`,
        :class:`~objects_curve.CenterArc`,
        :class:`~objects_curve.EllipticalCenterArc`,
        :class:`~objects_curve.EllipticalStartArc`,
        :class:`~objects_curve.JernArc`,
        :class:`~objects_curve.ParabolicCenterArc`,
        :class:`~objects_curve.HyperbolicCenterArc`
    * - Equidistance
      - A constant distance from an edge or wire
      - :func:`~operations_generic.offset`
    * - Tangency
      - Tangent to one, two or three other curves
      - :class:`~objects_curve.ConstrainedArcs`,
        :class:`~objects_curve.ConstrainedLines`
    * - Continuity
      - Join two curves smoothly
      - :class:`~objects_curve.BlendCurve`
    * - Analytical
      - Dimensions that follow from other dimensions
      - :class:`~objects_sketch.Triangle`; any Python solver
    * - Enclosure
      - The smallest convex outline round a set of shapes
      - :func:`~operations_sketch.make_hull`

How to use each of them is shown in :ref:`drawing_with_constraints`, and
:ref:`tutorial_dimensioned_drawing` works through a complete drawing.

Geometric relationships
=======================

``@`` (position-at) and ``%`` (tangent-at) construct geometry relative to
existing geometry: a new edge starts at an exact point on another, or leaves
in the direction another is travelling. The relationship is not stored
anywhere as a constraint object. It is in the code: the second line is
computed from the first, so it follows when the first changes.
:func:`~operations_generic.mirror` enforces symmetry in the same spirit, by
producing reflected geometry that corresponds exactly to its source.

Extent
======

Several curve objects are constructed from natural geometric parameters and
then let another object decide where the result ends. Their size argument
can be a number, or a limiting object: a :class:`~topology.Shape`,
:class:`~geometry.Axis`, :class:`~geometry.Location`,
:class:`~geometry.Plane` or a point.

When a limit is given, the object builds the candidate geometry from its
start conditions, trims it at the first valid intersection with the limit,
and returns the shortest valid result from the start. If there is no valid
intersection it raises a ``ValueError``. This removes helper construction
lines and separate trim calls, and keeps the relationship local to one line
of code.

Equidistance
============

:func:`~operations_generic.offset` creates geometry at a constant normal
distance from a source edge or wire. This is the relationship behind wall
thicknesses, clearances, toolpaths and parallel profiles.

Tangency
========

:class:`~objects_curve.ConstrainedArcs` and
:class:`~objects_curve.ConstrainedLines` are local solvers for planar
line-and-circle constructions. They take explicit numeric and geometric
constraints relative to existing curves - a radius, an angle to another
line, tangency to a curve, passing through a point, a centre fixed or lying
on a curve - and return the arcs or lines that satisfy them.

Continuity
==========

:class:`~objects_curve.BlendCurve` creates a smooth Bézier transition
between two existing edges. *Continuity* describes how smoothly the blend
joins them at each end:

* **C0**, positional continuity: the ends meet, but the direction may kink.
* **C1**, tangent continuity: ends and tangent directions match, giving a
  visually smooth join with no corner.
* **C2**, curvature continuity: ends, tangents and curvature match, which
  reduces jumps in curvature and produces a fairer curve.

``BlendCurve`` builds a cubic Bézier for a C1 blend (position and first
derivative) and a quintic Bézier for a C2 blend (position, first and second
derivatives). The derivatives are sampled from the two source edges at the
chosen connection points and converted into control points that enforce the
requested continuity. Optional tangent scaling factors tune how strongly
the blend departs from each source edge, which changes its tension and
shape without changing the constraints at its ends.

Analytical
==========

Some relationships are algebra and not geometry. A
:class:`~objects_sketch.Triangle` is constructed from any three of its side
lengths and interior angles and solves for the rest. For anything more
involved, build123d code is Python: solve for the unknown values with
whatever suits - ``sympy``, for instance - and feed the results into
ordinary objects.

******************************
More than one right answer
******************************

A global solver starts from your rough sketch, so it usually lands on the
answer nearest to what you drew. A local solver has no rough sketch to
start from, and a tangency problem typically has several valid answers,
depending on which side of each reference the solution lies.

For example, there can be up to eight circles of a given radius tangent to
two circles that cross each other. All eight are correct. This is expected
behaviour, not an error.

.. figure:: /tutorials/assets/constraints/tangent_circles.svg
    :align: center

build123d therefore returns every answer and gives you two ways of saying
which you meant:

* **Qualification** narrows the search before it is made, by stating how
  the solution must sit relative to each thing it touches: enclosing it,
  enclosed by it, or outside it. This is natural for circles, which have an
  inside and an outside. For other curves, the inside is defined as the
  left-hand side of the curve with respect to its direction, which means
  that reversing an input curve can change which answers qualify.
* **Selection** picks from the answers that remain, with a ``selector``
  function that sorts or filters them exactly as selectors do for the edges
  of a part.

Even with qualification more than one answer may remain, so the two are
usually used together. Choosing by a geometric criterion - position,
distance, length - and not by position in the list is what makes the choice
survive a change to the geometry upstream; this is the same argument as for
selectors in general, made in :ref:`tutorial_selecting_and_finishing`.

The exact meaning of each qualifier and the forms the two objects accept
are given in :ref:`constrained_arcs_and_lines`.
