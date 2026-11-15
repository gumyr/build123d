.. _joints:

######
Joints
######

:class:`~topology.Joint`'s enable Solid and Compound objects to be arranged
relative to each other in an intuitive manner - with the same degree of motion
that is found with the equivalent physical joints.  :class:`~topology.Joint`'s always work
in pairs - a :class:`~topology.Joint` can only be connected to another :class:`~topology.Joint` as follows:

+---------------------------------------+---------------------------------------------------------------------+--------------------+
| :class:`~topology.Joint`              | attach                                                              | Example            |
+=======================================+=====================================================================+====================+
| :class:`~joints.BallJoint`            |  :class:`~joints.RigidJoint`                                        | Gimbal             |
+---------------------------------------+---------------------------------------------------------------------+--------------------+
| :class:`~joints.CylindricalJoint`     |  :class:`~joints.RigidJoint`                                        | Screw              |
+---------------------------------------+---------------------------------------------------------------------+--------------------+
| :class:`~joints.LinearJoint`          | :class:`~joints.RigidJoint`, :class:`~joints.RevoluteJoint`         | Slider or Pin Slot |
+---------------------------------------+---------------------------------------------------------------------+--------------------+
| :class:`~joints.RevoluteJoint`        | :class:`~joints.RigidJoint`                                         | Hinge              |
+---------------------------------------+---------------------------------------------------------------------+--------------------+
| :class:`~joints.RigidJoint`           | :class:`~joints.RigidJoint`                                         | Fixed              |
+---------------------------------------+---------------------------------------------------------------------+--------------------+

Objects may have many joints bound to them each with an identifying label. All :class:`~topology.Joint`
objects have a ``symbol`` property that can be displayed to help visualize
their position and orientation (the `ocp-vscode <https://github.com/bernhard-42/vscode-ocp-cad-viewer>`_ viewer
has built-in support for displaying joints).

.. note::
    If joints are created within the scope of a :class:`~build_part.BuildPart` builder, the ``to_part``
    parameter need not be specified as the builder will, on exit, automatically transfer the joints created in its
    scope to the part created. The same holds inside a :class:`~build_sheet.BuildSheet` nested in a
    ``BuildPart``: its joints, placed with the sheet, become the part's.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - give a part a joint
      - make it in the part's ``BuildPart``, or pass ``to_part``
    * - put a joint at every hole
      - make it inside ``GridLocations``, or ``locations * joint``
    * - connect two parts
      - ``joint.attach(other_joint)``
    * - fix two parts together
      - ``RigidJoint`` to ``RigidJoint``
    * - hinge one part on another
      - ``RevoluteJoint``, with ``attach(..., angle=)``
    * - slide one part along another
      - ``LinearJoint``, with ``attach(..., position=)``
    * - screw one part into another
      - ``CylindricalJoint``, with ``position`` and ``angle``
    * - swivel one part on another
      - ``BallJoint``, with ``attach(..., angles=)``
    * - keep connected parts together afterwards
      - put them in an :ref:`assembly <assembly>`

The first sections cover making and connecting joints; the later ones take
each kind of joint in turn.

***********************
Give a part a joint
***********************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/joints_examples.py
            :language: build123d
            :start-after: [bind]
            :end-before: [bind]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/joints_examples.py
            :language: build123d
            :start-after: [bind_algebra]
            :end-before: [bind_algebra]

A joint has a label, a part it belongs to, and a location on that part. In
builder mode a joint made inside a ``BuildPart`` belongs to the part being
built. In algebra mode the part is given as ``to_part``, the second
argument.

A joint made with neither is *free*: it has a location of its own and no
part. It can be bound afterwards in two ways. Assigning it into the part's
``joints`` under its label binds it where it stands and leaves the part the
same object:

.. literalinclude:: /how_to/joints_examples.py
    :language: build123d
    :start-after: [bind_free]
    :end-before: [bind_free]

Adding it with ``+`` follows the algebra rules instead: the result is a new
part, sharing the geometry, with a copy of the joint:

.. literalinclude:: /how_to/joints_examples.py
    :language: build123d
    :start-after: [bind_plus]
    :end-before: [bind_plus]

``part.joints`` is a dictionary of the part's joints by label, and labels
are unique within a part. A joint made or assigned under a label the part
already has replaces the earlier one. Deleting an entry frees the joint
again, and a joint can be moved from one part to another by assigning it.
``part.joints |= joints`` binds several at once and keeps the part the same
object, which is the form to use on ``self`` in the ``__init__`` of a
subclass.

*****************************
Put a joint at every hole
*****************************

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/joints_examples.py
            :language: build123d
            :start-after: [bulk]
            :end-before: [bulk]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/joints_examples.py
            :language: build123d
            :start-after: [bulk_algebra]
            :end-before: [bulk_algebra]

A joint is placed like any object. In builder mode a joint made inside a
locations context is made once at each place, alongside the hole it belongs
to. In algebra mode a free joint multiplied by a set of locations gives one
copy for each.

The copies are labelled by adding the index of the place to the label:
``"mount"`` becomes ``mount0``, ``mount1``, ``mount2`` and ``mount3``. To
choose the names, give ``label`` a sequence with one label for each place.
Labels made this way must be new to the part; one it already has raises
``ValueError``.

*********************
Connect two parts
*********************

.. literalinclude:: /how_to/joints_examples.py
    :language: build123d
    :start-after: [attach]
    :end-before: [attach]

:meth:`~topology.Joint.attach` is called on a joint of the part that is to
stay where it is, and given a joint of the part that is to move. The second
part is moved so that the two joints coincide. Here the post lands on the
first hole of the plate.

``attach`` places the part once and does not tie the two together. To keep
them together afterwards, put them into an :ref:`assembly <assembly>`, or
combine them.

Joints with freedom of movement take the position in that freedom as
arguments to ``attach``, within the range the joint was given:

.. literalinclude:: /how_to/joints_examples.py
    :language: build123d
    :start-after: [hinge]
    :end-before: [hinge]

The door is attached at 60 degrees. Attach it again with another ``angle``
and it swings there; an angle outside ``angular_range`` raises
``ValueError``.

****************************
Joints follow their part
****************************

Moving or rotating a part moves its joints with it. The operations that
regenerate the geometry do the same to the joints: ``mirror``, ``scale``,
and ``rotate`` or ``translate`` with ``transform=True``.

Mirroring needs more care, because a joint's frame has a handedness:

* A mirrored joint keeps a right-handed frame. Its origin, axis and
  reference direction are reflected and the remaining direction is
  recomputed, as :meth:`~geometry.Location.mirror` does. Its ranges are
  unchanged.
* A reflection reverses the sense of every rotation. A mirrored hinge at an
  angle therefore points its reference where the mirror image of the
  original hinge at the *negated* angle does. A mirrored slide at a position
  sits at the mirror image of the original at that position.
* Because the frame is rebuilt right-handed and not simply reflected, a part
  connected to a mirrored joint and offset along the joint's recomputed
  axis lands on the opposite side from the reflected original.
* In a builder, ``mirror`` with ``Mode.ADD`` keeps the original geometry
  beside the mirrored copy and leaves the builder's joints as they are.

***********
Rigid Joint
***********

A rigid joint positions two components relative to each another with no freedom of movement. When a
:class:`~joints.RigidJoint` is instantiated it's assigned a ``label``, a part to bind to (``to_part``),
and a ``joint_location`` which defines both the position and orientation of the joint (see
:class:`~geometry.Location`) - as follows:

.. code-block:: build123d

    RigidJoint(label="outlet", to_part=pipe, joint_location=path.location_at(1))

Once a joint is bound to a part this way, the :meth:`~topology.Joint.attach` method can be used to
attach another part to it: ``self`` stays fixed and the other joint's part is moved - as follows:

.. code-block:: build123d

    pipe.joints["outlet"].attach(flange_outlet.joints["pipe"])

The :meth:`~topology.Joint.attach` method only does a one time re-position of a part and does not
bind them in any way; however, putting them into an :ref:`assembly` will maintain their relative locations
as will combining parts with boolean operations or within a :class:`~build_part.BuildPart` context.

As an example of creating parts with joints and connecting them together, consider the following code where
flanges are attached to the ends of a curved pipe:

.. image:: /how_to/assets/joints/rigid_joints_pipe.png

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/rigid_joints_pipe.py
            :language: build123d
            :start-after: [pipe]
            :end-before: [pipe]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/rigid_joints_pipe.py
            :language: build123d
            :start-after: [pipe_algebra]
            :end-before: [pipe_algebra]

The pipe's two joints are made from its path. :meth:`~topology.Mixin1D.location_at`
gives a location at each end of the path, facing along it, and the ``-`` negate
operator reverses the one at the inlet without moving it, so that both joints
face out of the pipe.

The flange has two joints of its own: ``pipe``, at the end of its neck, and
``face``, on its mating face. The last two lines attach each flange by its
``pipe`` joint to an end of the pipe. The second flange is a ``copy.copy`` of
the first, and the copy carries the joints with it.

All of the joints are drawn in the picture, which the viewer does when ``show``
is given ``render_joints=True``.


The class and its arguments are in the reference: :class:`~joints.RigidJoint`.



**************
Revolute Joint
**************

Component rotates around axis like a hinge. The :ref:`joint_tutorial` covers Revolute Joints in detail.

During instantiation of a :class:`~joints.RevoluteJoint` there are three parameters not present with
Rigid Joints: ``axis``, ``angle_reference``, and ``range`` that allow the circular motion to be fully
defined.

When using :meth:`~topology.Joint.attach` with a Revolute Joint, an extra ``angle`` parameter is present
which allows one to change the relative position of joined parts by changing a single value.

The class and its arguments are in the reference: :class:`~joints.RevoluteJoint`.

************
Linear Joint
************

Component moves along a single axis as with a sliding latch shown here:

.. image:: /how_to/assets/joints/joint-latch-slide.png

The code to generate these components follows:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/slide_latch.py
            :language: build123d
            :start-after: [latch]
            :end-before: [latch]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/slide_latch.py
            :language: build123d
            :start-after: [latch_algebra]
            :end-before: [latch_algebra]

.. image:: /how_to/assets/joints/joint-latch.png
    :width: 65 %
.. image:: /how_to/assets/joints/joint-slide.png
    :width: 27.5 %

The slide is built standing upright, in a different orientation from the
direction it moves in. Three lines make and connect the joints:

* The :class:`~joints.LinearJoint` on the latch has an axis and the limits of
  movement along it.
* The :class:`~joints.RigidJoint` on the slide has a single location, turned so
  that the slide lies along the axis and its knob ends up on top.
* ``attach`` is given a ``position``, which must be within the limits.

The slide is moved back and forth by changing ``position``. A value outside the
limits raises ``ValueError``.

The class and its arguments are in the reference: :class:`~joints.LinearJoint`.

*****************
Cylindrical Joint
*****************

A :class:`~joints.CylindricalJoint` allows a component to rotate around and moves along a single axis
like a screw combining the functionality of a :class:`~joints.LinearJoint` and a
:class:`~joints.RevoluteJoint` joint.  The ``attach`` for these joints have both ``position`` and
``angle`` parameters as shown below extracted from the joint tutorial.


.. code-block:: python

    hinge_outer.joints["hole2"].attach(m6_joint, position=5 * MM, angle=30)

The class and its arguments are in the reference: :class:`~joints.CylindricalJoint`.

**********
Ball Joint
**********

A component rotates around all 3 axes using a gimbal system (3 nested rotations). A :class:`~joints.BallJoint`
is found within a rod end as shown here:

.. image:: /how_to/assets/joints/rod_end.png

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/rod_end.py
            :language: build123d
            :start-after: [rod_end]
            :end-before: [rod_end]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/rod_end.py
            :language: build123d
            :start-after: [rod_end_algebra]
            :end-before: [rod_end_algebra]

The ``BallJoint`` is at the centre of the socket. Its ``angular_range`` limits
the tilt about X and about Y to 14 degrees either way, which keeps a pin or
bolt through the ball clear of the rod end, and leaves the spin about Z free.
The ball has a ``RigidJoint`` at its own centre, and ``attach`` sets the three
angles; only the first two matter here, since the ball is the same all the way
round. An angle outside its range raises ``ValueError``.

The class and its arguments are in the reference: :class:`~joints.BallJoint`.

********
See also
********

* :ref:`joint_tutorial` builds a hinged box and connects it with joints
  step by step.
* :ref:`assembly` covers keeping connected parts together.
* :ref:`moving_objects` covers the locations joints are made from.
* :ref:`joints_reference` lists the joint classes and their arguments.
