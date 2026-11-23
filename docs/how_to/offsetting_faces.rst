.. _offsetting_faces:

#######################################
Offsetting a face on a curved surface
#######################################

``offset`` grows or shrinks a flat face within its plane, as
:ref:`sketching` shows. Given a face that is not flat, the side of a part or
a shape wrapped onto one, it does the same within the face's own surface:
the boundary moves the given distance *along the surface*, and the result
lies on that surface, ready to be thickened into the part or sunk into it.

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - To
      - use
    * - grow a curved face
      - ``offset(face, amount)``
    * - shrink it
      - a negative ``amount``
    * - square the corners, on a cylinder or a cone
      - ``kind=Kind.INTERSECTION``
    * - inset a face that goes all the way round a part from its rims
      - ``offset(side, -amount)``
    * - raise the result from the part, or sink it in
      - ``thicken``
    * - get each piece of a face that a shrink parts
      - ``Face.offset_2d``

In the pictures the face that was given and its offset are drawn in blue;
the knob is shown as it ends up.

****************
Growing a face
****************

.. image:: /how_to/assets/offsetting_faces/grow.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [grow]
            :end-before: [grow]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [grow_algebra]
            :end-before: [grow_algebra]

A 20 by 10 label is wrapped onto the side of a can with
:meth:`Face.wrap <topology.Face.wrap>`, and ``offset`` grows it by 2 all
round. The 2 is measured on the surface, so the pad is the same shape a
flat label grown by 2 would wrap into, with its outside corners rounded.
``thicken`` then raises it 1 from the can.

In builder mode the offset face is left pending, as a sketch is, and
``thicken`` picks it up. The flat rectangle is drawn in a ``BuildSketch``
of its own first, since a sketch object belongs in a sketch. In algebra
mode ``offset`` returns a sketch holding the face on the can.

******************
Shrinking a face
******************

.. image:: /how_to/assets/offsetting_faces/shrink.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [shrink]
            :end-before: [shrink]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [shrink_algebra]
            :end-before: [shrink_algebra]

A negative amount moves the boundary inwards. Here the label shrunk by 2
is thickened 1 *into* the can, a negative amount again, and taken out of
it, which leaves a recess with a margin of 2 inside the label's outline.

****************
Square corners
****************

.. image:: /how_to/assets/offsetting_faces/corners.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [corners]
            :end-before: [corners]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [corners_algebra]
            :end-before: [corners_algebra]

``kind`` shapes the corners of a grown face as it does for a flat one.
``Kind.ARC``, the default, rounds each outside corner with an arc of the
offset's own radius; ``Kind.INTERSECTION`` carries the sides on until they
meet.

Square corners are available on a plane, a cylinder and a cone, the
surfaces that unroll flat without stretching. On any other surface only
``Kind.ARC`` can be made, and another kind raises ``ValueError``.

**************************************
A face that goes all the way round
**************************************

.. image:: /how_to/assets/offsetting_faces/round.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [round]
            :end-before: [round]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [round_algebra]
            :end-before: [round_algebra]

The side of a knob is one face all the way round, and the seam where it
meets itself is not part of its boundary. Offsetting it moves only its two
rims: shrunk by 4 it is a band 4 in from each rim, measured down the slope,
and still one face. Sunk 1 into the knob it makes a grip.

A face grown until it meets itself round a cylinder or a cone joins up in
the same way, and comes back as one face all the way round.

***********************************
On a sphere, or any other surface
***********************************

.. image:: /how_to/assets/offsetting_faces/sphere.svg
    :align: center

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [sphere]
            :end-before: [sphere]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/offsetting_faces.py
            :language: build123d
            :start-after: [sphere_algebra]
            :end-before: [sphere_algebra]

A sphere does not unroll, and neither does a torus, a spline surface or
most surfaces of revolution. On these the boundary is moved along the
surface's geodesics, its shortest paths, so the distance is still measured
on the surface, and the corners are rounded. It takes longer than on a
cylinder: tenths of a second for a face like this one.

********************************************
The pieces of a face that a shrink parts
********************************************

.. image:: /how_to/assets/offsetting_faces/parts.svg
    :align: center

.. literalinclude:: /how_to/offsetting_faces.py
    :language: build123d
    :start-after: [parts]
    :end-before: [parts]

Shrinking can part a face. The bar between these two discs is 1.5 wide,
so shrinking by 1 removes it and leaves the discs as two faces.

:meth:`Face.offset_2d <topology.Face.offset_2d>` is the method behind the
operation, used the same way in both modes. It returns the faces of the
result as a list, and takes a ``tolerance`` for the curves it has to fit.
The ``offset`` operation returns the same faces together in one sketch.

*************************
What cannot be offset
*************************

* The apex of a cone and the pole of a sphere are points a face made this
  way cannot include. A face that reaches one, or an offset that would,
  raises ``ValueError``.
* A face shrunk until nothing is left of it raises ``ValueError``.
* A face grown past the end of its surface, the edge of a spline patch,
  ends there.
* With ``Kind.INTERSECTION`` or ``Kind.TANGENT``, an outline grown until it
  closes on itself, as the letter C does, raises ``RuntimeError``, and so
  can an outline with curved edges that are not arcs. ``Kind.ARC`` handles
  both.

********
See also
********

* :ref:`projection_faces` puts flat faces onto a curved part in the first
  place.
* :func:`~operations_generic.offset` and
  :meth:`Face.offset_2d <topology.Face.offset_2d>` in the reference.
* :meth:`Face.offset <topology.Face.offset>` is a different thing: it moves
  a whole face along its normals onto another surface, so that a cylinder
  changes radius.
