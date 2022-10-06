#############
API Reference
#############

****************
Selector Methods
****************

.. py:module:: build_common

.. automethod:: Builder.vertices
.. automethod:: Builder.faces
.. automethod:: Builder.edges
.. automethod:: Builder.wires

.. py:module:: build_part

.. automethod:: BuildPart.solids

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

.. _shape_list:

=========
ShapeList
=========

.. py:module:: build_common

.. autoclass:: ShapeList
    :members:

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
.. autoclass:: BuildFace
.. autoclass:: BuildHull

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

*****************
Geometric Objects
*****************

.. py:module:: build_common
    :noindex:

.. _axis:
.. autoclass:: Axis
.. autoclass:: Rotation

*************
Shape Objects
*************