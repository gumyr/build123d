.. _builder_api_reference:

#####################
Builder API Reference
#####################

****************
Selector Methods
****************

.. automethod:: build_common::Builder.vertices
.. automethod:: build_common::Builder.faces
.. automethod:: build_common::Builder.edges
.. automethod:: build_common::Builder.wires
.. automethod:: build_common::Builder.solids

*****
Enums
*****

.. py:module:: build_enums

.. autoclass:: Align
.. autoclass:: CenterOf
.. autoclass:: FontStyle
.. autoclass:: GeomType
.. autoclass:: Keep
.. autoclass:: Kind
.. autoclass:: Mode
.. autoclass:: Select
.. autoclass:: SortBy
.. autoclass:: Transition
.. autoclass:: Until

*********
Locations
*********

.. autoclass:: build_common::Locations
.. autoclass:: build_common::GridLocations
.. autoclass:: build_common::HexLocations
.. autoclass:: build_common::PolarLocations

******************************
Generic Objects and Operations
******************************

There are several objects and operations that apply to more than one type
of builder which are listed here. The builder that these operations apply
to is determined by context.

.. py:module:: operations_generic

=======
Objects
=======
.. autoclass:: add

==========
Operations
==========
.. autoclass:: bounding_box
.. autoclass:: chamfer
.. autoclass:: fillet
.. autoclass:: mirror
.. autoclass:: offset
.. autoclass:: scale
.. autoclass:: split

*********
BuildLine
*********
.. py:module:: build_line

.. autoclass:: BuildLine
    :members:

.. py:module:: objects_curve

=======
Objects
=======
.. autoclass:: Bezier
.. autoclass:: CenterArc
.. autoclass:: EllipticalCenterArc
.. autoclass:: Helix
.. autoclass:: JernArc
.. autoclass:: Line
.. autoclass:: PolarLine
.. autoclass:: Polyline
.. autoclass:: RadiusArc
.. autoclass:: SagittaArc
.. autoclass:: Spline
.. autoclass:: TangentArc
.. autoclass:: ThreePointArc

***********
BuildSketch
***********

.. py:module:: build_sketch

.. autoclass:: BuildSketch
    :members:

.. py:module:: objects_sketch

=======
Objects
=======
.. autoclass:: Circle
.. autoclass:: Ellipse
.. autoclass:: Polygon
.. autoclass:: Rectangle
.. autoclass:: RectangleRounded
.. autoclass:: RegularPolygon
.. autoclass:: SlotArc
.. autoclass:: SlotCenterPoint
.. autoclass:: SlotCenterToCenter
.. autoclass:: SlotOverall
.. autoclass:: Text
.. autoclass:: Trapezoid

.. py:module:: operations_sketch

==========
Operations
==========
.. autoclass:: make_face
.. autoclass:: make_hull

*********
BuildPart
*********

.. py:module:: build_part

.. autoclass:: BuildPart
    :members:

.. py:module:: objects_part

=======
Objects
=======
.. autoclass:: Box
.. autoclass:: Cone
.. autoclass:: Cylinder
.. autoclass:: Sphere
.. autoclass:: Torus
.. autoclass:: Wedge
.. autoclass:: CounterBoreHole
.. autoclass:: CounterSinkHole
.. autoclass:: Hole

.. py:module:: operations_part

==========
Operations
==========
.. autoclass:: extrude
.. autoclass:: loft
.. autoclass:: revolve
.. autoclass:: section
.. autoclass:: sweep
