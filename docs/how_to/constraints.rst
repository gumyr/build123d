.. _drawing_with_constraints:

########################
Drawing with constraints
########################

An outline drawn from typed-in coordinates is right once. Change one
dimension and the pieces no longer meet. An outline drawn with
*constraints* holds together: each line or arc takes its ends, its
direction or its length from the objects it belongs with, so when they
change it follows.

build123d has no sketch solver. A constraint here is a line of code that
asks an object already drawn for a point, a direction or a length, and
the outline is built in order, each piece from the ones before it. Why it
works this way is discussed in :ref:`constraints_explained`, and
:ref:`tutorial_dimensioned_drawing` uses several of these techniques
together on one drawing.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To make a line or arc
      - use
    * - start where another ends
      - ``other @ 1``
    * - sized from another object
      - ``other @ 0.5``, ``other.length``
    * - leave another along its tangent
      - ``other % 1``
    * - leave another at a right angle
      - ``(other % 1).rotate(Axis.Z, 90)``
    * - stand a sketch across another, for a sweep
      - ``other ^ 0``
    * - run until it meets another object
      - ``PolarLine(..., length=other)``
    * - keep a constant distance from another
      - ``offset``
    * - join two curves smoothly
      - ``BlendCurve``
    * - tangent to other lines and arcs
      - ``ConstrainedArcs``, ``ConstrainedLines``
    * - with a dimension worked out by trigonometry
      - ``Triangle``

The code is the same in both modes. In builder mode the lines are drawn
inside a ``BuildLine`` and collected by it; in algebra mode each is kept
in a variable and they are added together at the end.

In the pictures the object each example adds is drawn in blue, what it
is tied to in black, and construction geometry dashed.

***********************************
Start where another object ends
***********************************

.. image:: /how_to/assets/constraints/ends.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [ends]
            :end-before: [ends]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [ends_algebra]
            :end-before: [ends_algebra]

``@`` is the *position at* operator, a short way of writing the
:meth:`~topology.Mixin1D.position_at` method of an ``Edge`` or ``Wire``:
``l1 @ 0`` is ``l1.position_at(0)``. That is the point at the start of
``l1``, and ``l1 @ 1`` is the point at its end, so the arc starts and ends
on the ends of the line, wherever the line is. Any value between 0 and 1
gives the point that fraction of the way along.

There are three such operators, each short for a method of the same name:

.. list-table::
    :header-rows: 1
    :widths: 20 40 40

    * - Operator
      - Method
      - Gives
    * - ``line @ 0.5``
      - ``line.position_at(0.5)``
      - a point on the line
    * - ``line % 0.5``
      - ``line.tangent_at(0.5)``
      - the direction of the line there
    * - ``line ^ 0.5``
      - ``line.location_at(0.5)``
      - a location there: the point, and a frame turned to face along
        the line

The methods take further arguments that the operators cannot, such as
measuring the position as a distance along the line in place of a
fraction.

.. note::

    Values outside 0 to 1 are accepted too. On an ``Edge`` the underlying
    curve is followed beyond the end of the edge where it can be: an open
    curve is carried on and a closed one wraps round. On a ``Wire`` the
    value is held at the first or last point. The same goes for ``%`` and
    ``^``.

*****************************
Sized from another object
*****************************

.. image:: /how_to/assets/constraints/measure.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [measure]
            :end-before: [measure]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [measure_algebra]
            :end-before: [measure_algebra]

The middle point of the arc is no longer typed in. ``l1 @ 0.5`` is the
middle of the line, and ``(0, l1.length / 2)`` is added to it, a vector
half the length of the line. ``length`` is a property of every edge and
wire. The arc now follows the line through any change of position, length
or slope.

Other properties serve the same way: an arc has a ``radius`` and an
``arc_center``, and every shape has a ``center()`` and a bounding box.

*************************
Leave along a tangent
*************************

.. image:: /how_to/assets/constraints/tangent.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [tangent]
            :end-before: [tangent]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [tangent_algebra]
            :end-before: [tangent_algebra]

``%`` is the *tangent at* operator, short for the
:meth:`~topology.Mixin1D.tangent_at` method: ``l2 % 1`` is
``l2.tangent_at(1)``, the direction ``l2`` is heading at its end, drawn
dashed in the picture.
:class:`~objects_curve.JernArc` is an arc given by where it starts and
which way it sets off, so with ``start=l2 @ 1`` and ``tangent=l2 % 1`` it
carries on from the line with no corner. Its ``radius`` and ``arc_size``
finish the description.

The last line starts at the end of the arc and its other end is worked
out from ``l2.length`` and ``l3.radius``, so it too follows the rest.

**************************
Leave at a right angle
**************************

.. image:: /how_to/assets/constraints/perpendicular.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [perpendicular]
            :end-before: [perpendicular]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [perpendicular_algebra]
            :end-before: [perpendicular_algebra]

A tangent is a vector, and can be turned. Rotated a quarter turn about
``Axis.Z`` it points square to the curve, and
:class:`~objects_curve.PolarLine` draws a line from a start point in a
direction. ``l2`` stays perpendicular to the end of the arc whatever the
arc is changed to. Use ``90`` to leave on the other side.

The third operator, ``^``, is short for
:meth:`~topology.Mixin1D.location_at`. ``l1 ^ 1`` is a whole location at
the end of ``l1``, a place with its Z direction along the line, and is
what a sketch is put on to stand it across a path.
:ref:`placing_sketches` shows it used for the profile of a sweep.

*************************************
Run until it meets another object
*************************************

When the intent is "go this way until you meet that", give the other
object in place of a length.

.. image:: /how_to/assets/constraints/until.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [until]
            :end-before: [until]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [until_algebra]
            :end-before: [until_algebra]

Two lines leave one point at different angles and each stops on the
ellipse. ``PolarLine`` is given the ellipse as its ``length`` and limits
the line where the two meet. The piece of the ellipse between the two
lines is then cut out with ``trim`` and becomes the third side.

The ellipse is construction geometry: only a piece of it belongs in the
outline. In builder mode it is made with ``mode=Mode.PRIVATE``, which
keeps it out of the line being built, and the trimmed piece is added with
``insert``. In algebra mode nothing is collected automatically, so the
ellipse is simply left out of the sum.

The limit can be a :class:`~topology.Shape`, an :class:`~geometry.Axis`,
a :class:`~geometry.Location`, a :class:`~geometry.Plane` or a point. If
the line never meets it a ``ValueError`` is raised. The same works for
the ``arc_size`` of these arcs:

- :class:`~objects_curve.CenterArc`
- :class:`~objects_curve.EllipticalCenterArc`
- :class:`~objects_curve.JernArc`
- :class:`~objects_curve.ParabolicCenterArc`
- :class:`~objects_curve.HyperbolicCenterArc`

so a parabola or a hyperbola can be grown from its start and ended by a
line or an axis:

.. literalinclude:: /how_to/constraints.py
    :language: build123d
    :start-after: [until_arcs]
    :end-before: [until_arcs]

****************************
Keep a constant distance
****************************

.. image:: /how_to/assets/constraints/distance.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [distance]
            :end-before: [distance]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [distance_algebra]
            :end-before: [distance_algebra]

:func:`~operations_generic.offset` makes a copy of a line at a constant
distance from it, on the side named by ``side``. Given an open line, as
here, it also closes the two ends, so the result is a closed outline the
thickness of the offset: the wall of a channel, ready for ``make_face``.
How the corners are joined is controlled by its ``kind`` parameter.

In builder mode ``offset`` works on the line drawn so far and replaces it
with the result. In algebra mode it is given the line and returns the
result.

****************************
Join two curves smoothly
****************************

.. image:: /how_to/assets/constraints/blend.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [blend]
            :end-before: [blend]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [blend_algebra]
            :end-before: [blend_algebra]

:class:`~objects_curve.BlendCurve` connects the end of one curve to the
start of another with a third that meets both smoothly. Here an arc, on
the left, is joined to a spline, on the right.

``continuity=ContinuityLevel.C2`` matches curvature at each end as well
as position and direction, which avoids a visible break where the curves
join; :ref:`constraints_explained` describes the levels.
``tangent_scalars`` sets how strongly the connector sets off along each
of the two curves.

The fine lines in the picture are a *curvature comb*, a way of checking
the result. The length of each tooth shows how sharply the curve is
bending there, and a smooth join gives a comb that changes gradually,
with no step:

.. literalinclude:: /how_to/constraints.py
    :language: build123d
    :start-after: [blend_comb]
    :end-before: [blend_comb]

***********************************
Tangent to other lines and arcs
***********************************

:class:`~objects_curve.ConstrainedArcs` and
:class:`~objects_curve.ConstrainedLines` make arcs and lines that are
tangent to curves, pass through points, or both. Such a construction
usually has several answers, so there are two things to do: narrow the
answers down, and choose among those left.

.. image:: /how_to/assets/constraints/tangent_to.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [tangent_to]
            :end-before: [tangent_to]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/constraints.py
            :language: build123d
            :start-after: [tangent_to_algebra]
            :end-before: [tangent_to_algebra]

The two ends of this outline are arcs of circles, and each side is an arc
of a given radius tangent to both.

**Narrowing down.** Each curve is paired with a ``Tangency`` qualifier.
``Tangency.OUTSIDE`` asks for an arc that lies outside both circles, and
``Tangency.ENCLOSING`` for one that wraps round both. That is enough to
give one answer for the lower side.

**Choosing.** The upper side still has more than one answer, and the
highest in Y is the one wanted. Both objects return a
:class:`~topology.Curve` holding every answer. In algebra mode, make them
all and select afterwards with ``sort_by``. In builder mode, select
inside the call with ``selector``, so that only the wanted answer is
added to the line; without one, every answer is added.

The ends are then trimmed to the parts that lie between the two sides,
as the ellipse was above.

Some useful selectors:

.. code-block:: build123d

    # Nearest to point
    selector=lambda edges: edges.sort_by_distance((0, 0))[0]

    # Longest
    selector=lambda edges: edges.sort_by(Edge.length)[-1]

    # Right most
    selector=lambda edges: edges.sort_by(Axis.X)[-1]

    # Keep two branches
    selector=lambda edges: edges[:2]

    # Keep all solutions
    selector=lambda edges: edges

Prefer geometric criteria (distance, position along an axis, length) over
an index into the list when the geometry upstream may change.

**If it does not work:**

- Too many results: add qualifiers and a stricter ``selector``.
- No results: relax the qualifier, starting with ``Tangency.UNQUALIFIED``,
  and check that the geometry is coplanar.
- The choice changes when the model changes: avoid selecting by index
  alone; sort geometrically.
- Builder mode adds many edges unexpectedly: give a ``selector`` in the
  call.
- A qualifier seems to do the opposite: check the direction of the input
  edge, since inside and outside are defined by it.

Every form the two objects accept, and the exact meaning of the
qualifiers, is in :ref:`constrained_arcs_and_lines`.

*************************
Solve for a dimension
*************************

Where a dimension follows from others by trigonometry, the
:class:`~objects_sketch.Triangle` object has a solver built in: give it
any three of its sides and angles and it works out the rest. It is the
same in both modes.

.. code-block:: build123d

    >>> isosceles = Triangle(a=30, b=30, C=60)
    >>> isosceles.c
    29.999999999999996
    >>> isosceles.A
    60.00000000000001
    >>> isosceles.B
    60.00000000000001
    >>> isosceles.vertex_A
    Vertex(-1.7763568394002505e-15, 17.32050807568877, 0.0)

Here the sides ``a`` and ``b`` and the angle between them, ``C``, are
given, and the remaining side, angles and vertices are computed. Side ``a``
is opposite angle ``A``, ``b`` opposite ``B`` and ``c`` opposite ``C``.

Here the sides ``a`` and ``b`` and the angle between them, ``C``, are
given, and the remaining side, angles and vertices are computed. Side
``a`` is opposite angle ``A``, ``b`` opposite ``B`` and ``c`` opposite
``C``.

When the governing relationships are algebraic and awkward to construct
with objects, solve them first with an external solver and feed the solved
values into ordinary build123d objects. This uses the symbolic solver
``sympy``:

.. code-block:: build123d

    from math import sin, cos, tan, radians
    from build123d import *
    from ocp_vscode import *
    import sympy

    # This problem uses the sympy symbolic math solver

    # Define the symbols for the unknowns
    # - the center of the radius 30 arc (x30, y30)
    # - the center of the radius 66 arc (x66, y66)
    # - end of the 8° line (l8x, l8y)
    # - the point with the radius 30 and 66 arc meet i30_66
    # - the start of the horizontal line lh
    y30, x66, xl8, yl8 = sympy.symbols("y30 x66 xl8 yl8")
    x30 = 77 - 55 / 2
    y66 = 66 + 32

    # There are 4 unknowns so we need 4 equations
    equations = [
        (x66 - x30) ** 2 + (y66 - y30) ** 2 - (66 + 30) ** 2,  # distance between centers
        xl8 - (x30 + 30 * sin(radians(8))),  # 8 degree slope
        yl8 - (y30 + 30 * cos(radians(8))),  # 8 degree slope
        (yl8 - 50) / (55 / 2 - xl8) - tan(radians(8)),  # 8 degree slope
    ]
    # There are two solutions but we want the 2nd one
    solution = {k: float(v) for k,v in sympy.solve(equations, dict=True)[1].items()}

    # Create the critical points
    c30 = Vector(x30, solution[y30])
    c66 = Vector(solution[x66], y66)
    l8 = Vector(solution[xl8], solution[yl8])

    ...

************
See also
************

* :ref:`constraints_explained` discusses why build123d constrains by
  construction and has no solver.
* :ref:`tutorial_drawing_outlines` introduces ``@`` and ``%`` step by
  step, and :ref:`tutorial_dimensioned_drawing` applies these recipes to
  a complete drawing.
* :ref:`constrained_arcs_and_lines` is the reference for
  ``ConstrainedArcs`` and ``ConstrainedLines``.
