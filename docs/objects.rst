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

2D/Sketch and 3D/Part objects can be aligned relative to themselves, either centered, or justified
right or left of each Axis. The following diagram shows how this alignment works in 2D:

.. image:: _build/assets/objects/align.svg
    :align: center

For example:

.. code-block:: build123d

    with BuildSketch():
        Circle(1, align=(Align.MIN, Align.MIN))

creates a circle who's minimal X and Y values are on the X and Y axis and is located in the top right corner.
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

The following objects all can be used in BuildLine contexts. Note that
1D objects are not affected by ``Locations`` in Builder mode.

.. grid:: 3

    .. grid-item-card:: :class:`~objects_curve.Airfoil`

        .. image:: _build/assets/objects/example_airfoil.svg

        +++
        Airfoil described by 4 digit NACA profile

    .. grid-item-card:: :class:`~objects_curve.Bezier`

        .. image:: _build/assets/objects/bezier_curve_example.svg

        +++
        Curve defined by control points and weights

    .. grid-item-card:: :class:`~objects_curve.BlendCurve`

        .. image:: _build/assets/objects/example_blend_curve.svg

        +++
        Curve blending curvature of two curves

    .. grid-item-card:: :class:`~objects_curve.CenterArc`

        .. image:: _build/assets/objects/center_arc_example.svg

        +++
        Arc defined by center, radius, & angles


    .. grid-item-card:: :class:`~objects_curve.ConstrainedArcs`

        .. image:: assets/constrained_arcs_example.svg

        +++
        Arc(s) constrained by other geometric objects


    .. grid-item-card:: :class:`~objects_curve.ConstrainedLines`

        .. image:: assets/constrained_lines_example.svg

        +++
        Line(s) constrained by other geometric objects

    .. grid-item-card:: :class:`~objects_curve.DoubleTangentArc`

        .. image:: _build/assets/objects/double_tangent_line_example.svg

        +++
        Arc defined by point/tangent pair & other curve

    .. grid-item-card:: :class:`~objects_curve.EllipticalCenterArc`

        .. image:: _build/assets/objects/elliptical_center_arc_example.svg

        +++
        Elliptical arc defined by center,  radii & angles

    .. grid-item-card:: :class:`~objects_curve.EllipticalStartArc`

        .. image:: assets/elliptical_start_arc_example.svg

        +++
        Elliptical arc defined by start, tangent, radii & angles

    .. grid-item-card:: :class:`~objects_curve.ParabolicCenterArc`

        .. image:: _build/assets/objects/parabolic_center_arc_example.svg

        +++
        Parabolic arc defined by vertex, focal length & angles

    .. grid-item-card:: :class:`~objects_curve.HyperbolicCenterArc`

        .. image:: _build/assets/objects/hyperbolic_center_arc_example.svg

        +++
        Hyperbolic arc defined by center, radii & angles

    .. grid-item-card:: :class:`~objects_curve.FilletPolyline`

        .. image:: _build/assets/objects/filletpolyline_example.svg

        +++
        Polyline with filleted corners defined by pts and radius

    .. grid-item-card:: :class:`~objects_curve.Helix`

        .. image:: _build/assets/objects/helix_example.svg

        +++
        Helix defined pitch, radius and height

    .. grid-item-card:: :class:`~objects_curve.IntersectingLine`

        .. image:: _build/assets/objects/intersecting_line_example.svg

        +++
        Intersecting line defined by start, direction & other line

    .. grid-item-card:: :class:`~objects_curve.JernArc`

        .. image:: _build/assets/objects/jern_arc_example.svg

        +++
        Arc define by start point, tangent, radius and angle

    .. grid-item-card:: :class:`~objects_curve.Line`

        .. image:: _build/assets/objects/line_example.svg

        +++
        Line defined by end points

    .. grid-item-card:: :class:`~objects_curve.PolarLine`

        .. image:: _build/assets/objects/polar_line_example.svg

        +++
        Line defined by start, angle and length

    .. grid-item-card:: :class:`~objects_curve.Polyline`

        .. image:: _build/assets/objects/polyline_example.svg

        +++
        Multiple line segments defined by points

    .. grid-item-card:: :class:`~objects_curve.RadiusArc`

        .. image:: _build/assets/objects/radius_arc_example.svg

        +++
        Arc defined by two points and a radius

    .. grid-item-card:: :class:`~objects_curve.SagittaArc`

        .. image:: _build/assets/objects/sagitta_arc_example.svg

        +++
        Arc defined by two points and a sagitta

    .. grid-item-card:: :class:`~objects_curve.Spline`

        .. image:: _build/assets/objects/spline_example.svg

        +++
        Curve define by points

    .. grid-item-card:: :class:`~objects_curve.TangentArc`

        .. image:: _build/assets/objects/tangent_arc_example.svg

        +++
        Arc defined by two points and a tangent

    .. grid-item-card:: :class:`~objects_curve.ThreePointArc`

        .. image:: _build/assets/objects/three_point_arc_example.svg

        +++
        Arc defined by three points

    .. grid-item-card:: :class:`~objects_curve.ArcArcTangentLine`

        .. image:: _build/assets/objects/example_arc_arc_tangent_line.svg

        +++
        Line tangent defined by two arcs

    .. grid-item-card:: :class:`~objects_curve.ArcArcTangentArc`

        .. image:: _build/assets/objects/example_arc_arc_tangent_arc.svg

        +++
        Arc tangent defined by two arcs

    .. grid-item-card:: :class:`~objects_curve.PointArcTangentLine`

        .. image:: _build/assets/objects/example_point_arc_tangent_line.svg

        +++
        Line tangent defined by a point and arc

    .. grid-item-card:: :class:`~objects_curve.PointArcTangentArc`

        .. image:: _build/assets/objects/example_point_arc_tangent_arc.svg

        +++
        Arc tangent defined by a point, direction, and arc

Reference
^^^^^^^^^
.. py:module:: objects_curve

.. autoclass:: BaseLineObject
.. autoclass:: Airfoil
.. autoclass:: Bezier
.. autoclass:: BlendCurve
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
.. autoclass:: ArcArcTangentLine
.. autoclass:: ArcArcTangentArc
.. autoclass:: PointArcTangentLine
.. autoclass:: PointArcTangentArc

2D Objects
----------

.. grid:: 3

    .. grid-item-card:: :class:`~drafting.Arrow`

        .. image:: _build/assets/objects/arrow.svg

        +++
        Arrow with head and path for shaft

    .. grid-item-card:: :class:`~drafting.ArrowHead`

        .. image:: _build/assets/objects/arrow_head.svg

        +++
        Arrow head with multiple types


    .. grid-item-card:: :class:`~objects_sketch.Circle`

        .. image:: _build/assets/objects/circle_example.svg

        +++
        Circle defined by radius

    .. grid-item-card:: :class:`~drafting.DimensionLine`

        .. image:: _build/assets/objects/d_line.svg

        +++
        Dimension line


    .. grid-item-card:: :class:`~objects_sketch.Ellipse`

        .. image:: _build/assets/objects/ellipse_example.svg

        +++
        Ellipse defined by major and minor radius

    .. grid-item-card:: :class:`~drafting.ExtensionLine`

        .. image:: _build/assets/objects/e_line.svg

        +++
        Extension lines for distance or angles

    .. grid-item-card:: :class:`~objects_sketch.Polygon`

        .. image:: _build/assets/objects/polygon_example.svg

        +++
        Polygon defined by points

    .. grid-item-card:: :class:`~objects_sketch.Rectangle`

        .. image:: _build/assets/objects/rectangle_example.svg

        +++
        Rectangle defined by width and height

    .. grid-item-card:: :class:`~objects_sketch.RectangleRounded`

        .. image:: _build/assets/objects/rectangle_rounded_example.svg

        +++
        Rectangle with rounded corners defined by width, height, and radius

    .. grid-item-card:: :class:`~objects_sketch.RegularPolygon`

        .. image:: _build/assets/objects/regular_polygon_example.svg

        +++
        RegularPolygon defined by radius and number of sides

    .. grid-item-card:: :class:`~objects_sketch.SlotArc`

        .. image:: _build/assets/objects/slot_arc_example.svg

        +++
        SlotArc defined by arc and height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterPoint`

        .. image:: _build/assets/objects/slot_center_point_example.svg

        +++
        SlotCenterPoint defined by two points and a height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterToCenter`

        .. image:: _build/assets/objects/slot_center_to_center_example.svg

        +++
        SlotCenterToCenter defined by center separation and height

    .. grid-item-card:: :class:`~objects_sketch.SlotOverall`

        .. image:: _build/assets/objects/slot_overall_example.svg

        +++
        SlotOverall defined by end-to-end length and height

    .. grid-item-card:: :class:`~drafting.TechnicalDrawing`

        .. image:: _build/assets/objects/tech_drawing.svg

        +++
        A technical drawing with descriptions

    .. grid-item-card:: :class:`~objects_sketch.Text`

        .. image:: _build/assets/objects/text_example.svg

        +++
        Text defined by string and font parameters

    .. grid-item-card:: :class:`~objects_sketch.Trapezoid`

        .. image:: _build/assets/objects/trapezoid_example.svg

        +++
        Trapezoid defined by width, height and interior angles

    .. grid-item-card:: :class:`~objects_sketch.Triangle`

        .. image:: _build/assets/objects/triangle_example.svg

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
.. autoclass:: Ellipse
.. autoclass:: drafting.ExtensionLine
.. autoclass:: Polygon
.. autoclass:: Rectangle
.. autoclass:: RectangleRounded
.. autoclass:: RegularPolygon
.. autoclass:: SlotArc
.. autoclass:: SlotCenterPoint
.. autoclass:: SlotCenterToCenter
.. autoclass:: SlotOverall
.. autoclass:: drafting.TechnicalDrawing
.. autoclass:: Text
.. autoclass:: Trapezoid
.. autoclass:: Triangle

3D Objects
----------

.. grid:: 3

    .. grid-item-card:: :class:`~objects_part.Box`

        .. image:: _build/assets/objects/box_example.svg

        +++
        Box defined by length, width, height

    .. grid-item-card:: :class:`~objects_part.Cone`

        .. image:: _build/assets/objects/cone_example.svg

        +++
        Cone defined by radii and height

    .. grid-item-card:: :class:`~objects_part.ConvexPolyhedron`

        .. image:: _build/assets/objects/convex_polyhedron_example.svg

        +++
        Convex Polyhedron defined by points

    .. grid-item-card:: :class:`~objects_part.CounterBoreHole`

        .. image:: _build/assets/objects/counter_bore_hole_example.svg

        +++
        Counter bore hole defined by radii and depths

    .. grid-item-card:: :class:`~objects_part.CounterSinkHole`

        .. image:: _build/assets/objects/counter_sink_hole_example.svg

        +++
        Counter sink hole defined by radii and depth and angle

    .. grid-item-card:: :class:`~objects_part.Cylinder`

        .. image:: _build/assets/objects/cylinder_example.svg

        +++
        Cylinder defined by radius and height

    .. grid-item-card:: :class:`~objects_part.Hole`

        .. image:: _build/assets/objects/hole_example.svg

        +++
        Hole defined by radius and depth

    .. grid-item-card:: :class:`~objects_part.Sphere`

        .. image:: _build/assets/objects/sphere_example.svg

        +++
        Sphere defined by radius and arc angles

    .. grid-item-card:: :class:`~objects_part.Torus`

        .. image:: _build/assets/objects/torus_example.svg

        +++
        Torus defined major and minor radii

    .. grid-item-card:: :class:`~objects_part.Wedge`

        .. image:: _build/assets/objects/wedge_example.svg

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

.. include:: objects/text.rst


Custom Objects
--------------

All of the objects presented above were created using one of three base object classes:
:class:`~objects_curve.BaseLineObject` , :class:`~objects_sketch.BaseSketchObject` , and
:class:`~objects_part.BasePartObject` .  Users can use these base object classes to
easily create custom objects that have all the functionality of the core objects.

.. image:: _build/assets/examples/card_box.svg
    :align: center
    :height: 300px

Here is an example of a custom sketch object specially created as part of the design of
this playing card storage box (:download:`see the playing_cards.py example <../examples/playing_cards.py>`):

.. literalinclude:: ../examples/playing_cards.py
    :language: build123d
    :start-after: [Club]
    :end-before: [Club]

Here the new custom object class is called ``Club`` and it's a sub-class of
:class:`~objects_sketch.BaseSketchObject` .  The ``__init__`` method contains all
of the parameters used to instantiate the custom object, specially a ``height``,
``rotation``, ``align``, and ``mode`` - your objects may contain a sub or super set of
these parameters but should always contain a ``mode`` parameter such that it
can be combined with a builder's object.

Next is the creation of the object itself, in this case a sketch of the club suit.

The final line calls the ``__init__`` method of the super class - i.e.
:class:`~objects_sketch.BaseSketchObject` with its parameters.

That's it, now the ``Club`` object can be used anywhere a :class:`~objects_sketch.Circle`
would be used - with either the Algebra or Builder API.

.. image:: _build/assets/objects/buildline_example_6.svg
    :align: center
    :height: 300px
