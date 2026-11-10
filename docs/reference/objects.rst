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

.. image:: /reference/assets/objects/align.svg
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
        Arc defined by center, radius, & angles


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
        Elliptical arc defined by center,  radii & angles

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
        Hyperbolic arc defined by center, radii & angles

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
        SlotCurve defined by a center line and height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterPoint`

        .. image:: /reference/assets/objects/slot_center_point_example.svg

        +++
        SlotCenterPoint defined by two points and a height

    .. grid-item-card:: :class:`~objects_sketch.SlotCenterToCenter`

        .. image:: /reference/assets/objects/slot_center_to_center_example.svg

        +++
        SlotCenterToCenter defined by center separation and height

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


Custom Objects
--------------

All of the objects presented above are normal Python classes built on the
``Base*Object`` classes. Users can use these same base classes to create their
own reusable objects that work like the core build123d objects in both Algebra
and Builder mode.

The base class is chosen from the dimensionality of the object being created:

.. list-table::
   :header-rows: 1

   * - Object being created
     - Base class
     - Builder
   * - 3D solid or part
     - :class:`~objects_part.BasePartObject`
     - :class:`~build_part.BuildPart`
   * - 2D face or sketch
     - :class:`~objects_sketch.BaseSketchObject`
     - :class:`~build_sketch.BuildSketch`
   * - Single 1D edge
     - :class:`~objects_curve.BaseEdgeObject`
     - :class:`~build_line.BuildLine`
   * - Connected 1D wire
     - :class:`~objects_curve.BaseLineObject`
     - :class:`~build_line.BuildLine`
   * - General 1D curve
     - :class:`~objects_curve.BaseCurveObject`
     - :class:`~build_line.BuildLine`

A custom object usually follows the same pattern:

#. Create a class that inherits from the appropriate ``Base*Object``.
#. Put the input parameters in the class ``__init__`` method.
#. Build the shape using normal build123d tools.
#. Pass the completed object to ``super().__init__(..., mode=mode)``.

The ``Base*Object`` class handles the Builder integration. Intermediate objects
created inside the custom object are isolated from the caller's Builder context,
so a helper ``Box``, ``Circle``, or ``Line`` used during construction doesn't
leak into the user's model. When the custom object is complete, it is published
once to the active Builder using the provided ``mode``. Any active
:class:`~build_common.Locations` context and any Builder ``placements`` are
applied at publication time, just as they are for the built-in objects.

Each built-in base class also declares which Builder it applies to. For example,
``BasePartObject`` applies to ``BuildPart`` and ``BaseSketchObject`` applies to
``BuildSketch``. If a custom object inherits from one of these base classes and
is used in the wrong Builder, build123d raises an error before the custom object
is constructed. This validation is provided by the inherited ``_applies_to``
attribute; most custom objects don't need to set it themselves unless they are
creating a new base class or intentionally changing the Builder compatibility.

.. image:: /reference/assets/objects/card_box.svg
  :align: center

Here is an example of a custom sketch object specially created as part of the design of
this playing card storage box (:download:`see the playing_cards.py example </../examples/playing_cards.py>`):

.. literalinclude:: /../examples/playing_cards.py
    :language: build123d
    :start-after: [Club]
    :end-before: [Club]

Here the new custom object class is called ``Club`` and it's a subclass of
:class:`~objects_sketch.BaseSketchObject` because it creates a 2D sketch object.
The ``__init__`` method contains the parameters used to instantiate the custom
object: ``height``, ``rotation``, ``align``, and ``mode``. Your objects may have
different parameters, but should usually include ``mode`` so they can be added
to, subtracted from, intersected with, or kept private in a Builder.

The middle of the method creates the object itself, in this case a sketch of the
club suit. The final line calls ``super().__init__`` with the completed sketch
and passes through the ``rotation``, ``align``, and ``mode`` parameters handled
by :class:`~objects_sketch.BaseSketchObject`.

That's it. The ``Club`` object can now be used anywhere a
:class:`~objects_sketch.Circle` would be used, with either the Algebra or
Builder API.

.. image:: /how_to/assets/build_line/buildline_example_6.svg
  :align: center
