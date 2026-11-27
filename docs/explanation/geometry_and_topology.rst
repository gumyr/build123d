.. _geometry_and_topology:

#####################
Geometry and topology
#####################

build123d keeps two kinds of thing apart, and a design uses both from its
first lines. A :class:`~geometry.Plane` and an :class:`~geometry.Axis` have
no size: a plane has no outline and an axis has no ends. A ``Face`` and an
``Edge`` do: a face has an area and an edge has a length. The first kind
lives in the ``geometry`` module and the second in ``topology``, and the split
is not a matter of filing. It is the idea a boundary representation (BREP)
kernel is built on, and following it down explains several things that
otherwise look like quirks: why a cylinder has an edge running up its side,
why a sphere has edges that cannot be seen, and how a shape drawn flat can be
put onto a curved face exactly.

***********************
Limitless and limited
***********************

*Geometry* is a description that goes on forever. A plane is a position and
two directions; a line is a position and one direction. Neither says where
to stop.

*Topology* says where to stop. A straight ``Edge`` is the stretch of a line
between two vertices. A flat ``Face`` is the part of a plane inside an
outline. Each is a piece of something limitless, and the limitless thing can
be had back from it:

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [limits]
    :end-before: [limits]

.. image:: /explanation/assets/geometry_and_topology/limits.svg
    :align: center
    :alt: A rectangular face on a plane that continues past it, and a cylindrical face on a cylinder that continues past both its ends.

The kernel carries the same idea through to every curve and surface, not
only the straight and the flat. The wall of a ``Cylinder`` is a piece of a
cylinder that runs without end in both directions along its axis; the skin
of a ``Sphere`` is a piece of a sphere; a face made by
:ref:`surface modelling <surface_modeling>` is a piece of a spline surface.
In each case the *surface* is geometry and the *face* is topology: the
surface, and the limits drawn on it.

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [surface]
    :end-before: [surface]

``Plane`` and ``Axis`` are the limitless things build123d gives a name of
their own, because a design refers to them all the time: to sketch on, to
revolve about, to measure from. It has no such object for an endless
cylinder or a whole sphere. Those exist only inside the kernel, underneath a
face, and are reached through the face. The ``geometry`` module also holds
things that are neither, such as ``Vector``, ``Location`` and ``Color``; the
pairing here is between ``Plane`` and ``Axis`` and the faces and edges cut
from them.

:ref:`topology` describes the limited side in full: the vertices, edges,
wires, faces, shells and solids a shape is made of. The rest of this page is
about where the two sides meet.

****************************
A face has a flat picture
****************************

A surface is a rule that turns two numbers into a point in space. The
numbers are called *u* and *v*, the surface's parameters. On a cylinder *u*
is the angle round the axis and *v* is the distance along it, so the endless
cylinder is, to the kernel, a flat strip: every point of it is a (*u*, *v*)
pair.

The limits of a face are drawn on that strip. Each edge of a face is held
twice: as a curve in space, which is what is seen, and as a curve in
(*u*, *v*), which is what says which part of the surface the face keeps.
The second set of curves is a flat drawing of the face, and build123d will
show it:

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [two_views]
    :end-before: [two_views]

.. image:: /explanation/assets/geometry_and_topology/cylinder_uv.svg
    :align: center
    :alt: The wall of a cylinder with a line up its side, beside a rectangle whose two upright sides are that same line.

The wall of the cylinder is a rectangle in (*u*, *v*): 2π wide, since *u* is
an angle in radians, and 10 tall. That rectangle is why the wall has the
edges it has.

*********
The seam
*********

A rectangle has four sides, and the wall of a cylinder has two circles, which
account for the top and the bottom. The other two sides are *u* = 0 and
*u* = 2π, and on the cylinder those are the same line. So the face is given
one more edge, running up its side, and uses it twice: once as the left side
of the rectangle and once as the right. That edge is the *seam*.

The seam is bookkeeping. Nothing about the part changes there, and the
surface is as smooth across it as anywhere else. It exists because a surface
that closes on itself has to be cut somewhere to lie flat, just as the label
of a tin has to be cut to come off. Where the cut falls is a property of how
the surface was made, and it shows up in the ways an extra edge would:
``wall.edges()`` has three entries, a selector may return it, and a shape
drawn across it has to be treated as crossing from one side of the flat
picture to the other. :attr:`~topology.Face.seams` picks it out.

*****************
Degenerate edges
*****************

A sphere goes one step further. Its parameters are longitude and latitude,
and its flat picture is again a rectangle, 2π wide and π tall. The left and
right sides are a seam, as on the cylinder: half a circle from pole to pole.
The top and bottom sides are the trouble. All along the top side the
latitude is 90°, and on the sphere every such point is the same point, the
north pole.

.. image:: /explanation/assets/geometry_and_topology/sphere_uv.svg
    :align: center
    :alt: A sphere with a half circle from pole to pole, beside a rectangle whose upright sides are that half circle and whose top and bottom sides are the two poles.

The flat picture still needs those two sides, or its outline would not
close. So the kernel gives the face an edge for each: an edge with a proper
length in (*u*, *v*) and no length at all in space. These are *degenerate*
edges. A sphere has two, one at each pole, and a cone has one, at its apex.

build123d leaves degenerate edges out of what it reports, since there is
nothing to select or measure:

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [sphere]
    :end-before: [sphere]

They are still there underneath, and now and then they matter. An operation
that follows the boundary of a face edge by edge can be stopped by an edge
with no length. ``sweep``, for one, refuses a profile taken from a sphere or
a cone face for that reason, and says so, rather than hand the kernel a
boundary it cannot follow.

***********************
Writing in the flat
***********************

If the limits of a face are a flat drawing, then adding to the drawing adds
to the face. A circle drawn into the (*u*, *v*) picture of a cylinder, and
handed to the kernel as a curve on that surface, is a curve lying on the
cylinder: not projected onto it, and not fitted to it afterwards, but there
by construction.

The (*u*, *v*) picture itself is awkward to draw in. Its units are whatever
the surface uses, an angle one way and a length the other on a cylinder, so
a round hole is not round there. :class:`~topology.UVFrame` supplies the
missing step. It lays an ordinary flat coordinate system onto a face, in the
units of the model, with its origin and x direction wherever they are
wanted, and writes shapes drawn on ``Plane.XY`` through it into the face's
parameters. :meth:`~topology.Face.uv_frame` makes one:

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [write]
    :end-before: [write]

.. image:: /explanation/assets/geometry_and_topology/written.svg
    :align: center
    :alt: A circle drawn flat, the same circle as a hole in the wall of a cylinder, and the hole's outline in the cylinder's parameters, where it is taller than it is wide.

:meth:`~topology.UVFrame.write_face` gives the drawn shape as a face on the
surface, and :meth:`~topology.UVFrame.punch` gives the surface's face with
the shape cut out of it. The frame also takes care of the seam: a shape that
lies across it is written as one face.

*****************************
How flat is flat
*****************************

What a flat drawing means on a curved face depends on the face.

A cylinder and a cone can be unrolled onto a table without stretching, and a
plane is flat already. On these the frame is exact: a length drawn flat is
the same length on the face, and an area is the same area. The disc above
has the area and the circumference of the circle it was drawn as.

A sphere cannot be flattened without stretching, which is why every map of
the world distorts something, and neither can a surface that curves two ways
at once. On these a frame has to choose what to keep. The frame build123d
makes for a sphere keeps distances and directions from its origin, so a
shape is true at the origin and stretched more the farther it reaches:

.. literalinclude:: /explanation/geometry_and_topology.py
    :language: build123d
    :start-after: [stretch]
    :end-before: [stretch]

The cap is still a circle on the sphere, two units from its centre measured
along the surface. Its rim is shorter than the flat circle's because a
sphere has less room that far out than a plane does. For any other surface
the frame follows the shortest paths leaving its origin, with the same
character. A different choice of map can be given to ``UVFrame`` directly
when another property is the one to keep.

***********************
Sheet metal
***********************

Sheet metal is where being exact pays. A part is cut and drilled as a flat
blank and folded afterwards, so a hole near a fold is a circle in the blank
and something else in the finished part: where it runs onto the bend it is
wrapped round the bend's cylinder. The folded part has to carry exactly the
shape that flattens back to a circle, or the pattern sent to be cut will not
be the part that was designed.

A bend is a cylinder, and a cylinder unrolls exactly. So
:func:`~operations_sheet.bend` takes the strip of the blank that the bend
uses up, holes and all, and writes it through the unrolled frame of the
bend's cylinder. The hole is drawn once, flat, as it will be drilled:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /explanation/geometry_and_topology.py
            :language: build123d
            :start-after: [sheet]
            :end-before: [sheet]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /explanation/geometry_and_topology.py
            :language: build123d
            :start-after: [sheet_algebra]
            :end-before: [sheet_algebra]

.. image:: /explanation/assets/geometry_and_topology/sheet_hole.svg
    :align: center
    :alt: A bracket folded at a right angle with a hole running from the bend into the upright wall, and its flat pattern, in which the hole is a circle.

In the folded part the hole's edge on the bend is a curve in space that lies
in no plane, so it is not a circle seen from any direction. Unfolded, every edge of the hole lies on the circle that
was drilled.

*************************
Where this shows up
*************************

* :meth:`~topology.Face.wrap_faces` writes text or a sketch along a path on
  a face through a ``UVFrame``; :ref:`projection_faces` has the steps.
* A sheet metal :ref:`bend <sheet_metal_bend>` writes the blank onto its
  cylinder, and :ref:`unfold <sheet_metal_unfold>` reads it back; see
  :ref:`sheet_metal`.
* A seam is an edge of its face, so it appears in ``edges()`` and can be the
  edge a selector returns on a cylinder, a cone, a sphere or a torus.
* Degenerate edges are left out of ``edges()``, and a profile that has one is
  refused by ``sweep``.
