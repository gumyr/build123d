.. _projection_shape:

############
Onto a shape
############

``project_to_shape`` casts faces, edges or wires onto the surface of a shape
along a direction, the way a label is cast onto a curved part. What comes
back lies on that surface: faces ready to be extruded into the part, or
edges to follow.

.. image:: /how_to/assets/projection/shape_emboss.svg
    :align: center

.. literalinclude:: /how_to/projection/projection_examples.py
    :language: build123d
    :start-after: [shape_emboss]
    :end-before: [shape_emboss]

In ``BuildPart`` the objects default to the pending faces and edges, those
of the sketches drawn since the last operation, the target to the part, and
the direction to the normal of the sketch's plane. The projected faces are
pending in turn, so an ``extrude`` follows directly, exactly as it would after
the sketch itself. In Algebra mode the objects and target are given, and the
direction too unless every object is a planar face, which projects along its
own normal. The direction is never turned toward the part: a sketch above the
part on ``Plane.XY.offset(10)`` faces up, so it takes ``direction=(0, 0, -1)``
or a plane that faces the part, as the example above does.

**********************
Which surfaces to keep
**********************

The projection meets every surface in its path. A face cast down onto a
plate lands on the plate's top and on its underside; cast onto a stepped
part it lands on each step and on each face behind it. ``hit`` says which to
keep.

.. image:: /how_to/assets/projection/shape_hits.svg
    :align: center

.. literalinclude:: /how_to/projection/projection_examples.py
    :language: build123d
    :start-after: [shape_hits]
    :end-before: [shape_hits]

.. list-table::
    :header-rows: 1
    :widths: 22 78

    * - ``hit``
      - Keeps
    * - ``Hit.ALL``
      - every surface met, nearest first. The default, and what the
        operation has always done.
    * - ``Hit.NEAREST``
      - the first surface met, the stepped front of a part as one region.
    * - ``Hit.FARTHEST``
      - the last surface met.
    * - ``Hit.VISIBLE``
      - what a viewer behind the objects, looking along the direction, sees:
        the surfaces facing the viewer with the parts hidden behind nearer
        surfaces removed.

``Hit.VISIBLE`` splits the target along its silhouette first, so a face that
wraps round from the front to the back of the part, a cylinder's side say,
contributes only its front. It needs a direction; the conical projection of a
curve from a ``center`` has no single direction and takes the other three.

*******************
Curves onto a shape
*******************

An edge or wire projects the same way and comes back as edges or wires on
the surface, nearest first. ``Hit.NEAREST`` picks the near side of a drum,
where ``Hit.ALL`` would give the far side too.

.. image:: /how_to/assets/projection/shape_curve.svg
    :align: center

.. literalinclude:: /how_to/projection/projection_examples.py
    :language: build123d
    :start-after: [shape_curve]
    :end-before: [shape_curve]

*****
Notes
*****

* The direct methods :meth:`Face.project_to_shape() <topology.Face.project_to_shape>`,
  :meth:`Wire.project_to_shape() <topology.Wire.project_to_shape>` and
  :meth:`Edge.project_to_shape() <topology.Edge.project_to_shape>` take the same
  ``hit`` argument and are what the operation calls.
* A face projected along a direction it is edge-on to has no area in that
  direction and gives nothing.
* A surface behind the objects, against the direction, is never met. The
  direction is the one given, or the sketch plane's or face's normal as drawn.
