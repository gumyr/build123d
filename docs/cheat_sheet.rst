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

            | :class:`~build_generic.Add`
            | :class:`~build_line.CenterArc`
            | :class:`~build_line.Helix`
            | :class:`~build_line.Line`
            | :class:`~build_line.PolarLine`
            | :class:`~build_line.Polyline`
            | :class:`~build_line.RadiusArc`
            | :class:`~build_line.SagittaArc`
            | :class:`~build_line.Spline`
            | :class:`~build_line.SagittaArc`
            | :class:`~build_line.TangentArc`
            | :class:`~build_line.ThreePointArc`

        .. grid-item-card:: 2D - BuildSketch

            | :class:`~build_generic.Add`
            | :class:`~build_sketch.Circle`
            | :class:`~build_sketch.Ellipse`
            | :class:`~build_sketch.Polygon`
            | :class:`~build_sketch.Rectangle`
            | :class:`~build_sketch.RegularPolygon`
            | :class:`~build_sketch.SlotArc`
            | :class:`~build_sketch.SlotCenterPoint`
            | :class:`~build_sketch.SlotCenterToCenter`
            | :class:`~build_sketch.SlotOverall`
            | :class:`~build_sketch.Text`
            | :class:`~build_sketch.Trapezoid`

        .. grid-item-card:: 3D - BuildPart

            | :class:`~build_generic.Add`
            | :class:`~build_part.Box`
            | :class:`~build_part.Cone`
            | :class:`~build_part.Cylinder`
            | :class:`~build_part.Sphere`
            | :class:`~build_part.Torus`
            | :class:`~build_part.Wedge`

.. card:: Operations

    .. grid:: 3

        .. grid-item-card:: 1D - BuildLine

            | :class:`~build_generic.BoundingBox`
            | :class:`~build_sketch.BuildFace`
            | :class:`~build_sketch.BuildHull`
            | :class:`~build_generic.Chamfer`
            | :class:`~build_generic.Mirror`
            | :class:`~build_generic.Offset`
            | :class:`~build_generic.Scale`
            | :class:`~build_generic.Split`

        .. grid-item-card:: 2D - BuildSketch

            | :class:`~build_generic.Fillet`
            | :class:`~build_generic.Mirror`
            | :class:`~build_generic.Offset`
            | :class:`~build_generic.Scale`
            | :class:`~build_generic.Split`

        .. grid-item-card:: 3D - BuildPart

            | :class:`~build_part.CounterBoreHole`
            | :class:`~build_part.CounterSinkHole`
            | :class:`~build_part.Extrude`
            | :class:`~build_part.Hole`
            | :class:`~build_part.Loft`
            | :class:`~build_generic.Fillet`
            | :class:`~build_generic.Mirror`
            | :class:`~build_generic.Offset`
            | :class:`~build_part.Revolve`
            | :class:`~build_generic.Scale`
            | :class:`~build_part.Section`
            | :class:`~build_generic.Split`

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
            | :meth:`~build_part.BuildPart.solids`

.. card:: Selector Operators

    +----------+------------------------------------------------------------+----------------------------------------------------+
    | Operator | Operand                                                    | Method                                             |
    +==========+============================================================+====================================================+
    | >        | :class:`~build_common.SortBy`, :class:`~build_common.Axis` | :meth:`~build_common.ShapeList.sort_by`            |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | <        | :class:`~build_common.SortBy`, :class:`~build_common.Axis` | :meth:`~build_common.ShapeList.sort_by`            |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | >>       | :class:`~build_common.SortBy`, :class:`~build_common.Axis` | :meth:`~build_common.ShapeList.group_by`\[-1\]     |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | <<       | :class:`~build_common.SortBy`, :class:`~build_common.Axis` | :meth:`~build_common.ShapeList.group_by`\[0\]      |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | %        | :class:`~build_common.GeomType`                            | :meth:`~build_common.ShapeList.filter_by_type`     |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | \|       | :class:`~build_common.Axis`                                | :meth:`~build_common.ShapeList.filter_by_axis`     |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    | []       |                                                            | python indexing / slicing                          |
    +----------+------------------------------------------------------------+----------------------------------------------------+
    |          | :class:`~build_common.Axis`                                | :meth:`~build_common.ShapeList.filter_by_position` |
    +----------+------------------------------------------------------------+----------------------------------------------------+

.. card:: Enums

    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.FontStyle`  | REGULAR, BOLD, ITALIC                                                                                                                   |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.GeomType`   | BEZIER, BSPLINE, CIRCLE, CONE, CYLINDER, ELLIPSE, EXTRUSION, HYPERBOLA, LINE, OFFSET, OTHER, PARABOLA, PLANE, REVOLUTION, SPHERE, TORUS |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Halign`     | CENTER, LEFT, RIGHT                                                                                                                     |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Keep`       | TOP, BOTTOM, BOTH                                                                                                                       |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Kind`       | ARC, INTERSECTION, TANGENT                                                                                                              |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Mode`       | ADD, SUBTRACT, INTERSECT, REPLACE, PRIVATE                                                                                              |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Select`     | ALL, LAST                                                                                                                               |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.SortBy`     | LENGTH, RADIUS, AREA, VOLUME, DISTANCE                                                                                                  |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Transition` | RIGHT, ROUND, TRANSFORMED                                                                                                               |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Until`      | NEXT, LAST                                                                                                                              |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_common.Valign`     | CENTER, TOP, BOTTOM                                                                                                                     |
    +-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
