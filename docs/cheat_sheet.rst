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
            | :class:`~build_line.Bezier`
            | :class:`~build_line.CenterArc`
            | :class:`~build_line.EllipticalCenterArc`
            | :class:`~build_line.Helix`
            | :class:`~build_line.JernArc`
            | :class:`~build_line.Line`
            | :class:`~build_line.PolarLine`
            | :class:`~build_line.Polyline`
            | :class:`~build_line.RadiusArc`
            | :class:`~build_line.SagittaArc`
            | :class:`~build_line.Spline`
            | :class:`~build_line.TangentArc`
            | :class:`~build_line.ThreePointArc`

        .. grid-item-card:: 2D - BuildSketch

            | :class:`~build_generic.Add`
            | :class:`~build_sketch.Circle`
            | :class:`~build_sketch.Ellipse`
            | :class:`~build_sketch.Polygon`
            | :class:`~build_sketch.Rectangle`
            | :class:`~build_sketch.RectangleRounded`
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
            | :class:`~build_generic.Chamfer`
            | :class:`~build_generic.Mirror`
            | :class:`~build_generic.Offset`
            | :class:`~build_generic.Scale`
            | :class:`~build_generic.Split`

        .. grid-item-card:: 2D - BuildSketch

            | :class:`~build_generic.Fillet`
            | :class:`~build_sketch.MakeFace`
            | :class:`~build_sketch.MakeHull`
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
            | :meth:`~build_common.Builder.solids`

.. card:: Selector Operators

    +----------+------------------------------------------------------------+---------------------------------------------------+
    | Operator | Operand                                                    | Method                                            |
    +==========+============================================================+===================================================+
    | >        | :class:`~build_enums.SortBy`, :class:`~build_common.Axis`  | :meth:`~direct_api.ShapeList.sort_by`             |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | <        | :class:`~build_enums.SortBy`, :class:`~build_common.Axis`  | :meth:`~direct_api.ShapeList.sort_by`             |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | >>       | :class:`~build_enums.SortBy`, :class:`~build_common.Axis`  | :meth:`~direct_api.ShapeList.group_by`\[-1\]      |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | <<       | :class:`~build_enums.SortBy`, :class:`~build_common.Axis`  | :meth:`~direct_api.ShapeList.group_by`\[0\]       |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | \|       | :class:`~direct_api.Axis`, :class:`~build_enums.GeomType`  | :meth:`~direct_api.ShapeList.filter_by`           |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    | []       |                                                            | python indexing / slicing                         |
    +----------+------------------------------------------------------------+---------------------------------------------------+
    |          | :class:`~direct_api.Axis`                                  | :meth:`~direct_api.ShapeList.filter_by_position`  |
    +----------+------------------------------------------------------------+---------------------------------------------------+

.. card:: Edge and Wire Operators

    +----------+---------------------+-----------------------------------------+---------------------------------+
    | Operator | Operand             | Method                                  | Description                     |
    +==========+=====================+=========================================+=================================+
    | @        | 0.0 <= float <= 1.0 | :meth:`~direct_api.Mixin1D.position_at` | Position as Vector along object |
    +----------+---------------------+-----------------------------------------+---------------------------------+
    | %        | 0.0 <= float <= 1.0 | :meth:`~direct_api.Mixin1D.tangent_at`  | Tangent as Vector along object  |
    +----------+---------------------+-----------------------------------------+---------------------------------+

.. card:: Shape Operators

    +----------+---------------------+-----------------------------------------+---------------------------------------------+
    | Operator | Operand             | Method                                  | Description                                 |
    +==========+=====================+=========================================+=============================================+
    | ==       | Any                 | :meth:`~direct_api.Shape.is_same`       | Compare CAD objects not including meta data |
    +----------+---------------------+-----------------------------------------+---------------------------------------------+


.. card:: Plane Operators

    +----------+----------------------------+-----------------------------+
    | Operator | Operand                    | Description                 |
    +==========+============================+=============================+
    | ==       | :class:`~direct_api.Plane` | Check for equality          |
    +----------+----------------------------+-----------------------------+
    | !=       | :class:`~direct_api.Plane` | Check for inequality        |
    +----------+----------------------------+-----------------------------+
    | \-       | :class:`~direct_api.Plane` | Reverse direction of normal |
    +----------+----------------------------+-----------------------------+
    | \*       | :class:`~direct_api.Plane` | Relocate by Location        |
    +----------+----------------------------+-----------------------------+

.. card:: Vector Operators

    +----------+------------------------------+-------------------------------------+---------------------+
    | Operator | Operand                      | Method                              | Description         |
    +==========+==============================+=====================================+=====================+
    | \+       | :class:`~direct_api.Vector`  | :meth:`~direct_api.Vector.add`      | add                 |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \-       | :class:`~direct_api.Vector`  | :meth:`~direct_api.Vector.sub`      | subtract            |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \*       | ``float``                    | :meth:`~direct_api.Vector.multiply` | multiply by scalar  |
    +----------+------------------------------+-------------------------------------+---------------------+
    | \/       | ``float``                    | :meth:`~direct_api.Vector.multiply` | divide by scalar    |
    +----------+------------------------------+-------------------------------------+---------------------+

.. card:: Vertex Operators

    +----------+-----------------------------+-------------------------------------+
    | Operator | Operand                     | Method                              |
    +==========+=============================+=====================================+
    | \+       | :class:`~direct_api.Vertex` | :meth:`~direct_api.Vertex.add`      |
    +----------+-----------------------------+-------------------------------------+
    | \-       | :class:`~direct_api.Vertex` | :meth:`~direct_api.Vertex.sub`      |
    +----------+-----------------------------+-------------------------------------+

.. card:: Enums

    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Align`      | MIN, CENTER, MAX                                                                                                                        |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.CenterOf`   | GEOMETRY, MASS, BOUNDING_BOX                                                                                                            |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.FontStyle`  | REGULAR, BOLD, ITALIC                                                                                                                   |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.GeomType`   | BEZIER, BSPLINE, CIRCLE, CONE, CYLINDER, ELLIPSE, EXTRUSION, HYPERBOLA, LINE, OFFSET, OTHER, PARABOLA, PLANE, REVOLUTION, SPHERE, TORUS |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Keep`       | TOP, BOTTOM, BOTH                                                                                                                       |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Kind`       | ARC, INTERSECTION, TANGENT                                                                                                              |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Mode`       | ADD, SUBTRACT, INTERSECT, REPLACE, PRIVATE                                                                                              |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Select`     | ALL, LAST                                                                                                                               |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.SortBy`     | LENGTH, RADIUS, AREA, VOLUME, DISTANCE                                                                                                  |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Transition` | RIGHT, ROUND, TRANSFORMED                                                                                                               |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
    | :class:`~build_enums.Until`      | NEXT, LAST                                                                                                                              |
    +----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
