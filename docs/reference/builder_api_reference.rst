.. _builder_api_reference:

#####################
Builder API Reference
#####################

The four builders, followed by the attributes, selector methods and enums
they share.

************
The Builders
************

.. py:module:: build_line

.. autoclass:: BuildLine
    :members:

.. py:module:: build_sketch

.. autoclass:: BuildSketch
    :members:

.. py:module:: build_part

.. autoclass:: BuildPart
    :members:

.. py:module:: build_sheet

.. autoclass:: BuildSheet
    :members:

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

*****
Units
*****

build123d works in millimetres and grams. A dimension written as a bare
number is in millimetres. The constants below are the size of each unit in
those terms, so multiplying by one converts a value given in that unit:
``2 * IN`` is 50.8, and ``3 * MM`` is 3. Dividing converts the other way:
``part.volume / IN**3`` is a volume in cubic inches.

.. py:module:: build_constants

.. list-table::
    :header-rows: 1
    :widths: 20 30 50

    * - Constant
      - Value
      - Unit
    * - ``MC``
      - 0.001
      - micron (micrometre)
    * - ``MM``
      - 1
      - millimetre
    * - ``CM``
      - 10
      - centimetre
    * - ``M``
      - 1000
      - metre
    * - ``THOU``
      - 0.0254
      - thousandth of an inch
    * - ``IN``
      - 25.4
      - inch
    * - ``FT``
      - 304.8
      - foot
    * - ``G``
      - 1
      - gram
    * - ``KG``
      - 1000
      - kilogram
    * - ``LB``
      - 453.59237
      - pound

.. py:data:: MC
             MM
             CM
             M
             THOU
             IN
             FT

    Length constants, as in the table above.

.. py:data:: G
             KG
             LB

    Mass constants, as in the table above.

.. py:data:: G_PER_LB

    The number of grams in a pound, 453.59237.

.. py:data:: UNITS_PER_METER

    A dictionary from each length :class:`~build_enums.Unit` to the number
    of that unit in a metre.

.. py:data:: UNITS_PER_KILOGRAM

    A dictionary from each mass :class:`~build_enums.Unit` to the number of
    that unit in a kilogram.

The :class:`~build_enums.Unit` enum names the same units where a function
takes one as a parameter, as ``mass(Unit.LB)`` does.

*********
Locations
*********

.. autoclass:: build_common::Locations
.. autoclass:: build_common::GridLocations
.. autoclass:: build_common::HexLocations
.. autoclass:: build_common::PolarLocations
