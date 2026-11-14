#########
BuildLine
#########

BuildLine is a python context manager that is used to create one dimensional
objects - objects with the property of length but not area - that are typically
used as part of a BuildSketch sketch or a BuildPart path.

The complete API for BuildLine is located at the end of this section.

*******************
Basic Functionality
*******************

The following is a simple BuildLine example:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 1]
    :end-before: [Ex. 1]

The ``with`` statement creates the ``BuildLine`` context manager with the
identifier ``example_1``. The objects and operations that are within the
scope (i.e. indented) of this context will contribute towards the object
being created by the context manager.  For ``BuildLine``, this object is
``line`` and it's referenced as ``example_1.line``.

The first object in this example is a ``Line`` object which is used to create
a straight line from coordinates (0,0) to (2,0) on the default XY plane.
The second object is a ``ThreePointArc`` that starts and ends at the two
ends of the line.

.. image:: /how_to/assets/build_line/buildline_example_1.svg
    :align: center

.. _drawing_with_constraints:

***********
Constraints
***********

Building with constraints enables the designer to capture design intent and
add a high degree of robustness to their designs.  The following sections
describe creating positional and tangential constraints as well as using
object attributes to enable this type of design.

Why build123d works this way, and has no sketch solver, is discussed in
:ref:`constraints_explained`. :ref:`tutorial_dimensioned_drawing` uses
several of these techniques together on one drawing.

@ ``position_at`` Operator
===========================

In the previous example, the ``ThreePointArc`` started and ended at the
two ends of the ``Line`` but this was done by referring to the same
point ``(0,0)`` and ``(2,0)``.  This can be improved upon by specifying
constraints that lock the arc to those two end points, as follows:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 2]
    :end-before: [Ex. 2]

Here instance variables ``l1`` and ``l2`` are assigned to the two BuildLine
objects and the ``ThreePointArc`` references the beginning of the straight
line with ``l1 @ 0`` and the end with ``l1 @ 1``.  The ``@`` operator takes
a float (or integer) parameter between 0 and 1 and determines a position
at this fractional position along the line's length.

Values outside the usual 0-to-1 range are also accepted by ``position_at``,
``tangent_at``, and ``location_at``. On an ``Edge``, the underlying curve is
evaluated beyond the trimmed edge where supported: open curves can extrapolate
and periodic curves can wrap. On a ``Wire``, out-of-range values are clamped to
the first or last point (and its corresponding tangent or location frame).

This example can be improved on further by calculating the mid-point
of the arc as follows:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 3]
    :end-before: [Ex. 3]

Here ``l1 @ 0.5`` finds the center of ``l1`` while ``l1 @ 0.5 + (0, 1)`` does
a vector addition to generate the point ``(1,1)``.

To make the design even more parametric, the height of the arc can be calculated
from ``l1`` as follows:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 4]
    :end-before: [Ex. 4]

The arc height is now calculated as ``(0, l1.length / 2)`` by using the ``length``
property of ``Edge`` and ``Wire`` shapes.  At this point the ``ThreePointArc`` is
fully parametric and able to generate the same shape for any horizontal line.

% ``tangent_at`` Operator
=========================

The other operator that is commonly used within BuildLine is ``%`` the tangent at
operator. Here is another example:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 5]
    :end-before: [Ex. 5]

which generates (note that the circles show line junctions):

.. image:: /how_to/assets/build_line/buildline_example_5.svg
    :align: center

The ``JernArc`` has the following parameters:

* ``start=l2 @ 1`` - start the arc at the end of line ``l2``,
* ``tangent=l2 % 1`` - the tangent of the arc at the start point is equal to the ``l2``\'s,
  tangent at its end (shown as a dashed line)
* ``radius=0.5`` - the radius of the arc, and
* ``arc_size=90`` the angular size of the arc.

The final line starts at the end of ``l3`` and ends at a point calculated from the length
of ``l2`` and the radius of arc ``l3``.

Building with constraints as shown here will ensure that your designs both fully represent
design intent and are robust to design changes.

Perpendicular to a Curve
========================

To leave a curve at a right angle, take its tangent with ``tangent_at`` (the
method behind ``%``) and rotate it by 90 degrees:

.. code-block:: build123d

    with BuildLine() as perpendicular_ex:
        l1 = CenterArc((0, 0), 1.5, 0, 45)
        l2 = PolarLine(
            start=l1 @ 1, length=1, direction=l1.tangent_at(1).rotate(Axis.Z, -90)
        )

.. figure:: /tutorials/assets/constraints/perpendicular_ex.svg
    :align: center

The direction of ``l2`` is built from ``l1.tangent_at(1)``, so it stays
perpendicular to the end of the arc whatever the arc is changed to.

Run Until It Meets Another Object
=================================

When the intent is "go in this direction until you meet that", give the
other object in place of a length. Here two lines leave one point at
different angles and each stops on an ellipse:

.. code-block:: build123d

    with BuildLine() as intersect_ex:
        c1 = EllipticalCenterArc((0, 0), 1.2, 1.8, 0, arc_size=120, mode=Mode.PRIVATE)
        l1 = PolarLine(start=(-0.2, 0.1), length=c1, angle=10)
        l2 = PolarLine(start=(-0.2, 0.1), length=c1, angle=70)
        l3 = insert(c1.trim(l1 @ 1, l2 @ 1))

.. figure:: /tutorials/assets/constraints/intersect_ex.svg
    :align: center

:class:`~objects_curve.PolarLine` creates each line from a start point and
a direction and limits it by its intersection with the ellipse. The ellipse
is construction geometry (``mode=Mode.PRIVATE``); the piece of it between
the two lines is cut out with ``trim`` and added with ``insert``. This is
cleaner than drawing long helper lines and trimming them afterwards.

The limit can be a :class:`~topology.Shape`, :class:`~geometry.Axis`,
:class:`~geometry.Location`, :class:`~geometry.Plane` or a point, and if the
line never meets it a ``ValueError`` is raised. The same works for the
``arc_size`` of several arcs:

- :class:`~objects_curve.CenterArc`
- :class:`~objects_curve.EllipticalCenterArc`
- :class:`~objects_curve.EllipticalStartArc`
- :class:`~objects_curve.JernArc`
- :class:`~objects_curve.ParabolicCenterArc`
- :class:`~objects_curve.HyperbolicCenterArc`

For example, a parabola or a hyperbola can be grown from a start condition
and ended by a line or an axis:

.. code-block:: build123d

    p1 = ParabolicCenterArc((0, 0), 0.5, 0, arc_size=Line((0, 1), (5, 1)))
    h1 = HyperbolicCenterArc((0, 0), 2, 1, 0, arc_size=Axis((0, 1), (1, 0)))

This is particularly useful when a sketch is not symmetric and several
local constructions must each end against different surrounding geometry.

Keep a Constant Distance
========================

.. code-block:: build123d

    inside = FilletPolyline((1.5, 0), (1.5, 1), (-1.5, 1), (-1.5, 0), radius=0.2)
    perimeter = offset(inside, amount=0.2, side=Side.RIGHT)

.. figure:: /tutorials/assets/constraints/offset_ex.svg
    :align: center

:func:`~operations_generic.offset` keeps the shape of the source profile
while enforcing a constant distance from it. This is the common pattern for
wall thicknesses, clearances and manufacturing margins. How the corners are
joined is controlled by its ``kind`` parameter.

Join Two Curves Smoothly
========================

To connect two curves with a third that meets both smoothly, use
:class:`~objects_curve.BlendCurve`. Here a semi-circle, on the left, is
joined to a spline, on the right:

.. code-block:: build123d

    m1 = CenterArc((-2, 0.6), 1, -10, 200).reversed()
    m2 = Spline((0.4, -0.6), (1, -1.6), (2, 0))
    connector = BlendCurve(m1, m2, tangent_scalars=(2, 1), continuity=ContinuityLevel.C2)
    comb = Curve(Wire([m1, connector, m2]).curvature_comb(200))

.. figure:: /tutorials/assets/constraints/blend_curve_ex.svg
    :align: center

``continuity=ContinuityLevel.C2`` matches curvature at each end as well as
position and tangent, which avoids a visible break in fairness at the
joins; :ref:`constraints_explained` describes the levels.
``tangent_scalars`` controls how strongly the connector departs from each
source curve.

``curvature_comb`` is used here as a diagnostic. The length of each tooth
of the comb shows the curvature at that point; a smooth transition gives a
comb that varies gradually, with no abrupt steps.

Tangent to Other Lines and Arcs
===============================

:class:`~objects_curve.ConstrainedArcs` and
:class:`~objects_curve.ConstrainedLines` make arcs and lines that are
tangent to curves, pass through points, or both. Tangent constructions
usually have several answers, so there are two things to do: narrow the
answers down, and choose among those left.

.. code-block:: build123d

    with BuildLine() as egg_plant:
        # Construction Geometry
        c1 = CenterArc((-2, 0), 0.75, 80, 240, mode=Mode.PRIVATE)
        c2 = CenterArc((2, 0), 1, 220, 250, mode=Mode.PRIVATE)

        # egg_plant perimeter
        l1 = ConstrainedArcs((c2, Tangency.OUTSIDE), (c1, Tangency.OUTSIDE), radius=6)
        l2 = ConstrainedArcs(
            (c2, Tangency.ENCLOSING),
            (c1, Tangency.ENCLOSING),
            radius=8,
            selector=lambda a: a.sort_by(Axis.Y)[-1],
        )
        l3 = insert(c1.trim(l1 @ 1, l2 @ 1))
        l4 = insert(c2.trim(l1 @ 0, l2 @ 0))

.. figure:: /tutorials/assets/constraints/enclosing_ex.svg
    :align: center

In this "egg-plant", each reference curve is paired with a ``Tangency``
qualifier. ``Tangency.OUTSIDE`` asks for the arc that lies outside both
circles, and ``Tangency.ENCLOSING`` for the one that wraps round both. That
reduces the answers to the intended outer profile, and the ``selector`` on
``l2`` settles what is left by taking the highest in Y.

**Choosing among the answers.** Both objects return a
:class:`~topology.Curve` holding one or more edges. In algebra mode, make
them all and select afterwards:

.. code-block:: build123d

    arcs = ConstrainedArcs(..., sagitta=Sagitta.BOTH)
    chosen = arcs.edges().sort_by(Edge.length)[0]

In builder mode, select inside the call with ``selector``, so that only the
wanted answers are added to the ``BuildLine``. Without one, every answer is
added, which is rarely what a sketch needs:

.. code-block:: build123d

    with BuildLine() as bl:
        ConstrainedArcs(
            ...,
            sagitta=Sagitta.BOTH,
            selector=lambda arcs: arcs.sort_by(Edge.length)[0],
        )

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

Every form the two objects accept, and the exact meaning of the qualifiers,
is in :ref:`constrained_arcs_and_lines`.

Solve for a Dimension
=====================

Where a dimension follows from others by trigonometry, the
:class:`~objects_sketch.Triangle` object has a solver built in: give it any
three of its sides and angles and it works out the rest.

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

************************
BuildLine to BuildSketch
************************

As mentioned previously, one of the two primary reasons to create BuildLine objects is to
use them in BuildSketch.  When a BuildLine context manager exits and is within the scope of a
BuildSketch context manager it will transfer the generated line to BuildSketch. The BuildSketch
:meth:`~operations_sketch.make_face` or :meth:`~operations_sketch.make_hull`  operations are then used
to transform the line (specifically a list of Edges) into a Face - the native BuildSketch
objects.

Here is an example of using BuildLine to create an object that otherwise might be
difficult to create:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 6]
    :end-before: [Ex. 6]

which generates:

.. image:: /how_to/assets/build_line/buildline_example_6.svg
    :align: center

.. note:: SVG import to BuildLine

    The BuildLine code used in this example was generated by translating a SVG file
    into BuildLine source code with the :func:`~importers.import_svg_as_buildline_code`
    function. For example:

    .. code::

        svg_code, builder_name = import_svg_as_buildline_code("club.svg")

    would translate the "club.svg" image file's paths into BuildLine code much like
    that shown above. From there it's easy for a user to add constraints or otherwise
    enhance the original image and use it in their design.

**********************
BuildLine to BuildPart
**********************

The other primary reasons to use BuildLine is to create paths for BuildPart
:meth:`~operations_generic.sweep` operations. Here some curved and straight segments
define a path:

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 7]
    :end-before: [Ex. 7]

which generates:

.. image:: /how_to/assets/build_line/buildline_example_7.svg
    :align: center

There are few things to note from this example:

* The @ and % operators are used to create a plane normal to the beginning of the
  path with which to create the circular section used by the sweep operation
  (this plane is not one of the ordinal planes).
* Both the path generated by BuildLine and the section generated by BuildSketch
  have been transferred to BuildPart when each of them exit.
* The BuildPart ``Sweep`` operation is using the path and section previously
  transferred to it (as "pending" objects) as parameters of the sweep. The
  ``Sweep`` operation "consumes" these pending objects as to not interfere with
  subsequence operations.

******************************
Publishing to other Placements
******************************

So far all of the examples were created in local ``Plane.XY`` coordinates and published
to the default placement. Sometimes it's convenient to publish the completed line to
another placement, especially when creating paths for BuildPart ``Sweep`` operations.

.. literalinclude:: /reference/objects_1d.py
    :language: build123d
    :start-after: [Ex. 8]
    :end-before: [Ex. 8]

which generates:

.. image:: /how_to/assets/build_line/buildline_example_8.svg
    :align: center

Here the ``BuildLine`` object is constructed in local coordinates and the completed
line is published to ``Plane.YZ``. The local, unplaced result is available as
``line_local`` while the placed result is available as ``line``.

There are a few rules to keep in mind when publishing ``BuildLine`` output to
alternate placements:

#. ``BuildLine`` accepts a single placement, unlike ``BuildPart`` and ``BuildSketch``
   which can publish to multiple placements.
#. Values entered as tuples such as ``(1, 2)`` or ``(1, 2, 3)`` are interpreted in
   the builder's local coordinate system during construction. They are not converted
   by the placement as they are entered.
#. The placement is applied once to the completed line when ``line`` is requested or
   when the ``BuildLine`` exits and publishes to its parent.
#. Use ``line_local`` when you want to inspect or select from the construction result
   before placement. Use ``line`` when you want the published result.

.. code-block:: build123d

    with BuildLine(Plane.YZ) as path:
        Line((0, 0), (1, 0))

    show_object(path.line_local)  # line from (0, 0, 0) to (1, 0, 0)
    show_object(path.line)        # same line published to Plane.YZ

.. note::
    In earlier versions, ``BuildLine`` used the input plane during construction:
    tuple points were localized to that plane immediately. ``BuildLine`` now follows
    the same model as ``BuildPart`` and ``BuildSketch``: construction happens in the
    local coordinate system and the placement is applied at publication time.

    This does not restrict ``BuildLine`` to planar curves. Curve objects can still
    create non-planar geometry when given enough 3D information; the placement only
    controls where the completed curve is published.

Finally, a ``BuildLine`` placement need not be one of the predefined ordinal planes.
It can be any ``Plane``, ``Face``, or ``Location``, including one derived from a
surface of a ``BuildPart`` part that is currently under construction.

*********
Reference
*********
.. py:module:: build_line

.. autoclass:: BuildLine
    :members:
