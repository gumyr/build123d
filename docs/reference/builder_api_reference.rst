.. _builder_api_reference:

############################
Builder Common API Reference
############################

The following are common to all the builders.

**********
Attributes
**********

.. autoattribute:: build_common::Builder.label

****************
Selector Methods
****************

.. automethod:: build_common::Builder.vertices
.. automethod:: build_common::Builder.faces
.. automethod:: build_common::Builder.edges
.. automethod:: build_common::Builder.wires
.. automethod:: build_common::Builder.solids

****************
Selector Results
****************

A selector returns a :class:`~topology.ShapeList`; ``group_by`` returns a
``GroupBy`` holding one for each group.

.. autoclass:: topology::GroupBy
   :special-members: __getitem__

*****
Enums
*****

.. py:module:: build_enums

.. autoclass:: Align
.. autoclass:: AngularDirection
.. autoclass:: ApproxOption
.. autoclass:: BendPosition
.. autoclass:: CenterOf
.. autoclass:: ContinuityLevel
.. autoclass:: Convexity
.. autoclass:: Extrinsic
.. autoclass:: FontStyle
.. autoclass:: FrameMethod
.. autoclass:: GeomType
.. autoclass:: HeadType
.. autoclass:: HemType
.. autoclass:: Hit
.. autoclass:: Intrinsic
.. autoclass:: Keep
.. autoclass:: Kind
.. autoclass:: LengthFrom
.. autoclass:: LengthMode
.. autoclass:: MeshType
.. autoclass:: Mode
.. autoclass:: NumberDisplay
.. autoclass:: PageSize
.. autoclass:: PositionMode
.. autoclass:: PrecisionMode
.. autoclass:: ReliefType
.. autoclass:: Sagitta
.. autoclass:: Select
.. autoclass:: SheetSurface
.. autoclass:: Side
.. autoclass:: SortBy
.. autoclass:: Tangency
.. autoclass:: TextAlign
.. autoclass:: Transition
.. autoclass:: Unit
.. autoclass:: Until

*********
Locations
*********

.. autoclass:: build_common::Locations
.. autoclass:: build_common::GridLocations
.. autoclass:: build_common::HexLocations
.. autoclass:: build_common::PolarLocations
