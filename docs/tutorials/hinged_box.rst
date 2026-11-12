.. _joint_tutorial:
.. _tutorial_hinged_box:

############
A hinged box
############

Every part so far has been made where it was wanted. An assembly is
different: its parts are made separately, each wherever is convenient, and
then have to be brought together. Working out by hand where each one goes,
and at what angle, is tedious and easy to get wrong.

A *joint* does that work. It is a marked point on a part that says *another
part connects here*, and in what way: fixed, turning, or sliding. Connect a
joint on one part to a joint on another and the second part moves into
place. In this tutorial you will put joints on a box, a lid, a hinge, its
pin and its screws, and connect them into this:

.. image:: /tutorials/assets/hinged_box/hinged_open.svg
    :align: center
    :width: 60%

Along the way you will:

* put joints on a part as it is built, beside the features they belong to,
* use three kinds of joint: rigid, revolute and cylindrical,
* give a joint to a part imported from a file,
* connect joints with ``attach``, and set a joint's angle,
* gather the parts into an assembly and check that none of them overlap.

It takes about thirty minutes. It uses the custom object of
:ref:`tutorial_parametric_part`, and how the builder and algebra tabs on
this page work is described in :ref:`tutorial_sketch_then_extrude`.

*****************
Step 1: Setup
*****************

Start a new Python file with the imports and the dimensions, in
millimetres.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The first two lines of dimensions describe the hinge and the rest describe
the box. ``copy`` is part of Python and is used in step 9, to make six
screws out of one.

*************************
Step 2: A hinge leaf
*************************

A hinge is two *leaves* that turn about a pin. The leaves are nearly the
same - a flat plate with screw holes, and one edge rolled into a tube for
the pin - and differ only in where the tube is cut away so that the two
can mesh. One custom object can therefore make both.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [leaf]
    :end-before: [leaf]

.. image:: /tutorials/assets/hinged_box/hinged_leaves.svg
    :align: center
    :width: 60%

The leaf is made the way a real one is: cut from sheet metal and rolled.
That uses build123d's sheet metal tools, which are a subject of their own
and are described in :ref:`sheet_metal`; this is all you need to know of
them here:

* ``BuildSheet`` builds a part from a flat sheet of a given ``thickness``.
* The sketch inside it is the flat blank: a rectangle with notches cut out
  of one edge. ``outer`` chooses between two notches and three, which is
  the whole difference between the two leaves.
* ``hem`` with ``HemType.ROLLED`` rolls what is left of that edge into a
  tube that fits the pin.
* ``thicken`` turns the sheet into a solid.

The screw holes are ordinary: a ``GridLocations`` on the top of the leaf,
with a ``CounterSinkHole`` at each place.

Notice that both leaves are made the same way round, with the rolled edge
at X = 0. In the picture the second one has been turned to face the first
by hand. From here on, joints will do that. The pin is a part of its own
and comes in step 6.

************************************
Step 3: Put joints on the leaf
************************************

A leaf connects to several things: the part it is screwed to, the other
leaf, its screws, and - for one of them - the pin. Each connection gets a joint, and the joint is
made inside the ``BuildPart``, which is all it takes for it to belong to
the part. Replace the class with this one, which has the joints added:

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [leaf_joints]
    :end-before: [leaf_joints]

.. code-block:: text

    ['hole0', 'hole1', 'hole2', 'mount', 'hinge', 'pin']

.. image:: /tutorials/assets/hinged_box/hinged_leaf_joints.svg
    :align: center
    :width: 55%

Every joint has a label, and a part keeps its joints in ``joints``, a
dictionary, under those labels. The picture shows the symbol of each one in
red. Taking them in the order they appear in the code:

**The screws.** A :class:`~joints.CylindricalJoint` lets a part turn about
an axis and slide along it, which is what a screw does in its hole. It is
created on the line after the ``CounterSinkHole``, inside the same
``GridLocations``, so one is made at each of the three holes and they are
labelled ``hole0``, ``hole1`` and ``hole2``. A joint made this way cannot
drift away from its hole: move the holes and the joints move too. Its axis
is the Z axis of its location, which points up out of the hole, and
``linear_range`` says how far along that axis a screw may sit.

**The mounting face.** A :class:`~joints.RigidJoint` allows no movement at
all: it marks a position and a direction, and whatever is attached to it is
held there. ``mount`` is on the underside of the leaf, under the middle
screw hole.

**The hinge.** One leaf turns about the other, and that is a
:class:`~joints.RevoluteJoint`: an axis to turn about and a range of angles
it may turn through. Only one of a pair of joints needs to describe the
movement, so the outer leaf has the ``RevoluteJoint`` and the inner leaf
has a plain ``RigidJoint`` in the same place.

The axis does not have to be worked out. Each tube rolled by ``hem`` is a
bend, and a bend knows its own axis, ``axis_of_rotation``. The leaf has
two or three bends, all on the same line, so any of them gives the right
axis; what differs is the point each axis starts from, which is the end of
its own tube. The two joints have to meet at one point, and the end of the
first tube on the outer leaf is where the last tube on the inner leaf
ends. So the bends are sorted along Y, and the outer leaf takes the first
and the inner leaf the last.

The two leaves were made the same way round, but in a hinge they face each
other, so the axis of one has to run the opposite way to the axis of the
other. That is the ``reverse()``.

**The pin.** The pin is pushed in from one end of the hinge, and the outer
leaf, whose tubes are at both ends, is the one that holds it. Its ``pin``
joint is a ``RigidJoint`` taken from a bend as well: the last one this
time, whose axis starts at the very end of the leaf and runs back along
the tubes. That is where the pin goes in and the way it points.

The ``angular_range`` of 90 to 360 degrees is the angle between the leaves:
180 is the hinge lying flat. Below 90 the tubes of one leaf would run into
the plate of the other.

*********************
Step 4: The box
*********************

The box is a rectangle extruded and then hollowed, as in
:ref:`tutorial_beyond_extrude`. It needs one joint, where the hinge goes,
and three holes for the screws.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [box_builder]
            :end-before: [box_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [box_algebra]
            :end-before: [box_algebra]

.. image:: /tutorials/assets/hinged_box/hinged_box.svg
    :align: center
    :width: 55%

A ``RigidJoint`` is a location: a position and three directions. The
directions matter as much as the position, because connecting two rigid
joints lines them up exactly - X with X, Y with Y, Z with Z. So the joint
on the box has to be placed where the leaf's ``mount`` joint should end up,
*and turned the way that joint should end up turned*.

``hinge_plane`` is that location, and nothing in it is a typed-in
coordinate:

* Its origin is found from the box: ``back`` is the face with the lowest X,
  ``rim`` is the top edge of that face, and ``rim @ 0.5`` is the middle of
  that edge. From there it is moved in Z by the distance from the pin to
  the screws, less the height of the pin above the rim. Both are read from
  the leaf, in ``box_leaf.screw_inset`` and ``box_leaf.barrel_radius``.
* ``z_dir=(-1, 0, 0)`` points out of the back of the box. The Z of the
  leaf's ``mount`` joint points up through the leaf, so the leaf will lie
  flat against the box with its top outwards.
* ``x_dir=(0, 0, -1)`` points down. The X of the leaf runs away from its
  rolled edge, so the roll will be at the top.

The joint and the holes are then made at that one location. In builder
mode both are inside ``Locations(hinge_plane)``; in algebra mode a joint is
placed with ``*`` and added with ``+``, exactly as a shape is. Either way
the box now has a joint, ``box.joints["hinge"]``, drawn in red above.

********************
Step 5: The lid
********************

The lid is a slab with the same joint and the same holes, on its top face.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [lid_builder]
            :end-before: [lid_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [lid_algebra]
            :end-before: [lid_algebra]

.. image:: /tutorials/assets/hinged_box/hinged_lid.svg
    :align: center
    :width: 55%

Here the Z of the joint points up out of the lid and its X points away
from the back edge, towards the front, so that the roll of the second leaf
will hang just over the back.

Look at where the lid is: flat on ``Plane.XY``, in the same place as the
bottom of the box. It was made where it was easiest to make. Nothing in
its code says where it belongs, and nothing needs to.

***********************************
Step 6: The pin and a screw
***********************************

The pin can be pulled out of a real hinge, so it is not part of either
leaf. It is a part of its own: a round shank the length of the leaf, with
a wider head at one end.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [pin_builder]
            :end-before: [pin_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/hinged_box.py
            :language: build123d
            :start-after: [pin_algebra]
            :end-before: [pin_algebra]

.. image:: /tutorials/assets/hinged_box/hinged_pin.svg
    :align: center
    :width: 55%

The shank is a circle extruded upwards and the head is a larger circle
extruded downwards, by a negative amount, so the two meet at the origin.
That is where the ``head`` joint is: a ``RigidJoint`` with no location
given sits at the origin, with its Z along the shank. (The picture shows
the pin lying on its side.) The radius of the
head is read from the leaf, to match its tubes.

The last part is a screw, and it is not made here at all. A joint does not
have to be made in a builder. Any solid can be given one, including a part
that was drawn somewhere else and imported. Download the screw
:download:`M6-1x12-countersunk-screw.step </tutorials/M6-1x12-countersunk-screw.step>`
into the folder of your file.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [screw]
    :end-before: [screw]

.. image:: /tutorials/assets/hinged_box/hinged_screw.svg
    :align: center
    :width: 30%

Outside a builder, a joint is told which part it belongs to: the second
argument, ``screw``. The location is the origin, which in this file is the
middle of the top of the screw's head, with Z pointing up out of it.

************************************
Step 7: Connect the joints
************************************

Every part now carries its joints, and the parts are all in the wrong
places. Four lines put them right. This step, and the rest of the
tutorial, is the same in both modes.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [connect_box]
    :end-before: [connect_box]

.. image:: /tutorials/assets/hinged_box/hinged_connect_box.svg
    :align: center
    :width: 55%

``attach`` reads as *this joint, stay where you are; that joint, come
here*. The part that owns the first joint does not move. The part that
owns the joint in the brackets moves so that the two joints meet. Here the
box stays and the leaf comes to it.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [connect_leaves]
    :end-before: [connect_leaves]

.. image:: /tutorials/assets/hinged_box/hinged_connect_leaves.svg
    :align: center
    :width: 55%

The outer leaf, now fixed to the box, stays, and the inner leaf comes to
it. Because ``hinge`` on the outer leaf is a ``RevoluteJoint``, ``attach``
takes an ``angle``: 90 degrees between the leaves, which is the hinge of a
closed box.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [connect_lid]
    :end-before: [connect_lid]

.. image:: /tutorials/assets/hinged_box/hinged_connect_lid.svg
    :align: center
    :width: 55%

Last, the inner leaf stays and the lid comes to it. The lid has travelled
from the floor of the box to the top of it, and no line of the file says
how far that is.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [connect_pin]
    :end-before: [connect_pin]

.. image:: /tutorials/assets/hinged_box/hinged_connect_pin.svg
    :align: center
    :width: 55%

The pin goes to the ``pin`` joint of the outer leaf, which puts it through
the tubes of both leaves with its head against the end of the hinge.

The order matters. Each ``attach`` moves one part to a part that is already
in its final place, so work outwards from the part that stays still: the
box, then the leaf on it, then the other leaf, then the lid. The pin
hangs from the first leaf, so it could have gone in any time after that.

*************************
Step 8: An assembly
*************************

The five parts are in the right places but are still five separate
variables. An assembly gathers them into one object.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [assembly]
    :end-before: [assembly]

.. code-block:: text

    Do any of the parts overlap? False

A ``Compound`` given ``children`` is an assembly: each child keeps its own
shape, its place and its ``label``. The leaves were given labels by their
class and the pin in step 6, and the box and the lid get theirs here. :ref:`assembly` has more
about assemblies.

``do_children_intersect`` checks every part of an assembly against every
other and reports whether any two occupy the same space. Joints make
mistakes of this kind easy to find, and easy to make: a joint that is 2 mm
out puts a part 2 mm inside its neighbour, which is hard to see in a
viewer.

***********************
Step 9: The screws
***********************

There is one screw and there are six holes. Each hole needs a copy.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [screws]
    :end-before: [screws]

.. code-block:: text

    hinged box           Compound at 0x121233980, Location((0, 0, 0), (0, 0, 0))
    ├── box              Part     at 0x1212333e0, Location((0, 0, 0), (0, 0, 0))
    ├── outer leaf       HingeLeafat 0x120c70740, Location((-150, 0, 114.5), (0, -90, 180))
    ├── inner leaf       HingeLeafat 0x120cfdb80, Location((-154.5, 0, 110), (0, 0, 0))
    ├── lid              Part     at 0x120cb8650, Location((0, 0, 100), (0, 0, 0))
    ├── pin              Part     at 0x121271dc0, Location((-154.5, -60, 114.5), (-90, 0, 0))
    ├── outer leaf screw Solid    at 0x120cb82f0, Location((-152, 40, 84.5), (0, -90, 180))
    ├── outer leaf screw Solid    at 0x121233770, Location((-152, 0, 84.5), (0, -90, 180))
    ├── outer leaf screw Solid    at 0x120cfda90, Location((-152, -40, 84.5), (0, -90, 180))
    ├── inner leaf screw Solid    at 0x120cfd700, Location((-124.5, -40, 112), (0, 0, 0))
    ├── inner leaf screw Solid    at 0x120cfe270, Location((-124.5, 0, 112), (0, 0, 0))
    └── inner leaf screw Solid    at 0x120cfcfb0, Location((-124.5, 40, 112), (0, 0, 0))

.. image:: /tutorials/assets/hinged_box/hinged_finished.svg
    :align: center
    :width: 60%

* ``copy.copy(screw)`` makes another screw that shares the shape of the
  first, so six screws take little more memory than one. The copy has its
  own place and its own copy of the ``head`` joint.
* The leaf's ``hole`` joints are ``CylindricalJoint``\ s, so ``attach``
  takes a ``position`` along the axis and an ``angle`` about it. A position
  of 0 puts the head level with the top of the leaf. Try a ``position`` of
  5 to see the screws partly undone.
* Setting ``parent`` adds a part to an assembly that already exists.
* ``show_topology`` prints the assembly as a tree. The leaves were moved
  after the holes were made in them, and the joints of the holes moved
  with them: a joint always follows its part.

The overlap check was made before the screws went in, because a screw is
meant to bite into the sides of its hole and would be reported.

***************************
Step 10: Open the lid
***************************

The box is closed because of one number, the ``angle`` in step 7. A
different angle opens it.

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [open]
    :end-before: [open]

.. image:: /tutorials/assets/hinged_box/hinged_open.svg
    :align: center
    :width: 60%

An ``attach`` moves the one part it is given and nothing else. Moving the
inner leaf to its new angle leaves the lid and its screws behind, so they
are attached again, in the same order as before. Each line is the one that
was used the first time; only the angle has changed.

A ``RevoluteJoint`` refuses an angle outside its range:

.. literalinclude:: /tutorials/hinged_box.py
    :language: build123d
    :start-after: [limit]
    :end-before: [limit]

.. code-block:: text

    angle (45) must in range of (90, 360)

.. note::

    To see the joints in your viewer, show their symbols, as in
    ``show(box, box.joints["hinge"].symbol)``. The ocp_vscode viewer can
    also draw every joint of a part: ``show(box, render_joints=True)``.

********************
What you learned
********************

* A **joint** marks where, and how, a part connects to another. A part
  keeps its joints in ``joints``, under their labels, and they move when
  it moves.
* A joint made inside a ``BuildPart`` belongs to the part being built. Made
  inside a ``GridLocations`` with a hole, there is one at every hole, with
  a number added to its label.
* A :class:`~joints.RigidJoint` fixes a part in place and direction; a
  :class:`~joints.RevoluteJoint` lets it turn about an axis; a
  :class:`~joints.CylindricalJoint` lets it turn and slide.
* Place a joint from the part's own faces and edges, and turn it the way
  the other part should end up turned.
* ``first.attach(second)`` leaves the first part where it is and brings the
  second to it. Work outwards from the part that stays still.
* A ``Compound`` with ``children`` is an assembly, and
  ``do_children_intersect`` checks that its parts do not overlap.

:ref:`joints` describes every kind of joint, including the two not used
here, :class:`~joints.LinearJoint` and :class:`~joints.BallJoint`.
