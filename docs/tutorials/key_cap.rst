.. _tutorial_key_cap:

#########
A key cap
#########

A moulded plastic part has a look of its own. Its sides lean, so that it
will come out of the mould. It is a thin shell, because thick plastic
sinks as it cools. And inside the shell are ribs and posts that run from
wherever they are needed up to the underside of the outer skin, whatever
shape that skin happens to be. In this tutorial you will build such a
part, a key cap for a Cherry MX keyboard switch:

.. image:: /tutorials/assets/key_cap/keycap_finished.png
    :align: center
    :width: 60%
    :alt: A key cap, drawn see-through to show the ribs and socket inside

Along the way you will:

* lean the sides of a block with ``draft``,
* hollow it with ``offset``, and see why that comes before rounding its
  edges,
* tell the outside edges of a shell from the inside ones with
  ``Convexity``,
* measure the inside of the part with ``section``, and
* extrude ribs with ``until``, so that they stop at the underside of the
  cap wherever it is.

It takes about twenty-five minutes and follows on from
:ref:`tutorial_beyond_extrude`. How the builder and algebra tabs on this
page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the key cap,
in millimetres.

.. literalinclude:: /tutorials/key_cap.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The values are introduced with the step that uses them. As before, each
step below shows the whole of the rest of the file as it stands at that
point.

***********************
Step 2: The block
***********************

The key cap starts as a square block, a sketch extruded straight up.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [block_builder]
            :end-before: [block_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [block_algebra]
            :end-before: [block_algebra]

.. image:: /tutorials/assets/key_cap/keycap_block.png
    :align: center
    :width: 50%

*******************************
Step 3: Draft the sides
*******************************

The sides of a key cap lean in toward the top. That lean is called
*draft*, and :func:`~operations_part.draft` applies it to faces a part
already has.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [draft_builder]
            :end-before: [draft_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [draft_algebra]
            :end-before: [draft_algebra]

.. image:: /tutorials/assets/key_cap/keycap_draft.png
    :align: center
    :width: 50%

``draft`` takes three things:

* the faces to lean. ``filter_by(Axis.Z)`` would keep the faces that face
  along Z, the top and the bottom; ``reverse=True`` keeps the others, the
  four sides.
* a *neutral plane*. Where a face crosses this plane it stays put, and the
  rest of the face swings about that line. With ``Plane.XY`` the bottom of
  the cap keeps its size and the top shrinks, from 18 to 12.6.
* the angle, in degrees from upright.

.. note::

    For a shape that is drafted from the moment it is made,
    ``extrude(amount=height, taper=draft_angle)`` does this in one step
    and gives exactly the same block. ``draft`` is for faces that already
    exist, and it can lean some of them and leave the rest alone.

***************************
Step 4: Dish the top
***************************

A fingertip sits in a shallow dish. The dish is part of a large sphere,
taken out of the top of the block.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [dish_builder]
            :end-before: [dish_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [dish_algebra]
            :end-before: [dish_algebra]

.. image:: /tutorials/assets/key_cap/keycap_dish.png
    :align: center
    :width: 50%

The centre of the sphere is ``dish_radius`` above the height its lowest
point should reach, ``dish_low``, and ``dish_shift`` toward the front of
the key, so the dish is deeper at the front than at the back. Cutting one
ready-made solid from another is the subject of
:ref:`tutorial_combining_solids`, and this is a case where it is the right
tool.

``rotation=(90, 0, 0)`` tips the sphere on its side. A sphere has two
poles, like a globe, and as made they are at its top and bottom, which
would put one in the middle of the dish. A pole is a point where the
surface is awkward to work with, and the hollowing of the next step fails
on it. Tipped over, the poles are out to the sides, clear of the key cap.

***********************
Step 5: Hollow it
***********************

The outside is the right shape, so now the block can become a shell.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [hollow_builder]
            :end-before: [hollow_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [hollow_algebra]
            :end-before: [hollow_algebra]

.. image:: /tutorials/assets/key_cap/keycap_hollow.png
    :align: center
    :width: 50%

This is the hollowing of :ref:`tutorial_beyond_extrude`: ``offset`` by a
negative amount moves every face inward by ``wall``, and ``openings``
names the face to leave open, here the bottom, the lowest face of the
part. The wall is the same thickness everywhere, under the dish as well as
up the sides.

*********************************
Step 6: Round the outside
*********************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [round_builder]
            :end-before: [round_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [round_algebra]
            :end-before: [round_algebra]

.. image:: /tutorials/assets/key_cap/keycap_round.png
    :align: center
    :width: 50%

Hollowing doubled the number of edges: every outside edge now has a
partner on the inside, at much the same height, so selecting by height
alone would find both. What tells them apart is which way the part turns
at the edge:

* ``filter_by(Convexity.CONVEX)`` keeps the edges where the surface turns
  outward, as at the corner of a box. Every outside edge is one of these.
  The inside edges are *concave*, like the corner of a room, and are
  dropped.
* The rim round the bottom is convex too, inside and out, and it is to
  stay sharp. ``group_by(Axis.Z)`` puts the edges in groups by height,
  lowest first, and ``[1:]`` takes every group but the first.

That leaves the eight outside edges, and ``fillet`` rounds them.

.. note::

    Why not round the edges first and hollow afterwards, since
    :ref:`tutorial_beyond_extrude` said to finish the outside before
    hollowing? Because ``offset`` has to move the rounded edges inward
    too, and a rounding of radius 1 moved inward by 1 has nothing left to
    be. Hollowing a rounded part works only when the wall is thicker than
    the rounding. Hollowing first and rounding the outside afterwards
    works for any wall.

***************************************
Step 7: Ribs that reach the top
***************************************

The switch pushes on a socket in the middle of the key cap, and the socket
is held by two ribs that cross the inside. The ribs start at
``rib_height`` and go up until they meet the underside of the dished top.
Two things about them are not known: how long they should be at that
height, since the sides lean, and how tall, since the top is curved. The
part can answer both.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [ribs_builder]
            :end-before: [ribs_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [ribs_algebra]
            :end-before: [ribs_algebra]

.. image:: /tutorials/assets/key_cap/keycap_ribs.png
    :align: center
    :width: 50%

**How long.** :func:`~operations_part.section` cuts the part with a
plane and gives back the cut surface as a face. Cutting a shell gives a
frame: the outer wire is the outside of the wall, and the one inner wire
is the cavity. The size of that wire's bounding box, 13.8 each way, is the
room there is for a rib at that height, and the sketch uses it. In builder
mode ``section`` cuts the part being built; in algebra mode it is given
the part.

**How tall.** ``extrude`` is given ``until=Until.NEXT`` in place of an
amount. The sketch is pushed upward until it meets the part, and it ends
on the surface it meets, following its shape: the top of each rib is
curved to fit the underside of the dish. In builder mode the part it
meets is the one being built. In algebra mode it is named with ``target``,
and the result is added to the cap.

The ribs are a little too long higher up, where the sides have leaned
further in, and their ends run into the wall. That is what joins them to
it.

Change ``dish_low`` or ``dish_radius`` and the ribs still end on the
underside; change ``wall`` or ``draft_angle`` and they still fit across.
Neither number was ever worked out.

*************************
Step 8: The socket
*************************

The stem of the switch is a cross, and the key cap pushes onto it. The
socket is a round post with a cross-shaped hole, hanging down from the
ribs.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [socket_builder]
            :end-before: [socket_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/key_cap.py
            :language: build123d
            :start-after: [socket_algebra]
            :end-before: [socket_algebra]

.. image:: /tutorials/assets/key_cap/keycap_socket.png
    :align: center
    :width: 50%

The sketch is on the same plane as the ribs, and a negative ``amount``
extrudes it downward from there. It stops half a millimetre short of the
bottom of the key cap.

Try a ``draft_angle`` of 8, a ``wall`` of 1.5 or a ``dish_low`` of 8, and
look at the underside again.

********************
What you learned
********************

* :func:`~operations_part.draft` leans faces a part already has, about the
  line where each crosses a neutral plane. ``extrude`` with ``taper``
  does the same for a new extrusion.
* Hollow a part with :func:`~operations_generic.offset` before rounding
  its edges, unless the wall is thicker than the rounding.
* ``filter_by(Convexity.CONVEX)`` keeps outside corners and
  ``Convexity.CONCAVE`` inside ones, which separates the two skins of a
  shell.
* :func:`~operations_part.section` cuts a part with a plane, and the
  cut can be measured.
* ``extrude`` with ``until=Until.NEXT`` runs until it meets the part and
  ends on the surface it meets. ``Until.LAST`` carries on to the last
  surface in its path instead.
* A feature sized from the part itself still fits when the part changes.

:ref:`tutorial_selecting_and_finishing` introduced selections and
``fillet``, and :ref:`tutorial_projection_chalice` uses the same idea of
measuring a part to size what is added to it.
