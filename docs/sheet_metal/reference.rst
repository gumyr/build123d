.. _sheet_metal_reference:

#########
Reference
#########

The full signatures of everything on the preceding pages. The builder and its
parameters first, then the enums the operations take, then the operations in
the order a part usually meets them.

*******
Builder
*******

.. autoclass:: build_sheet.BuildSheet
    :members:
    :noindex:

.. autoclass:: build123d.sheet_utils.SheetMetalParameters
    :members:
    :noindex:

*****
Enums
*****

.. autoclass:: build_enums.SheetSurface
    :members:
    :undoc-members:
    :noindex:

.. autoclass:: build_enums.BendPosition
    :members:
    :undoc-members:
    :noindex:

.. autoclass:: build_enums.FlangeLength
    :members:
    :undoc-members:
    :noindex:

.. autoclass:: build_enums.HemType
    :members:
    :undoc-members:
    :noindex:

.. autoclass:: build_enums.ReliefType
    :members:
    :undoc-members:
    :noindex:

**********
Operations
**********

.. autofunction:: operations_sheet.flange
.. autofunction:: operations_sheet.bend
.. autofunction:: operations_sheet.jog
.. autofunction:: operations_sheet.hem
.. autofunction:: operations_sheet.miter
.. autofunction:: operations_sheet.corner_relief
.. autofunction:: operations_sheet.bend_relief
.. autofunction:: operations_sheet.unfold

.. autofunction:: operations_part.thicken
    :noindex:

*************
Shell methods
*************

The ``Shell`` methods the operations are built on, for Algebra mode and for
assembling a sheet from faces by hand.

.. automethod:: topology.Shell.make_sheet
    :noindex:

.. automethod:: topology.Shell.cut_sheet
    :noindex:

.. automethod:: topology.Shell.unfold
    :noindex:

.. automethod:: topology.Shell.flats
    :noindex:

.. automethod:: topology.Shell.bends
    :noindex:

.. automethod:: topology.Shell.rims
    :noindex:

.. automethod:: topology.Shell.fold_lines
    :noindex:
