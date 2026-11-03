.. _projection_reference:

#########
Reference
#########

The full signatures of everything on the preceding pages: the two operations,
the enum the shape form takes, the direct methods they call, and the view.

**********
Operations
**********

.. autofunction:: operations_generic.project_to_plane
    :noindex:

.. autofunction:: operations_part.project_to_shape
    :noindex:

*****
Enums
*****

.. autoclass:: build_enums.Hit
    :members:
    :undoc-members:
    :noindex:

**************
Direct methods
**************

.. automethod:: topology.Face.project_to_shape
    :noindex:

.. automethod:: topology.Wire.project_to_shape
    :noindex:

.. automethod:: topology.Edge.project_to_shape
    :noindex:

.. automethod:: topology.Face.silhouette_edges
    :noindex:

.. automethod:: topology.Face.wrap_faces
    :noindex:

.. automethod:: topology.Shape.project_faces
    :noindex:

****
View
****

.. automethod:: topology.Mixin1D.drawing_view
    :noindex:

.. autoclass:: topology.DrawingViewOutput
    :members:
    :noindex:
