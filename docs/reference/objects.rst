#######
Objects
#######

Objects are Python classes that take parameters as inputs and create 1D, 2D or 3D Shapes.
For example, a :class:`~objects_part.Torus` is defined by a major and minor radii. In
Builder mode, objects are positioned with ``Locations`` while in Algebra mode, objects
are positioned with the ``*`` operator and shown in these examples:

.. code-block:: build123d

    with BuildPart() as disk:
        with BuildSketch():
            Circle(a)
            with Locations((b, 0.0)):
                Rectangle(c, c, mode=Mode.SUBTRACT)
            with Locations((0, b)):
                Circle(d, mode=Mode.SUBTRACT)
        extrude(amount=c)

.. code-block:: build123d

    sketch = Circle(a) - Pos(b, 0.0) * Rectangle(c, c) - Pos(0.0, b) * Circle(d)
    disk = extrude(sketch, c)

The following sections describe the 1D, 2D and 3D objects:

Align
-----

2D/Sketch and 3D/Part objects can be aligned relative to themselves, either centred, or justified
right or left of each Axis. The following diagram shows how this alignment works in 2D:

.. image:: /reference/assets/objects/align.svg
    :align: center

For example:

.. code-block:: build123d

    with BuildSketch():
        Circle(1, align=(Align.MIN, Align.MIN))

creates a circle whose minimal X and Y values are on the X and Y axis and is located in the top right corner.
The ``Align`` enum has values: ``MIN``, ``CENTER`` and ``MAX``.

In 3D the ``align`` parameter also contains a Z align value but otherwise works in the same way.

Note that the ``align`` will also accept a single ``Align`` value which will be used on all axes -
as shown here:

.. code-block:: build123d

    with BuildSketch():
        Circle(1, align=Align.MIN)

Mode
----

With the Builder API the ``mode`` parameter controls how objects are combined with lines, sketches, or parts
under construction.  The ``Mode`` enum has values:

* ``ADD``: fuse this object to the object under construction
* ``SUBTRACT``: cut this object from the object under construction
* ``INTERSECT``: intersect this object with the object under construction
* ``REPLACE``: replace the object under construction with this object
* ``PRIVATE``: don't interact with the object under construction at all

The Algebra API doesn't use the ``mode`` parameter - users combine objects with operators.

1D Objects
----------

The following objects all can be used in BuildLine contexts. In Builder mode,
active ``Locations`` place 1D objects when they are added to the active builder.

.. grid:: 3

    .. grid-item-card:: :class:`~objects_curve.Airfoil`

        .. image:: /reference/assets/objects/example_airfoil.svg

        +++
        Airfoil described by 4 digit NACA profile

    .. grid-item-card:: :class:`~objects_curve.Bezier`

        .. image:: /reference/assets/objects/bezier_curve_example.svg

        +++
        Curve defined by control points and weights

    .. grid-item-card:: :class:`~objects_curve.BlendCurve`

        .. image:: /reference/assets/objects/example_blend_curve.svg

        +++
        Curve blending curvature of two curves

    .. grid-item-card:: :class:`~objects_curve.BSpline`

        .. image:: /reference/assets/objects/example_bspline.svg

        +++
        B-spline from control points and knot data

    .. grid-item-card:: :class:`~objects_curve.CenterArc`

        .. image:: /reference/assets/objects/center_arc_example.svg

        +++
        Arc defined by centre, radius, & angles


    .. grid-item-card:: :class:`~objects_curve.ConstrainedArcs`

        .. image:: /reference/assets/objects/constrained_arcs_example.svg

        +++
        Arc(s) constrained by other geometric objects


    .. grid-item-card:: :class:`~objects_curve.ConstrainedLines`

        .. image:: /reference/assets/objects/constrained_lines_example.svg

        +++
        Line(s) constrained by other geometric objects

    .. grid-item-card:: :class:`~objects_curve.DoubleTangentArc`

        .. image:: /reference/assets/objects/double_tangent_line_example.svg

        +++
        Arc defined by point/tangent pair & other curve

    .. grid-item-card:: :class:`~objects_curve.EllipticalCenterArc`

        .. image:: /reference/assets/objects/elliptical_center_arc_example.svg

        +++
        Elliptical arc defined by centre,  radii & angles

    .. grid-item-card:: :class:`~objects_curve.EllipticalStartArc`

        .. image:: /reference/assets/objects/elliptical_start_arc_example.svg

        +++
        Elliptical arc defined by start, tangent, radii & angles

    .. grid-item-card:: :class:`~objects_curve.ParabolicCenterArc`

        .. image:: /reference/assets/objects/parabolic_center_arc_example.svg

        +++
        Parabolic arc defined by vertex, focal length & angles

    .. grid-item-card:: :class:`~objects_curve.HyperbolicCenterArc`

        .. image:: /reference/assets/objects/hyperbolic_center_arc_example.svg

        +++
        Hyperbolic arc defined by centre, radii & angles

    .. grid-item-card:: :class:`~objects_curve.FilletPolyline`

        .. image:: /reference/assets/objects/filletpolyline_example.svg

        +++
        Polyline with filleted corners defined by pts and radius

    .. grid-item-card:: :class:`~objects_curve.Helix`

        .. image:: /reference/assets/objects/helix_example.svg

        +++
        Helix defined pitch, radius and height

    .. grid-item-card:: :class:`~objects_curve.IntersectingLine`

        .. image:: /reference/assets/objects/intersecting_line_example.svg

        +++
        Intersecting line defined by start, direction & other line

    .. grid-item-card:: :class:`~objects_curve.JernArc`

        .. image:: /reference/assets/objects/jern_arc_example.svg

        +++
        Arc define by start point, tangent, radius and angle

    .. grid-item-card:: :class:`~objects_curve.Line`

        .. image:: /reference/assets/objects/line_example.svg

        +++
        Line defined by end points

    .. grid-item-card:: :class:`~objects_curve.PolarLine`

        .. image:: /reference/assets/objects/polar_line_example.svg

        +++
        Line defined by start, angle and length

    .. grid-item-card:: :class:`~objects_curve.Polyline`

        .. image:: /reference/assets/objects/polyline_example.svg

        +++
        Multiple line segments defined by points

    .. grid-item-card:: :class:`~objects_curve.RadiusArc`

        .. image:: /reference/assets/objects/radius_arc_example.svg

        +++
        Arc defined by two points and a radius

    .. grid-item-card:: :class:`~objects_curve.SagittaArc`

        .. image:: /reference/assets/objects/sagitta_arc_example.svg

        +++
        Arc defined by two points and a sagitta

    .. grid-item-card:: :class:`~objects_curve.Spline`

        .. image:: /reference/assets/objects/spline_example.svg

        +++
        Curve define by points

    .. grid-item-card:: :class:`~objects_curve.TangentArc`

        .. image:: /reference/assets/objects/tangent_arc_example.svg

        +++
        Arc defined by two points and a tangent

    .. grid-item-card:: :class:`~objects_curve.ThreePointArc`

        .. image:: /reference/assets/objects/three_point_arc_example.svg

        +++
        Arc defined by three points

Reference
^^^^^^^^^
.. py:module:: objects_curve

.. autoclass:: BaseCurveObject
.. autoclass:: BaseEdgeObject
.. autoclass:: BaseLineObject
.. autoclass:: Airfoil
.. autoclass:: Bezier
.. autoclass:: BlendCurve
.. autoclass:: BSpline
.. autoclass:: CenterArc
.. autoclass:: ConstrainedArcs
.. autoclass:: ConstrainedLines
.. autoclass:: DoubleTangentArc
.. autoclass:: EllipticalCenterArc
.. autoclass:: EllipticalStartArc
.. autoclass:: ParabolicCenterArc
.. autoclass:: HyperbolicCenterArc
.. autoclass:: FilletPolyline
.. autoclass:: Helix
.. autoclass:: IntersectingLine
.. autoclass:: JernArc
.. autoclass:: Line
.. autoclass:: PolarLine
.. autoclass:: Polyline
.. autoclass:: RadiusArc
.. autoclass:: SagittaArc
.. autoclass:: Spline
.. autoclass:: TangentArc
.. autoclass:: ThreePointArc
    
2D Objects
----------

.. grid:: 3

    .. grid-item-card:: :class:`~drafting.Arrow`

        .. image:: /reference/assets/objects/arrow.svg

        +++
        Arrow with head and path for shaft

    .. grid-item-card:: :class:`~drafting.ArrowHead`

        .. image:: /reference/assets/objects/arrow_head.svg

        +++
        Arrow head with multiple types


    .. grid-item-card:: :class:`~objects_sketch.Circle`

        .. image:: /reference/assets/objects/circle_example.svg

        +++
        Circle defined by radius

    .. grid-item-card:: :class:`~drafting.DimensionLine`

        .. image:: /reference/assets/objects/d_line.svg

        +++
        Dimension line


    .. grid-item-card:: :class:`~objects_sketch.Ellipse`

        .. image:: /reference/assets/objects/ellipse_example.svg

        +++
        Ellipse defined by major and minor radius

    .. grid-item-card:: :class:`~drafting.ExtensionLine`

        .. image:: /reference/assets/objects/e_line.svg

        +++
        Extension lines for distance or angles

    .. grid-item-card:: :class:`~objects_sketch.Polygon`

        .. image:: /reference/assets/objects/polygon_example.svg

        +++
        Polygon defined by points

    .. grid-item-card:: :class:`~objects_sketch.Rectangle`

        .. image:: /reference/assets/objects/rectangle_example.svg

        +++
        Rectangle defined by width and height

    .. grid-item-card:: :class:`~objects_sketch.RectangleRounded`

        .. image:: /reference/assets/objects/rectangle_rounded_example.svg

        +++
        Rectangle with rounded corners defined by width, height, and radius

    .. grid-item-card:: :class:`~objects_sketch.RegularPolygon`

        .. image:: /reference/assets/objects/regular_polygon_example.svg

        +++
        RegularPolygon defined by radius and number of sides

    .. grid-item-card:: :class:`~objects_sketch.SlotCurve`

        .. image:: /reference/assets/objects/slot_curve_example.svg

        +++
        SlotCurve defined by a centre line and height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterPoint`

        .. image:: /reference/assets/objects/slot_center_point_example.svg

        +++
        SlotCenterPoint defined by two points and a height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterToCenter`

        .. image:: /reference/assets/objects/slot_center_to_center_example.svg

        +++
        SlotCenterToCenter defined by centre separation and height

    .. grid-item-card:: :class:`~objects_sketch.SlotOverall`

        .. image:: /reference/assets/objects/slot_overall_example.svg

        +++
        SlotOverall defined by end-to-end length and height

    .. grid-item-card:: :class:`~objects_sketch.Superellipse`

        .. image:: /reference/assets/objects/superellipse_example.svg

        +++
        Superellipse ("squircle") defined by width, height, and order

    .. grid-item-card:: :class:`~drafting.TechnicalDrawing`

        .. image:: /reference/assets/objects/tech_drawing.svg

        +++
        A technical drawing with descriptions

    .. grid-item-card:: :class:`~objects_sketch.Text`

        .. image:: /reference/assets/objects/text_example.svg

        +++
        Text defined by string and font parameters

    .. grid-item-card:: :class:`~objects_sketch.Trapezoid`

        .. image:: /reference/assets/objects/trapezoid_example.svg

        +++
        Trapezoid defined by width, height and interior angles

    .. grid-item-card:: :class:`~objects_sketch.Triangle`

        .. image:: /reference/assets/objects/triangle_example.svg

        +++
        Triangle defined by one side & two other sides or interior angles


Reference
^^^^^^^^^
.. py:module:: objects_sketch

.. autoclass:: BaseSketchObject
.. autoclass:: drafting.Arrow
.. autoclass:: drafting.ArrowHead
.. autoclass:: Circle
.. autoclass:: drafting.DimensionLine
.. autoclass:: drafting.Draft
.. autoclass:: Ellipse
.. autoclass:: drafting.ExtensionLine
.. autoclass:: Polygon
.. autoclass:: Rectangle
.. autoclass:: RectangleRounded
.. autoclass:: RegularPolygon
.. autoclass:: SlotArc
.. autoclass:: SlotCenterPoint
.. autoclass:: SlotCenterToCenter
.. autoclass:: SlotCurve
.. autoclass:: SlotOverall
.. autoclass:: Superellipse
.. autoclass:: drafting.TechnicalDrawing
.. autoclass:: Text
.. autoclass:: Trapezoid
.. autoclass:: Triangle

3D Objects
----------

.. grid:: 3

    .. grid-item-card:: :class:`~objects_part.Box`

        .. image:: /reference/assets/objects/box_example.svg

        +++
        Box defined by length, width, height

    .. grid-item-card:: :class:`~objects_part.Cone`

        .. image:: /reference/assets/objects/cone_example.svg

        +++
        Cone defined by radii and height

    .. grid-item-card:: :class:`~objects_part.ConvexPolyhedron`

        .. image:: /reference/assets/objects/convex_polyhedron_example.svg

        +++
        Convex Polyhedron defined by points

    .. grid-item-card:: :class:`~objects_part.CounterBoreHole`

        .. image:: /reference/assets/objects/counter_bore_hole_example.svg

        +++
        Counter bore hole defined by radii and depths

    .. grid-item-card:: :class:`~objects_part.CounterSinkHole`

        .. image:: /reference/assets/objects/counter_sink_hole_example.svg

        +++
        Counter sink hole defined by radii and depth and angle

    .. grid-item-card:: :class:`~objects_part.Cylinder`

        .. image:: /reference/assets/objects/cylinder_example.svg

        +++
        Cylinder defined by radius and height

    .. grid-item-card:: :class:`~objects_part.Hole`

        .. image:: /reference/assets/objects/hole_example.svg

        +++
        Hole defined by radius and depth

    .. grid-item-card:: :class:`~objects_part.Sphere`

        .. image:: /reference/assets/objects/sphere_example.svg

        +++
        Sphere defined by radius and arc angles

    .. grid-item-card:: :class:`~objects_part.Torus`

        .. image:: /reference/assets/objects/torus_example.svg

        +++
        Torus defined major and minor radii

    .. grid-item-card:: :class:`~objects_part.Wedge`

        .. image:: /reference/assets/objects/wedge_example.svg

        +++
        Wedge defined by lengths along multiple Axes


Reference
^^^^^^^^^
.. py:module:: objects_part

.. autoclass:: BasePartObject
.. autoclass:: Box
.. autoclass:: Cone
.. autoclass:: ConvexPolyhedron
.. autoclass:: CounterBoreHole
.. autoclass:: CounterSinkHole
.. autoclass:: Cylinder
.. autoclass:: Hole
.. autoclass:: Sphere
.. autoclass:: Torus
.. autoclass:: Wedge


Text
----

.. include:: /reference/objects/text.rst

The fonts build123d can use are found with these:

.. autofunction:: text.available_fonts

.. autoclass:: text.FontManager


.. _constrained_arcs_and_lines:

Constrained Arcs and Lines
--------------------------

:class:`~objects_curve.ConstrainedArcs` and
:class:`~objects_curve.ConstrainedLines` create planar arcs and lines from
constraints relative to existing geometry. Both return a
:class:`~topology.Curve` containing one or more :class:`~topology.Edge`
objects, because a set of constraints often has more than one solution.
:ref:`constraints_explained` gives the background and
:ref:`drawing_with_constraints` shows them in use.

Constraint objects
^^^^^^^^^^^^^^^^^^

Each positional argument is one constraint:

- an :class:`~topology.Edge` or :class:`~geometry.Axis` is a curve the
  result must be **tangent to**;
- a :class:`~topology.Vertex` or ``VectorLike`` is a point the result must
  **pass through**;
- a curve may be wrapped with a qualifier as ``(object, Tangency.XXX)``.

Tangency qualifiers
^^^^^^^^^^^^^^^^^^^

The ``Tangency`` qualifiers come from OCCT and state where a solution must
lie relative to the curve it is tangent to:

- ``Tangency.UNQUALIFIED``: no preference; every valid solution is returned
  (OCCT ``Unqualified``).
- ``Tangency.OUTSIDE``: the solution and the target are external to each
  other (OCCT ``Outside``).
- ``Tangency.ENCLOSING``: the solution encloses the target (OCCT
  ``Enclosing``).
- ``Tangency.ENCLOSED``: the solution is enclosed by the target (OCCT
  ``Enclosed``).

OCCT defines interior and exterior by orientation:

- Circle: the exterior is on the right-hand side when travelling along it
  in its direction; the interior, the material side, is on the left.
- Line or open curve: the interior is the left-hand side with respect to
  the direction of travel and the exterior is the other side.

Because of this, reversing an input edge can change which solutions satisfy
``OUTSIDE``, ``ENCLOSING`` and ``ENCLOSED``. If a qualifier appears to be
inverted, inspect the orientation of the input edge first. In many
practical cases ``UNQUALIFIED`` followed by a ``selector`` is a good
default.

Sagitta and selector
^^^^^^^^^^^^^^^^^^^^

``sagitta`` (``ConstrainedArcs`` only) chooses which arc of each solution
circle is returned: ``Sagitta.SHORT``, ``Sagitta.LONG`` or
``Sagitta.BOTH``.

``selector`` is a function that receives the solutions as a
:class:`~topology.ShapeList` of edges and returns the ones to keep:

.. code-block:: build123d

    # Keep all solutions
    ConstrainedArcs(..., selector=lambda arcs: arcs)

    # Keep first
    ConstrainedArcs(..., selector=lambda arcs: arcs[0])

    # Keep shortest
    ConstrainedArcs(..., selector=lambda arcs: arcs.sort_by(Edge.length)[0])

In Builder mode, every solution the selector returns is added to the
context. Use qualifiers and ``sagitta`` to reduce the number of solutions,
then finish with ``selector`` for a deterministic result.

ConstrainedArcs
^^^^^^^^^^^^^^^

:class:`~objects_curve.ConstrainedArcs` supports five families of
signature:

1. Two tangency or point constraints + fixed radius
2. Two tangency or point constraints + centre constrained to a locus
3. Three tangency constraints
4. One tangency or point constraint + fixed centre
5. One tangency or point constraint + fixed radius + centre constrained to
   a locus

Point inputs are supported by signatures 1, 2, 4 and 5. The
three-constraint signature requires curves.

**Signature A: Two constraints +** ``radius``

.. code-block:: build123d

    ConstrainedArcs(
        tangency_one,
        tangency_two,
        radius=...,
        sagitta=Sagitta.SHORT,
        selector=lambda arcs: arcs,
    )

.. figure:: /tutorials/assets/constraints/tan2_rad_ex.svg
    :align: center

Use when the radius is known and the arc must be tangent to each curve
input or pass through each point input.

**Signature B: Two constraints +** ``center_on``

.. code-block:: build123d

    ConstrainedArcs(
        tangency_one,
        tangency_two,
        center_on=Axis(...),  # or Edge
        sagitta=Sagitta.SHORT,
        selector=lambda arcs: arcs,
    )

.. figure:: /tutorials/assets/constraints/tan2_on_ex.svg
    :align: center

Use when the centre must lie on a specific line or curve and the radius is
not fixed.

**Signature C: Three constraints**

.. code-block:: build123d

    ConstrainedArcs(
        tangency_one,
        tangency_two,
        tangency_three,
        sagitta=Sagitta.BOTH,
        selector=lambda arcs: arcs,
    )

.. figure:: /tutorials/assets/constraints/tan3_ex.svg
    :align: center

Use for an arc tangent to three curves. This can produce several solutions;
always consider using ``selector``.

**Signature D: One constraint + fixed** ``center``

.. code-block:: build123d

    ConstrainedArcs(
        tangency_one,
        center=(x, y),
        selector=lambda arcs: arcs[0],
    )

.. figure:: /tutorials/assets/constraints/pnt_center_ex.svg
    :align: center

Use when the centre is known.

**Signature E: One constraint +** ``radius`` **+** ``center_on``

.. code-block:: build123d

    ConstrainedArcs(
        tangency_one,
        radius=...,
        center_on=some_edge,
        selector=lambda arcs: arcs,
    )

.. figure:: /tutorials/assets/constraints/tan_rad_on_ex.svg
    :align: center

Use for a fixed radius with the centre guided along a curve.

ConstrainedLines
^^^^^^^^^^^^^^^^

:class:`~objects_curve.ConstrainedLines` supports three families of
signature:

1. Tangent to two curves
2. Tangent to one curve and passing through a fixed point
3. Tangent to one curve with a fixed orientation (``angle`` or
   ``direction``)

For all of them, qualifiers can be attached to the curve inputs when the
side must be controlled.

**Signature A: Two constraints**

.. code-block:: build123d

    ConstrainedLines(
        tangency_one,
        tangency_two,
        selector=lambda lines: lines,
    )

.. figure:: /tutorials/assets/constraints/lines_tan2_ex.svg
    :align: center

**Signature B: One constraint + through point**

.. code-block:: build123d

    ConstrainedLines(
        tangency_one,
        (x, y),  # through point
        selector=lambda lines: lines,
    )

.. figure:: /tutorials/assets/constraints/lines_tan_pnt_ex.svg
    :align: center

**Signature C: One constraint + fixed orientation**

.. code-block:: build123d

    ConstrainedLines(
        tangency_one,
        Axis.Y,
        angle=30,              # OR direction=(dx, dy)
        selector=lambda lines: lines,
    )

.. figure:: /tutorials/assets/constraints/lines_angle_ex.svg
    :align: center

Exactly one of ``angle`` or ``direction`` should be provided.


Custom Objects
--------------

All of the objects presented above are normal Python classes built on the
``Base*Object`` classes, and the same base classes are there for objects of
your own. :ref:`custom_objects` shows how to write one.
