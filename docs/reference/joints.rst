.. _joints_reference:

################
Joints Reference
################

The joint classes. :ref:`joints` shows how they are used, and
:class:`~topology.Joint` is the base class they share, with ``attach``.

.. py:module:: joints

.. autoclass:: RigidJoint

..
    :exclude-members: attach

    .. method:: attach(other: BallJoint, *, angles: RotationLike = None)
    .. method:: attach(other: CylindricalJoint, *, position: float = None, angle: float = None)
        :noindex:
    .. method:: attach(other: LinearJoint, *, position: float = None)
        :noindex:
    .. method:: attach(other: RevoluteJoint, *, angle: float = None)
        :noindex:
    .. method:: attach(other: RigidJoint)
        :noindex:

        Attach another joint's part to the ``RigidJoint``.
..

.. autoclass:: RevoluteJoint

..
    :exclude-members: attach

    .. method:: attach(other: RigidJoint, *, angle: float = None)

        Attach a ``RigidJoint``'s part to the ``RevoluteJoint``

.. autoclass:: LinearJoint

..
    :exclude-members: attach

    .. method:: attach(other: RevoluteJoint, *, position: float = None, angle: float = None)
    .. method:: attach(other: RigidJoint, *, position: float = None)
        :noindex:

        Connect the ``LinearJoint`` to either a ``RevoluteJoint`` or ``RigidJoint``

.. autoclass:: CylindricalJoint

..
    :exclude-members: attach

    .. method:: attach(other: RigidJoint, *, position: float = None, angle: float = None)

        Attach a ``RigidJoint``'s part to the ``CylindricalJoint``

.. autoclass:: BallJoint

..
    :exclude-members: attach

    .. method:: attach(other: RigidJoint, *, angles: RotationLike = None)

        Attach a ``RigidJoint``'s part to the ``BallJoint``
