.. _assembly_mates:

#########################
Persistent Assembly Mates
#########################

Build123d joints position two parts when ``connect_to`` is called.  An
:class:`~assembly.Assembly` instead retains its mates and mate relations as
design intent.  Calling :meth:`~assembly.Assembly.solve` recalculates every
active constraint simultaneously, so moving a fixed component, changing a
mate value, or suppressing a feature updates the complete assembly.

Mate connectors use the Onshape coordinate convention: Z is the primary axis
and X is the secondary axis.  :class:`~assembly.MateConnector` derives from
:class:`~joints.RigidJoint`, so existing rigid joints can be used directly as
mate connectors and retain the usual part-local storage and copy behavior.

Quick Start
***********

.. code-block:: python

    from build123d import *

    frame = Box(40, 20, 4)
    frame.label = "frame"
    arm = Pos(0, 0, 20) * Box(4, 4, 30)
    arm.label = "arm"

    frame_axis = MateConnector("frame axis", frame, Location((0, 0, 4)))
    arm_axis = MateConnector("arm axis", arm, arm.location)

    mechanism = Assembly((frame, arm), label="mechanism").ground(frame)
    hinge = mechanism.revolute(
        "hinge",
        frame_axis,
        arm_axis,
        limits={"rz": (-90, 90)},
    )

    hinge.set_value("rz", 35)
    mechanism.solve()

The assembly itself is a :class:`~topology.Compound`, so it can be displayed,
moved, and exported like other build123d shapes.  :func:`~exporters3d.export_step`
exports assemblies with mates as AP242.  Common connector mates, ranges, current
values, links, joints, and rigid groups are standard AP242 kinematics.  Because
AP242 cannot faithfully express every Onshape feature detail (including Ball's
single conical swing limit, Tangent/Width selections, and general mate
relations), the same file also contains a versioned build123d payload preserving
all mate fields and raw Onshape API parameters.  Use
:func:`~importers.import_step_assembly` for a lossless build123d round trip, or
``write_kinematics=False`` to export geometry without kinematics.

Mate Features
*************

Connector-based mates accept ``flip_primary`` to reverse Z and
``reorient_secondary`` to rotate the XY orientation in 90-degree increments.
They may also be created suppressed.  The complete supported motion and option
set is:

.. list-table::
   :header-rows: 1
   :widths: 18 20 20 24

   * - Mate
     - Free motion
     - Limits
     - Offset
   * - :class:`~assembly.FastenedMate`
     - None
     - None
     - X, Y, Z and rotation
   * - :class:`~assembly.RevoluteMate`
     - Rz
     - Rz
     - Z and rotation
   * - :class:`~assembly.SliderMate`
     - Tz
     - Tz
     - X, Y and rotation
   * - :class:`~assembly.PlanarMate`
     - Tx, Ty, Rz
     - Tx, Ty, Rz
     - Z and rotation
   * - :class:`~assembly.CylindricalMate`
     - Tz, Rz
     - Tz, Rz
     - None
   * - :class:`~assembly.PinSlotMate`
     - Tx, Rz
     - Tx, Rz
     - Z and rotation
   * - :class:`~assembly.BallMate`
     - Rx, Ry, Rz
     - Conical swing
     - None
   * - :class:`~assembly.ParallelMate`
     - Tx, Ty, Tz, Rz
     - Tx, Ty, Tz, Rz
     - None
   * - :class:`~assembly.TangentMate`
     - Determined by selected geometry
     - None
     - None
   * - :class:`~assembly.WidthMate`
     - Translation and rotation in the center plane
     - None
     - None
   * - :class:`~assembly.GroupMate`
     - Six for the group as a whole
     - None
     - Captured component origins

Tx, Ty, and Tz are translations in the first mate connector's frame.  Rx, Ry,
and Rz are rotations in degrees.  All mate types except Ball, Fastened,
Tangent, Width, and Group expose their free coordinates through
:meth:`~assembly.Mate.set_value`. Commanded angles retain their full turn count
for Gear, Rack and Pinion, and Screw relations even though the resulting rigid
transform is periodic.

Offsets, Limits, and Suppression
================================

:class:`~assembly.MateOffset` stores a fixed translation and Euler-angle
rotation.  Each mate validates that only its supported translation directions
are used.  :class:`~assembly.MateLimit` stores inclusive minimum and maximum
values.  Limits apply only to a mate's free coordinates:

.. code-block:: python

    slide = SliderMate(
        "piston",
        cylinder_connector,
        piston_connector,
        offset=MateOffset((2, -1, 0), (0, 0, 5)),
        limits={"tz": MateLimit(0, 80)},
    )
    assembly.add_mate(slide)
    slide.set_value("tz", 25)

    slide.suppress()
    assembly.solve()
    slide.suppress(False)
    assembly.solve()

For Ball mates, use ``limits={"swing": (0, maximum_angle)}``; the swing angle
is measured between the two connector Z axes.

Tangent
========

:class:`~assembly.TangentMate` accepts a component and selected face, edge, or
vertex on each side.  Analytic and swept faces are supported; offset and
generic Bezier/B-spline faces are rejected.  Adjacent tangent-continuous faces
or edges are included by default, or this can be disabled with
``propagate=False``. Propagation has no effect on vertices. ``flip_primary``
selects the opposite face-to-face normal relationship and is ignored for other
selection pairs.

.. code-block:: python

    tangent = TangentMate(
        "cam contact",
        cam,
        cam.faces()[0],
        follower,
        follower.faces()[0],
        propagate=True,
    )
    assembly.add_mate(tangent)

Width
=====

:class:`~assembly.WidthMate` accepts one or two tab connectors and exactly two
width connectors.  A one-tab mate centers that connector on the width center
plane.  A two-tab mate keeps the tabs mirror-symmetric about the plane.  Tab
and width connectors cannot belong to the same component, while either side
may use two connectors from one component.

Group
=====

:class:`~assembly.GroupMate` captures the current relative component origins
without depending on geometry.  The selected components subsequently move as
a rigid cluster.  The group itself remains free until a member is fixed or
constrained by another mate.

Mate Relations
**************

Relations couple coordinates already exposed by mates.  Their initial phase is
captured on the first solve, preserving the current assembly position.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Relation
     - Coupled motion
     - Parameter
   * - :class:`~assembly.GearRelation`
     - Two revolute Rz coordinates
     - Ratio and reverse direction
   * - :class:`~assembly.RackAndPinionRelation`
     - Revolute Rz and linear coordinate
     - Travel per revolution and reverse direction
   * - :class:`~assembly.ScrewRelation`
     - Tz and Rz of one cylindrical mate
     - Travel per revolution and reverse direction
   * - :class:`~assembly.LinearRelation`
     - Two translational mate coordinates
     - Ratio and reverse direction

Solving and Diagnostics
***********************

Use :meth:`~assembly.Assembly.ground` to ground one or more direct components.
If none is fixed, the solver temporarily grounds the first component to remove
the six global rigid-body degrees of freedom.  The solve result reports cost,
maximum normalized residual, iteration count, and remaining physical degrees
of freedom.  Inconsistent or nonconvergent constraints raise
:class:`~assembly.MateSolveError` by default; pass ``strict=False`` to inspect
the unsuccessful result without raising.

Mates and relations survive ordinary Python deep copies.  The copied assembly
has independent mate values, relations, grounding, and geometry.

API
***

.. py:module:: assembly

.. autoclass:: Assembly
   :members:
.. autoclass:: MateConnector
.. autoclass:: Mate
   :members:
.. autoclass:: MateLimit
.. autoclass:: MateOffset
.. autoclass:: FastenedMate
.. autoclass:: RevoluteMate
.. autoclass:: SliderMate
.. autoclass:: PlanarMate
.. autoclass:: CylindricalMate
.. autoclass:: PinSlotMate
.. autoclass:: BallMate
.. autoclass:: ParallelMate
.. autoclass:: TangentMate
.. autoclass:: WidthMate
.. autoclass:: GroupMate
.. autoclass:: GearRelation
.. autoclass:: RackAndPinionRelation
.. autoclass:: ScrewRelation
.. autoclass:: LinearRelation
.. autoclass:: MateSolveResult
.. autoclass:: MateSolveError
