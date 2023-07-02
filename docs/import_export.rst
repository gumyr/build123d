#############
Import/Export
#############

Methods and functions specific to exporting and importing build123d objects are defined below.

For example:

.. code-block:: python

    with BuildPart() as box_builder:
        Box(1, 1, 1)
    box_builder.part.export_step("box.step")

.. py:module:: topology
   :noindex:

.. automethod:: Shape.export_3mf
   :noindex:
.. automethod:: Shape.export_brep
   :noindex:
.. automethod:: Shape.export_dxf
   :noindex:
.. automethod:: Shape.export_stl
   :noindex:
.. automethod:: Shape.export_step
   :noindex:
.. automethod:: Shape.export_stl
   :noindex:
.. automethod:: Shape.export_svg
   :noindex:

.. py:module:: importers

.. autofunction:: import_brep
.. autofunction:: import_step
.. autofunction:: import_stl
.. autofunction:: import_svg
.. autofunction:: import_svg_as_buildline_code
