####################
Direct API Reference
####################

The Direct API is an interface layer between the primary user interface API
(the Builders) and the OpenCascade (OCCT) API. This API is based on the CadQuery
Direct API (thank you to all of the CadQuery contributors that made this possible)
with the following major changes:

* PEP8 compliance
* New Axis class
* New ShapeList class enabling sorting and filtering of shape objects
* Literal strings replaced with Enums

*****************
Geometric Objects
*****************
The geometric classes defined by build123d are defined below. This parameters to the
CAD objects described in the following section are frequently of these types.

.. inheritance-diagram:: geometry
   :parts: 1

.. py:module:: geometry

.. autoclass:: Axis
   :special-members: __copy__,__deepcopy__, __neg__
.. autoclass:: BoundBox
.. autoclass:: Color
   :special-members: __copy__,__deepcopy__
.. autoclass:: Location
   :special-members: __copy__,__deepcopy__, __mul__, __pow__, __eq__, __neg__
.. autoclass:: LocationEncoder
.. autoclass:: Pos
.. autoclass:: Rot
.. autoclass:: Matrix
   :special-members: __copy__,__deepcopy__
.. autoclass:: Plane
   :special-members: __copy__,__deepcopy__, __eq__, __ne__, __neg__, __mul__
.. autoclass:: Rotation
.. autoclass:: Vector
   :special-members: __add__, __sub__, __mul__, __truediv__, __rmul__, __neg__, __abs__, __eq__, __copy__, __deepcopy__

*******************
Topological Objects
*******************
The topological object classes defined by build123d are defined below.

Note that the :class:`~topology.Mixin1D` and :class:`~topology.Mixin3D` classes add
supplementary functionality specific to 1D
(:class:`~topology.Edge` and :class:`~topology.Wire`) and 3D (:class:`~topology.Compound` and
`~topology.Solid`) objects respectively.
Note that a :class:`~topology.Compound` may be contain only 1D, 2D (:class:`~topology.Face`)  or 3D objects.

.. inheritance-diagram:: topology
   :parts: 1

.. py:module:: topology

.. autoclass:: Compound
.. autoclass:: Edge
.. autoclass:: Face
   :special-members: __neg__
.. autoclass:: Mixin1D
   :special-members: __matmul__, __mod__
.. autoclass:: Mixin3D
.. autoclass:: Shape
   :special-members: __add__, __sub__, __and__, __rmul__, __eq__, __copy__, __deepcopy__, __hash__
.. autoclass:: ShapeList
   :special-members: __gt__, __lt__, __rshift__, __lshift__, __or__, __and__, __sub__, __getitem__
.. autoclass:: Shell
.. autoclass:: Solid
.. autoclass:: Wire
.. autoclass:: Vertex
   :special-members: __add__, __sub__
.. autoclass:: Curve
   :special-members: __matmul__, __mod__
.. autoclass:: Part
.. autoclass:: Sketch


*************
Import/Export
*************
Methods and functions specific to exporting and importing build123d objects are defined below.

.. py:module:: topology
   :noindex:

.. automethod:: Shape.export_brep
   :noindex:
.. automethod:: Shape.export_stl
   :noindex:
.. automethod:: Shape.export_step
   :noindex:
.. automethod:: Shape.export_stl
   :noindex:

.. py:module:: importers
   :noindex:

.. autofunction:: import_brep
   :noindex:
.. autofunction:: import_step
   :noindex:
.. autofunction:: import_stl
   :noindex:
.. autofunction:: import_svg
   :noindex:
.. autofunction:: import_svg_as_buildline_code
   :noindex:


************
Joint Object
************
Base Joint class which is used to position Solid and Compound objects relative to each
other are defined below. The :ref:`joints` section contains the class description of the
derived Joint classes.

.. py:module:: topology
   :noindex:

.. autoclass:: Joint
