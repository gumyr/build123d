.. _import_export_reference:

###########################
Import and Export Reference
###########################

The exporters and importers. :ref:`import_export` shows how they are used.

************
2D exporters
************

.. autoclass:: exporters.ExportDXF

.. autoclass:: exporters.ExportSVG

.. autoclass:: exporters.Export2D

.. autoclass:: exporters.LineType

.. autoclass:: exporters.DotLength

************
3D exporters
************

.. py:module:: exporters3d

.. autofunction:: export_brep

.. autofunction:: export_gltf

.. autofunction:: export_obj

.. autofunction:: export_step

.. autofunction:: export_stl

.. autofunction:: export_to_pcbway

******
Meshes
******

.. autoclass:: mesher.Mesher

************
2D importers
************

.. py:module:: import_dxf
.. autofunction:: import_dxf

.. py:module:: importers
.. autofunction:: import_svg
.. autofunction:: import_svg_as_buildline_code

************
3D importers
************

.. autofunction:: import_brep
.. autofunction:: import_step
.. autofunction:: import_stl

.. autofunction:: build123d.detect_primitives
