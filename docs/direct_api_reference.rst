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

The class inheritance diagram for the direct api is shown below. Note that the ``Mixin1D``
and ``Mixin3D`` classes add supplementary functionality specific to 1D
(``Edge`` and ``Wire``) and 3D (``Compound`` and ``Solid``) objects respectively.
Note that a ``Compound`` may be contain only 1D, 2D (``Face``)  or 3D objects.

.. inheritance-diagram:: direct_api
   :parts: 1


*****************
Geometric Objects
*****************
The geometric classes defined by build123d are defined below. This parameters to the
CAD objects described in the following section are frequently of these types.

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
The CAD object classes defined by build123d are defined below.

.. autoclass:: BoundBox
.. autoclass:: Color
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

*************************
Importer/Exporter Objects
*************************
Classes specific to importing and exporting build123d objects are defined below.

.. autoclass:: SVG

*************
Joint Objects
*************
Joint classes which are used to position Solid and Compound objects relative to each
other are defined below.

.. autoclass:: Joint
.. autoclass:: RigidJoint
.. autoclass:: RevoluteJoint
.. autoclass:: LinearJoint
.. autoclass:: CylindricalJoint
.. autoclass:: BallJoint
