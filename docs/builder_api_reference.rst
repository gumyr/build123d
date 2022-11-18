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
.. automethod:: build_part::BuildPart.solids

*****
Enums
*****

.. py:module:: build_common

.. autoclass:: FontStyle
.. autoclass:: GeomType
.. autoclass:: Halign
.. autoclass:: Keep
.. autoclass:: Kind
.. autoclass:: Mode
.. autoclass:: Select
.. autoclass:: SortBy
.. autoclass:: Transition
.. autoclass:: Until
.. autoclass:: Valign


******************************
Generic Objects and Operations
******************************

There are several objects and operations that apply to more than one type
of builder which are listed here. The builder that these operations apply
to is determined by context.

.. py:module:: build_generic

=======
Objects
=======
.. autoclass:: Add

==========
Operations
==========
.. autoclass:: BoundingBox
.. autoclass:: Chamfer
.. autoclass:: Fillet
.. autoclass:: Mirror
.. autoclass:: Offset
.. autoclass:: Scale
.. autoclass:: Split

*********
BuildLine
*********
.. py:module:: build_line

.. autoclass:: BuildLine
    :members:

=======
Objects
=======
.. autoclass:: CenterArc
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

=======
Objects
=======
.. autoclass:: Circle
.. autoclass:: Ellipse
.. autoclass:: Polygon
.. autoclass:: Rectangle
.. autoclass:: RegularPolygon
.. autoclass:: SlotArc
.. autoclass:: SlotCenterPoint
.. autoclass:: SlotCenterToCenter
.. autoclass:: SlotOverall
.. autoclass:: Text
.. autoclass:: Trapezoid

==========
Operations
==========
.. autoclass:: MakeFace
.. autoclass:: MakeHull

*********
BuildPart
*********

.. py:module:: build_part

.. autoclass:: BuildPart
    :members:

=======
Objects
=======
.. autoclass:: Box
.. autoclass:: Cone
.. autoclass:: Cylinder
.. autoclass:: Sphere
.. autoclass:: Torus
.. autoclass:: Wedge

==========
Operations
==========
.. autoclass:: CounterBoreHole
.. autoclass:: CounterSinkHole
.. autoclass:: Extrude
.. autoclass:: Hole
.. autoclass:: Loft
.. autoclass:: Revolve
.. autoclass:: Section
.. autoclass:: Sweep
