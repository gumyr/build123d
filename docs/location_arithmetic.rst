.. _location_arithmetics:

Location arithmetic for algebra mode
======================================


Position a shape relative to the XY plane
---------------------------------------------

For the following use the helper function:

.. code-block:: python

    def location_symbol(self, l=1) -> Compound:
        return Compound.make_triad(axes_scale=l).locate(self)


1. **Positioning at a location**

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")

    .. image:: assets/location-example-01.png

2) **Positioning on a plane**

    .. code-block:: python

        plane = Plane.XZ

        face = plane * Rectangle(1, 2)

        show_object(face, name="face")
        show_object(plane_symbol(plane), name="plane")

    .. image:: assets/location-example-07.png

    Note that the ``x``-axis and the ``y``-axis of the plane are on the ``x``-axis and the ``z``-axis of the world coordinate system (red and blue axis)


Relative positioning to a plane
------------------------------------

1. **Position an object on a plane relative to the plane**

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        box = Plane(loc) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
        # box = Plane(face.location) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)
        # box = loc * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")
        show_object(box, name="box")

    .. image:: assets/location-example-02.png

    The ``x``, ``y``, ``z`` components of ``Pos(0.2, 0.4, 0.1)`` are relative to the ``x``-axis, ``y``-axis or
    ``z``-axis of the underlying location ``loc``.

    Note: ``Plane(loc) *``, ``Plane(face.location) *`` and ``loc *`` are equivalent in this example.

2. **Rotate an object on a plane relative to the plane**

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        box = Plane(loc) * Rot(z=80) * Box(0.2, 0.2, 0.2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")
        show_object(box, name="box")

    .. image:: assets/location-example-03.png

    The box is rotated via ``Rot(z=80)`` around the ``z``-axis of the underlying location
    (and not of the z-axis of the world).

    More general:

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        box = loc * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")
        show_object(box, name="box")

    .. image:: assets/location-example-04.png

    The box is rotated via ``Rot(20, 40, 80)`` around all three axes relative to the plane.

3. **Rotate and position an object relative to a location**

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        box = loc *  Rot(20, 40, 80) * Pos(0.2, 0.4, 0.1) * Box(0.2, 0.2, 0.2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")
        show_object(box, name="box")
        show_object(location_symbol(loc *  Rot(20, 40, 80), 0.5), options={"color":(0, 255, 255)}, name="local_location")

    .. image:: assets/location-example-05.png

    The box is positioned via ``Pos(0.2, 0.4, 0.1)`` relative to the location ``loc *  Rot(20, 40, 80)``

4. **Position and rotate an object relative to a location**

    .. code-block:: python

        loc = Location((0.1, 0.2, 0.3), (10, 20, 30))

        face = loc * Rectangle(1,2)

        box = loc * Pos(0.2, 0.4, 0.1) * Rot(20, 40, 80) * Box(0.2, 0.2, 0.2)

        show_object(face, name="face")
        show_object(location_symbol(loc), name="location")
        show_object(box, name="box")
        show_object(location_symbol(loc * Pos(0.2, 0.4, 0.1), 0.5), options={"color":(0, 255, 255)}, name="local_location")

    .. image:: assets/location-example-06.png

    Note: This is the same as `box = loc * Location((0.2, 0.4, 0.1), (20, 40, 80)) * Box(0.2, 0.2, 0.2)`

