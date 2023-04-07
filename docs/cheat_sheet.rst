.. _cheat_sheet:

###########
Cheat Sheet
###########

.. card:: Stateful Contexts

    | :class:`~build_line.BuildLine` :class:`~build_part.BuildPart` :class:`~build_sketch.BuildSketch`
    | :class:`~build_common.GridLocations` :class:`~build_common.HexLocations` :class:`~build_common.Locations` :class:`~build_common.PolarLocations`
    | :class:`~build_common.Workplanes`

.. card:: Objects

    .. grid:: 3

        .. grid-item-card:: 1D - BuildLine

            | :meth:`~operations_generic.add`
            | :class:`~objects_curve.Bezier`
            | :class:`~objects_curve.CenterArc`
            | :class:`~objects_curve.EllipticalCenterArc`
            | :class:`~objects_curve.Helix`
            | :class:`~objects_curve.JernArc`
            | :class:`~objects_curve.Line`
            | :class:`~objects_curve.PolarLine`
            | :class:`~objects_curve.Polyline`
            | :class:`~objects_curve.RadiusArc`
            | :class:`~objects_curve.SagittaArc`
            | :class:`~objects_curve.Spline`
            | :class:`~objects_curve.TangentArc`
            | :class:`~objects_curve.ThreePointArc`

        .. grid-item-card:: 2D - BuildSketch

            | :meth:`~operations_generic.add`
            | :class:`~objects_sketch.Circle`
            | :class:`~objects_sketch.Ellipse`
            | :class:`~objects_sketch.Polygon`
            | :class:`~objects_sketch.Rectangle`
            | :class:`~objects_sketch.RectangleRounded`
            | :class:`~objects_sketch.RegularPolygon`
            | :class:`~objects_sketch.SlotArc`
            | :class:`~objects_sketch.SlotCenterPoint`
            | :class:`~objects_sketch.SlotCenterToCenter`
            | :class:`~objects_sketch.SlotOverall`
            | :class:`~objects_sketch.Text`
            | :class:`~objects_sketch.Trapezoid`

        .. grid-item-card:: 3D - BuildPart

            | :meth:`~operations_generic.add`
            | :class:`~objects_part.Box`
            | :class:`~objects_part.Cone`
            | :class:`~objects_part.Cylinder`
            | :class:`~objects_part.Sphere`
            | :class:`~objects_part.Torus`
            | :class:`~objects_part.Wedge`

.. card:: Operations

    .. grid:: 3

        .. grid-item-card:: 1D - BuildLine

            | :class:`~geometry.BoundBox`
            | :meth:`~operations_generic.chamfer`
            | :meth:`~operations_generic.mirror`
            | :meth:`~operations_generic.offset`
            | :meth:`~operations_generic.scale`
            | :meth:`~operations_generic.split`

        .. grid-item-card:: 2D - BuildSketch

            | :meth:`~operations_generic.fillet`
            | :meth:`~operations_sketch.make_face`
            | :meth:`~operations_sketch.make_hull`
            | :meth:`~operations_generic.mirror`
            | :meth:`~operations_generic.offset`
            | :meth:`~operations_generic.scale`
            | :meth:`~operations_generic.split`

        .. grid-item-card:: 3D - BuildPart

            | :class:`~objects_part.CounterBoreHole`
            | :class:`~objects_part.CounterSinkHole`
            | :meth:`~operations_part.extrude`
            | :class:`~objects_part.Hole`
            | :meth:`~operations_part.loft`
            | :meth:`~operations_generic.fillet`
            | :meth:`~operations_generic.mirror`
            | :meth:`~operations_generic.offset`
            | :meth:`~operations_part.revolve`
            | :meth:`~operations_generic.scale`
            | :meth:`~operations_part.section`
            | :meth:`~operations_generic.split`
            | :meth:`~operations_part.sweep`

.. card:: Selectors

    .. grid:: 3

        .. grid-item-card:: 1D - BuildLine

            | :meth:`~build_common.Builder.vertices`
            | :meth:`~build_common.Builder.edges`
            | :meth:`~build_common.Builder.wires`

        .. grid-item-card:: 2D - BuildSketch

            | :meth:`~build_common.Builder.vertices`
            | :meth:`~build_common.Builder.edges`
            | :meth:`~build_common.Builder.wires`
            | :meth:`~build_common.Builder.faces`

        .. grid-item-card:: 3D - BuildPart

            | :meth:`~build_common.Builder.vertices`
            | :meth:`~build_common.Builder.edges`
            | :meth:`~build_common.Builder.wires`
            | :meth:`~build_common.Builder.faces`
            | :meth:`~build_common.Builder.solids`

.. card:: Selector Operators

    +----------+------------------------------------------------------------+---------------------------------------------------+
    | Operator | Operand                                                    | Method                                            |
    +==========+============================================================+===================================================+
    | >        | :class:`~build_enums.SortBy`, :class:`~geometry.Axis`  | :meth:`~topology.ShapeList.sort_by`               |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | <        | :class:`~build_enums.SortBy`, :class:`~geometry.Axis`  | :meth:`~topology.ShapeList.sort_by`               |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | >>       | :class:`~build_enums.SortBy`, :class:`~geometry.Axis`  | :meth:`~topology.ShapeList.group_by`\[-1\]        |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | <<       | :class:`~build_enums.SortBy`, :class:`~geometry.Axis`  | :meth:`~topology.ShapeList.group_by`\[0\]         |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | \|       | :class:`~geometry.Axis`, :class:`~build_enums.GeomType`    | :meth:`~topology.ShapeList.filter_by`             |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | []       |                                                            | python indexing / slicing                         |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    |          | :class:`~geometry.Axis`                                    | :meth:`~topology.ShapeList.filter_by_position`    |
    +----------+------------------------------------------------------------+---------------------------------------------------+

.. card:: Edge and Wire Operators

    +----------+---------------------+-----------------------------------------+---------------------------------+
    | Operator | Operand             | Method                                  | Description                     |
    +==========+=====================+=========================================+=================================+
    | @        | 0.0 <= float <= 1.0 | :meth:`~topology.Mixin1D.position_at`   | Position as Vector along object |
    +----------+---------------------+-----------------------------------------+---------------------------------+
    | %        | 0.0 <= float <= 1.0 | :meth:`~topology.Mixin1D.tangent_at`    | Tangent as Vector along object  |
    +----------+---------------------+-----------------------------------------+---------------------------------+

.. card:: Shape Operators

    +----------+---------------------+-----------------------------------------+---------------------------------------------+
    | Operator | Operand             | Method                                  | Description                                 |
    +==========+=====================+=========================================+=============================================+
    | ==       | Any                 | :meth:`~topology.Shape.is_same`         | Compare CAD objects not including meta data |
    +----------+---------------------+-----------------------------------------+---------------------------------------------+


.. card:: Plane Operators

    +----------+----------------------------+-----------------------------+
    | Operator | Operand                    | Description                 |
    +==========+============================+=============================+
    | ==       | :class:`~geometry.Plane`   | Check for equality          |
    +----------+----------------------------+-----------------------------+
    | !=       | :class:`~geometry.Plane`   | Check for inequality        |
    +----------+----------------------------+-----------------------------+
    | \-       | :class:`~geometry.Plane`   | Reverse direction of normal |
    +----------+----------------------------+-----------------------------+
    | \*       | :class:`~geometry.Plane`   | Relocate by Location        |
    +----------+----------------------------+-----------------------------+

.. card:: Vector Operators

    +----------+------------------------------+-------------------------------------+---------------------+
    | Operator | Operand                      | Method                              | Description         |
    +==========+==============================+=====================================+=====================+
    | \+       | :class:`~geometry.Vector`    | :meth:`~geometry.Vector.add`        | add                 |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \-       | :class:`~geometry.Vector`    | :meth:`~geometry.Vector.sub`        | subtract            |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \*       | ``float``                    | :meth:`~geometry.Vector.multiply`   | multiply by scalar  |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \/       | ``float``                    | :meth:`~geometry.Vector.multiply`   | divide by scalar    |
    +----------+------------------------------+-------------------------------------+---------------------+

.. card:: Vertex Operators

    +----------+-----------------------------+-------------------------------------+
    | Operator | Operand                     | Method                              |
    +==========+=============================+=====================================+
    | \+       | :class:`~topology.Vertex`   | :meth:`~topology.Vertex.add`        |
    +----------+-----------------------------+-------------------------------------+
    | \-       | :class:`~topology.Vertex`   | :meth:`~topology.Vertex.sub`        |
    +----------+-----------------------------+-------------------------------------+

.. card:: Enums

    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Align`        | MIN, CENTER, MAX                                                                                                                        |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.ApproxOption` | ARC, NONE, SPLINE                                                                                                                       |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.CenterOf`     | GEOMETRY, MASS, BOUNDING_BOX                                                                                                            |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.FontStyle`    | REGULAR, BOLD, ITALIC                                                                                                                   |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.GeomType`     | BEZIER, BSPLINE, CIRCLE, CONE, CYLINDER, ELLIPSE, EXTRUSION, HYPERBOLA, LINE, OFFSET, OTHER, PARABOLA, PLANE, REVOLUTION, SPHERE, TORUS |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Keep`         | TOP, BOTTOM, BOTH                                                                                                                       |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Kind`         | ARC, INTERSECTION, TANGENT                                                                                                              |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Mode`         | ADD, SUBTRACT, INTERSECT, REPLACE, PRIVATE                                                                                              |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Select`       | ALL, LAST                                                                                                                               |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.SortBy`       | LENGTH, RADIUS, AREA, VOLUME, DISTANCE                                                                                                  |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Transition`   | RIGHT, ROUND, TRANSFORMED                                                                                                               |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Unit`         | MICRO, MILLIMETER, CENTIMETER, METER, INCH, FOOT                                                                                        |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Until`        | NEXT, LAST                                                                                                                              |
    +------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
