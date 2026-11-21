
####################
Direct API Reference
####################

The Direct API is an interface layer between the primary user interface APIs
(Algebra and Builders) and the OpenCascade (OCCT) API.

The original Direct API work began from CadQuery's Direct API. build123d has
since diverged substantially in structure, naming, typing, topology handling,
selection tools, object composition, and Builder integration. The build123d
project gratefully acknowledges the CadQuery contributors whose work helped make
this API possible.

*****************
Geometric Objects
*****************
The geometric classes defined by build123d are defined below. The parameters to the
CAD objects described in the following section are frequently of these types.

.. inheritance-diagram:: geometry
   :parts: 1

.. py:module:: geometry

.. autoclass:: Axis
   :special-members: __copy__,__deepcopy__, __neg__
.. autoclass:: BoundBox
.. autoclass:: OrientedBoundBox
.. autoclass:: Color
   :special-members: __copy__,__deepcopy__
.. autoclass:: Location
   :special-members: __copy__,__deepcopy__, __mul__, __pow__, __eq__, __neg__
.. autoclass:: Pos
.. autoclass:: Rot
.. autoclass:: Matrix
   :special-members: __copy__,__deepcopy__
.. autoclass:: Plane
   :special-members: __copy__,__deepcopy__, __eq__, __ne__, __neg__, __mul__
.. autoclass:: Rotation
.. autoclass:: Vector
   :special-members: __add__, __sub__, __mul__, __truediv__, __rmul__, __neg__, __abs__, __eq__, __copy__, __deepcopy__

.. autoclass:: GeomEncoder

Three type aliases appear throughout the signatures of build123d. None is a
class to be created: each is a name for a set of forms, and wherever one is
asked for, any of its forms may be given.

.. py:class:: VectorLike

   A position or a direction in space. Any of:

   - a :class:`Vector`;
   - ``tuple[float, float]``, a 2D coordinate ``(x, y)``, with Z taken as 0;
   - ``tuple[float, float, float]``, a 3D coordinate ``(x, y, z)``;
   - ``Sequence[float]``, any other sequence of two or three numbers, such
     as a list.

.. py:class:: ColorLike

   A colour. Any of:

   - a :class:`Color`;
   - ``str``, a colour name such as ``"red"``;
   - ``tuple[str, float]``, a name and an alpha, as ``("red", 0.5)``;
   - ``tuple[float, float, float]``, red, green and blue from 0 to 1, as
     ``(1, 0, 0)``;
   - ``tuple[float, float, float, float]``, the same with an alpha, as
     ``(1, 0, 0, 0.5)``;
   - ``int``, a hexadecimal RGB value, as ``0xFF0000``;
   - ``tuple[int, int]``, a hexadecimal value and an alpha from 0 to 255,
     as ``(0xFF0000, 0x80)``;
   - an OCP ``Quantity_ColorRGBA``.

   A shape's ``color`` can be set to any of these, and reads back as a
   :class:`Color`.

.. py:class:: RotationLike

   A rotation. Either of:

   - a :class:`Rotation`;
   - ``tuple[float, float, float]``, the angles of rotation about the X, Y
     and Z axes, in degrees.

*******************
Topological Objects
*******************
The topological object classes defined by build123d are defined below.

Note that the :class:`~topology.Mixin1D` and :class:`~topology.Mixin3D` classes add
supplementary functionality specific to 1D
(:class:`~topology.Edge` and :class:`~topology.Wire`) and 3D (:class:`~topology.Compound` and
:class:`~topology.Solid`) objects respectively.
Note that a :class:`~topology.Compound` may contain only 1D, 2D (:class:`~topology.Face`)  or 3D objects.

.. inheritance-diagram:: topology.shape_core topology.zero_d topology.one_d topology.two_d topology.three_d topology.composite topology.utils
   :parts: 1

.. py:module:: topology

.. autoclass:: Compound
.. autoclass:: Edge
.. autoclass:: Face
   :special-members: __neg__
.. autoclass:: Mixin1D
   :special-members: __matmul__, __mod__
.. autoclass:: Mixin2D
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
.. autoclass:: DrawingViewOutput
.. autoclass:: UVFrame
.. autoclass:: Curve
   :special-members: __matmul__, __mod__
.. autoclass:: Part
.. autoclass:: Sketch

.. autofunction:: new_edges
.. autofunction:: topo_distance_to
.. autofunction:: delta
.. autofunction:: edges_to_wires
.. autofunction:: polar
.. autofunction:: topo_explore_common_vertex
.. autofunction:: topo_explore_connected_edges
.. autoexception:: DraftAngleError


*************
Import/Export
*************
Methods and functions specific to exporting and importing build123d objects are defined below.

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
other, and the dictionary of joints a part holds, are defined below. The :ref:`joints`
section contains the class description of the derived Joint classes.

.. py:module:: topology
   :noindex:

.. autoclass:: Joint
.. autoclass:: JointDict
