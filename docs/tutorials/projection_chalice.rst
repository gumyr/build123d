.. _tutorial_projection_chalice:

###################
An embossed chalice
###################

A sketch is flat, and most decoration starts as one: a band, a logo, a line
of text. The surfaces that decoration ends up on are often not flat at all.
*Projection* is how the two are brought together. It carries geometry along
a direction, as a lamp throws a shadow, and it works both ways: a part can
be cast down onto a plane to give a sketch, and a sketch can be cast onto a
part to give faces that lie on its surface.

In this tutorial you will use both, one after the other, to put a raised
scalloped band round the bowl of a chalice:

.. image:: /tutorials/assets/projection_chalice/chalice_finished.png
    :align: center
    :width: 60%
    :alt: A chalice with a scalloped band embossed on its bowl

Along the way you will:

* revolve a profile into a cup with a curved wall,
* cast the cup onto a plane with ``project_to_plane`` to get its footprint,
* draw a band in two dimensions, sized from that footprint,
* cast the band back onto the cup with ``project_to_shape``,
* choose which of the surfaces it meets to keep, with ``hit``, and
* give the projected face a thickness and join it to the cup.

It takes about twenty minutes and follows on from
:ref:`tutorial_beyond_extrude`. How the builder and algebra tabs on this
page work is described in :ref:`tutorial_sketch_then_extrude`.
:ref:`projection` describes each projection in full.

*****************
Step 1: Setup
*****************

Start a new Python file with the import and the dimensions of the
decoration, in millimetres.

.. literalinclude:: /tutorials/projection_chalice.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

As before, each step below shows the whole of the rest of the file as it
stands at that point.

*************************
Step 2: The profile
*************************

The chalice is round, so it is drawn as half of its cross-section and
revolved, as the collar was in :ref:`tutorial_beyond_extrude`. The profile
is on ``Plane.XZ``, so its coordinates read as *(distance from the centre
line, height)*.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [profile_builder]
            :end-before: [profile_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [profile_algebra]
            :end-before: [profile_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_profile.png
    :align: center
    :width: 55%

* ``outside`` is the outer wall, a ``Spline`` through six points from the
  edge of the foot, in along the stem, and out again to the lip. The
  tangents set the direction it leaves the foot and arrives at the lip.
* ``rim`` is the flat top of the lip, ``wall`` wide.
* ``inside`` is the hollow of the bowl: a quarter circle that starts at the
  inner end of the rim heading straight down, with a radius equal to its
  distance from the centre line, so that it ends on the centre line.
* ``axis`` runs down the centre line, and a last line along the bottom
  closes the outline.

``make_face`` fills the outline. In builder mode the sketch is made on
``Plane.XZ``; in algebra mode the lines are drawn flat and
``Plane.XZ *`` stands the finished face up.

Nowhere in this file is the widest radius of the chalice written down. The
spline passes through ``(50, 60)`` and ``(50, 80)``, and between them it
bulges a little further out. Keep that in mind for step 4.

*********************
Step 3: The cup
*********************

:func:`~operations_part.revolve` turns the profile round ``Axis.Z``, the
centre line it was drawn against.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [cup_builder]
            :end-before: [cup_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [cup_algebra]
            :end-before: [cup_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_cup.png
    :align: center
    :width: 55%

The chalice stands upright, with its foot at Z = -40 and its lip at
Z = 80. That is more than tidiness. The next step looks straight down on
it, and the plane to look down on is ``Plane.XY``, which is also where
sketches are drawn. Step 4 says why that matters.

***************************
Step 4: The footprint
***************************

The band has to fit the bowl, so the first thing needed is how big the
bowl is, seen from above. Rather than measure it, cast it:
:func:`~operations_generic.project_to_plane` casts a shape onto a plane
along the plane's normal.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [footprint_builder]
            :end-before: [footprint_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [footprint_algebra]
            :end-before: [footprint_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_footprint.png
    :align: center
    :width: 55%

In builder mode the projection is made inside a new sketch. With nothing
in its brackets ``project_to_plane`` casts the part being built onto the
sketch's plane and draws the result into the sketch. In algebra mode it is
given the part and the plane, and returns the result.

A solid casts its *silhouette*: one face covering everything the solid
hides from a viewer looking along the normal. For a round chalice that is
a disc, and its radius is the widest radius of the chalice, wherever up
its height that happens to be.

.. tip::

    To see the number, add a line after the code above:

    .. code-block:: build123d

        print(footprint.edge().radius)

    It is 51.31: the bulge of step 2, not the 50 of the lip. Change the
    spline and the footprint follows, and so does everything drawn from it.

.. note::

    ``project_to_plane`` gives its result in the plane's own coordinates:
    flat on ``Plane.XY`` at the origin, ready to be drawn on, whichever
    plane the shape was cast onto.

    Here the plane *is* ``Plane.XY``, so the footprint lies exactly where
    the shadow falls and there is nothing to think about. Had the profile
    been drawn flat and revolved round ``Axis.Y``, the chalice would lie
    along the Y axis. You would cast it onto ``Plane.XZ``, and the disc
    would still come back flat on ``Plane.XY``, no longer lined up with
    the chalice. Multiplying by the plane, ``Plane.XZ * footprint``, puts
    such a result back on the plane it was cast onto.

***********************
Step 5: The band
***********************

The band is drawn like any other sketch, taking its size from the
footprint.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [band_builder]
            :end-before: [band_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [band_algebra]
            :end-before: [band_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_band.png
    :align: center
    :width: 55%

* ``guide`` is the edge of the footprint moved in by ``inset``. The band
  must stay inside the footprint: any part of it outside would be cast
  past the chalice and land on nothing.
* ``positions`` gives points along a line by how far along they are, from
  0 at the start to 1 at the end. ``start`` and ``end`` are the two ends of
  the first tenth of the guide circle.
* ``RadiusArc`` is an arc between two points with a given radius. This one
  sags in from the guide circle toward the centre, and
  ``PolarLocations(0, scallops)`` repeats it ten times round the origin.
* ``make_face`` fills the ten arcs to make a scalloped disc, kept as
  ``inner``.
* ``offset`` grows that disc by ``band_width``. ``Kind.INTERSECTION`` keeps
  the points between the scallops sharp instead of rounding them.
* Taking ``inner`` back out of the grown disc leaves the band.

In builder mode the sketch already holds the footprint. ``offset`` shrinks
it where it is, and ``mode=Mode.REPLACE`` on ``make_face`` swaps it for the
scalloped disc instead of adding to it. In algebra mode each shape is a
variable of its own, and nothing has to be replaced.

The band is flat on ``Plane.XY``, at the height of the middle of the stem
and well clear of it, with the bowl above.

***************************
Step 6: Onto the cup
***************************

:func:`~operations_part.project_to_shape` casts the band along
``direction``, straight up, and gives back the part of the cup's surface
it lands on.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [project_builder]
            :end-before: [project_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [project_algebra]
            :end-before: [project_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_project.png
    :align: center
    :width: 55%

In builder mode ``project_to_shape`` takes the sketch that has been made
and not yet used, casts it onto the part, and leaves the result waiting
for the next operation, as a sketch waits for ``extrude``. In algebra mode
it is given the band and the cup, and the result is kept in ``on_cup``.

The result, in red, is no longer flat. It is a piece of the bowl's own
surface, cut to the outline of the band.

It is also more than twice the area of the band: 1475 square millimetres
against 636. Where the wall of the bowl is nearly level the band lands
almost unchanged, and where the wall climbs steeply the same width of band
is spread up a long stretch of it. That is why the points of the scallops,
which reach furthest out to where the wall is steepest, are drawn out into
tall spikes. Projection keeps the shape as seen along the direction and
lets everything else stretch.

``hit`` chooses among the surfaces that are met. A projection does not stop
at the first one: it carries on through the part. Without ``hit`` this one
would return thirty-two faces, nearest first: the underside of the bowl,
then the hollow inside it, the top of the rim, and the outside again where
it bulges above its widest point. ``Hit.NEAREST`` keeps the first of them,
which is the one wanted here.

*************************
Step 7: The relief
*************************

A face has no thickness. To emboss the band it is given some, and the
result is added to the cup.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [relief_builder]
            :end-before: [relief_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/projection_chalice.py
            :language: build123d
            :start-after: [relief_algebra]
            :end-before: [relief_algebra]

.. image:: /tutorials/assets/projection_chalice/chalice_finished.png
    :align: center
    :width: 55%

:func:`~operations_part.thicken` grows a face into a solid by moving every
point of it the same distance along the surface normal, so the band stands
``relief`` proud of the bowl all the way round and follows its curve. A
plain ``extrude`` would have moved it in one straight direction instead.
In builder mode ``thicken`` takes the projected face left waiting by the
last step and adds the result to the part; in algebra mode ``+=`` does the
adding.

The chalice has gained about 1460 cubic millimetres, the area of the
projected face times the relief, and it is still one valid solid.

Try 12 or 16 ``scallops``, or change one of the spline's points and watch
the band resize itself to the new bowl.

********************
What you learned
********************

* Projection carries geometry along a direction, from a part to a plane or
  from a sketch to a part.
* :func:`~operations_generic.project_to_plane` casts a solid's silhouette
  onto a plane, which measures a part in a way its dimensions may not.
* Its result is in the plane's own coordinates, flat on ``Plane.XY``;
  multiply by the plane to put it back.
* :func:`~operations_part.project_to_shape` casts a face onto a part and
  gives back the faces it lands on, which lie on the part's surface.
* A projection meets every surface in its path, and ``hit`` chooses which
  to keep.
* Projection stretches a shape wherever the surface slopes away from the
  direction.
* :func:`~operations_part.thicken` turns a face on a curved surface into a
  solid that follows it.

:ref:`projection_plane` and :ref:`projection_shape` cover the two
operations in full, including the other choices of ``hit`` and projecting
edges instead of faces.
