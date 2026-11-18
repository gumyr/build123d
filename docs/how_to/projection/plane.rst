.. _projection_plane:

############
Onto a plane
############

``project_to_plane`` casts geometry onto a plane along its normal, each
object from its own side, and hands back the result flat, in the plane's own
coordinates. It exists for one workflow above all: bring a 3D object into a
sketch or a line, enhance it there, and use the result to modify the object.

.. image:: /how_to/assets/projection/plane_faces.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_faces]
            :end-before: [plane_faces]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_faces_algebra]
            :end-before: [plane_faces_algebra]

The plane to project onto is the ``workplane`` argument. It is always
required, in a builder as much as in Algebra mode, and no plane is inferred
from the builder. The result lies in that plane's coordinates: a ``Sketch`` of
faces, a ``Curve`` of edges, or a list of points. In Algebra mode it is
returned. In ``BuildSketch`` or ``BuildLine`` it is drawn in the builder's own
coordinates like any other content and placed with it on exit, so projecting
onto the plane the sketch was created with puts the result back where the
object is. With no objects given, the sketch or line projects the object of
the builder it is nested in, so a part can be brought into a sketch inside its
own ``BuildPart``.

****************************
What a builder can hold
****************************

A builder takes what it can hold and reduces or refuses the rest.

* ``BuildLine`` holds edges. An edge or wire projects to its edges; a face or
  a solid contributes its edges, so a part's top face gives the outline of
  that face. Coincident shadows become one edge, so the twelve edges of a box
  give the four of its outline.
* ``BuildSketch`` holds faces. A face casts its shadow whichever way it
  curves or faces, unless it stands edge-on to the plane, in which case it
  has no area there and is skipped. A solid, shell or compound casts its
  **silhouette**: the shadows of all its faces fused, holes included.
* Points are projected and returned, never drawn, so that lines can be built
  from a part's vertices. Points and shapes cannot be mixed in one call.
* Edges and wires cannot go into a sketch. Those raise unless
  ``mode=Mode.PRIVATE``, which returns the result without adding it.

.. image:: /how_to/assets/projection/plane_silhouette.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_silhouette]
            :end-before: [plane_silhouette]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_silhouette_algebra]
            :end-before: [plane_silhouette_algebra]

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_edges]
            :end-before: [plane_edges]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_edges_algebra]
            :end-before: [plane_edges_algebra]

******************
Onto another plane
******************

Any plane will do as the ``workplane``, and the result comes back in that
plane's coordinates. In Builder mode, create the sketch on the same plane and
it carries the result there: the side view of the part, standing in
``Plane.XZ``. To work on one face of a part, use ``Plane(face)`` for both.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_side]
            :end-before: [plane_side]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/projection/projection_examples.py
            :language: build123d
            :start-after: [plane_side_algebra]
            :end-before: [plane_side_algebra]

Points come back as ``Vector`` positions in the plane's coordinates, as the
last line of the Algebra example shows.


*****************************
Choosing the plane for a view
*****************************

A projection plane is often wanted at a given orientation and position
relative to the part, with its x axis along a known edge. The
:class:`~geometry.Plane` constructor builds one from an origin, an x direction
and the projection direction as its normal, projecting the x direction onto
the plane if it is not already in it. The result is passed as ``workplane``
in Algebra mode or places the sketch that receives the projection.

.. code-block:: build123d

    view_plane = Plane(origin + direction * distance, x_dir=x_dir, z_dir=direction)

*****
Notes
*****

* ``project_to_plane`` replaces the plane form of ``project``, which also
  projected onto the part inside ``BuildPart``. ``project`` works as it did,
  with a deprecation warning, for one release; its two jobs are now
  ``project_to_plane`` and :ref:`project_to_shape <projection_shape>`.
  ``project_workplane`` is deprecated with it: the ``Plane`` constructor
  above does what it did.
* Projection onto a plane is a parallel projection. For a perspective view
  of a part see :ref:`drawing_view <projection_view>`.

********
See also
********

* :ref:`tutorial_projection_chalice` casts a part onto a plane, draws on its
  footprint and casts the drawing back.
* :ref:`projection_shape` is the projection in the other direction, from a
  sketch onto a part.
* :ref:`sketching` covers what can be done with the sketch once the
  projection is in it.
