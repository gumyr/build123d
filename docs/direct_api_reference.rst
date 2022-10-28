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

.. py:module:: direct_api

*****************
Geometric Objects
*****************

.. autoclass:: Axis
.. autoclass:: Location
.. autoclass:: Matrix
.. autoclass:: Plane
.. autoclass:: Rotation
.. autoclass:: Vector
.. autoclass:: Vertex

***********
CAD Objects
***********

.. autoclass:: BoundBox
.. autoclass:: Compound
.. autoclass:: Edge
.. autoclass:: Face
.. autoclass:: Mixin1D
.. autoclass:: Mixin3D
.. autoclass:: Shape
.. autoclass:: ShapeList
.. autoclass:: Shell
.. autoclass:: Solid
.. autoclass:: Wire
