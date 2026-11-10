.. _projection_faces:

##################
Faces along a path
##################

A label on a curved part is a row of flat letters laid along a curve on the
surface, each standing on the surface at its own place. Two methods do that,
and they differ in how they put a letter onto the surface.

.. image:: /how_to/assets/projection/faces.svg
    :align: center

******************************
One surface: ``wrap_faces``
******************************

:meth:`~topology.Face.wrap_faces` writes the letters into the face's own
parameter space through a :class:`~topology.UVFrame`. On a developable
surface, a cylinder or a cone, that is exact: the letters keep their lengths
as if the sheet had been rolled onto the part. Seams are handled. The path
must lie on the one face.

.. literalinclude:: /how_to/projection/projection_examples.py
    :language: build123d
    :start-after: [faces_wrap]
    :end-before: [faces_wrap]

**********************************
Several faces: ``project_faces``
**********************************

:meth:`~topology.Shape.project_faces` stands each letter on the surface at
its point on the path, x along the path's tangent and z along the surface
normal, and projects it onto the whole shape along that normal. A letter
that straddles the boundary between two faces of the part, round a filleted
corner, comes back as a shell with a piece on each. That is the case a wrap
of one face cannot do. Projection foreshortens on a slope, so on a single
surface it is the approximate choice.

.. literalinclude:: /how_to/projection/projection_examples.py
    :language: build123d
    :start-after: [faces_project]
    :end-before: [faces_project]

*****
Notes
*****

* Both lay the faces out by their x positions: the leftmost point lands
  ``start`` of the way along the path and each face's centre as far beyond
  that as it is to the right of the leftmost point.
* The path's direction is the reading direction: the letters stand with x
  along it and z along the surface normal. An edge taken from the part may run
  the other way, which stands the letters on their heads; ``reversed()`` turns
  it round.
* ``project_faces`` finds the surface normal by a ray toward the shape's
  centre, so the centre must lie behind the surface along the whole path,
  and a letter placed at a sharp corner projects poorly.
* The :ref:`bicycle tire <examples-bicycle_tire>` wraps a tread onto one
  face; the :ref:`bracelet <examples-bracelet>` projects a label over several.
