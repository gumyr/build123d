.. _projection_plane:

############
Onto a plane
############

``project_to_plane`` casts geometry onto a plane along its normal, each
object from its own side, and hands back the result flat, in the plane's own
coordinates. It exists for one workflow above all: bring a 3D object into a
sketch or a line, enhance it there, and use the result to modify the object.

.. image:: /assets/projection/plane_faces.svg
    :align: center

.. literalinclude:: /projection_examples.py
    :language: build123d
    :start-after: [plane_faces]
    :end-before: [plane_faces]

In ``BuildSketch`` or ``BuildLine`` the objects are projected onto the
builder's construction plane, ``Plane.XY``, and ``workplane`` must not be
given. A sketch may be placed on many workplanes at once, so there is no one
plane to project onto; the projection is drawn in the sketch's own coordinates
like any other content and placed with it on exit. A sketch on ``Plane.XZ``
therefore holds the object's shadow on ``Plane.XY``, standing in ``Plane.XZ``;
to draw a side view, bring the object into the sketch's coordinates first.
With no objects given, the sketch or line projects the object of the builder
it is nested in, so a part can be brought into a sketch inside its own
``BuildPart``. In Algebra mode the plane is given as ``workplane`` and the
result is returned in that plane's coordinates: a ``Sketch`` of faces, a
``Curve`` of edges, or a list of points.

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

.. image:: /assets/projection/plane_silhouette.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /projection_examples.py
            :language: build123d
            :start-after: [plane_silhouette]
            :end-before: [plane_silhouette]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /projection_examples.py
            :language: build123d
            :start-after: [plane_silhouette_algebra]
            :end-before: [plane_silhouette_algebra]

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /projection_examples.py
            :language: build123d
            :start-after: [plane_edges]
            :end-before: [plane_edges]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /projection_examples.py
            :language: build123d
            :start-after: [plane_edges_algebra]
            :end-before: [plane_edges_algebra]

************
Algebra mode
************

The same rules hold with an explicit workplane, and points come back as
``Vector`` positions in the plane's coordinates.

.. literalinclude:: /projection_examples.py
    :language: build123d
    :start-after: [plane_algebra]
    :end-before: [plane_algebra]

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
