#####
Holes
#####

build123d provides three hole objects. Each uses ``Mode.SUBTRACT`` by default
to cut a hole at every active location.

* :class:`~objects_part.Hole` cuts a cylindrical bore.
* :class:`~objects_part.CounterSinkHole` adds a conical recess for a flat-head screw.
* :class:`~objects_part.CounterBoreHole` adds a flat-bottomed recess for a
  socket-head screw.

.. image:: assets/holes/hole_types.svg
    :align: center
    :alt: Cross section of a plate with a plain hole, a countersink, and a counterbore.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [Hole types]
    :end-before: [Hole types]

Placing holes
-------------

A hole runs from its location's origin along the local negative Z axis. When
you use a planar face as the location, positive Z follows the face normal and
the hole cuts into the part.

.. code-block:: build123d

    with BuildPart() as plate:
        Box(80, 40, 10)
        with Locations(plate.faces().sort_by(Axis.Z)[-1]):
            with GridLocations(60, 20, 2, 2):
                CounterBoreHole(radius=3, counter_bore_radius=5.5, counter_bore_depth=3)

In Builder mode, omit ``depth`` to size a through hole from the existing part.
In Algebra mode, set ``depth`` explicitly and subtract the cutter. Here the top
face is at Z = 0, so a depth of 10 cuts through the block.

.. code-block:: build123d

    block = Box(30, 30, 10, align=(Align.CENTER, Align.CENTER, Align.MAX))
    block -= Pos(5, 5) * Hole(radius=3, depth=10)

Dimensions
----------

The drawings show how each argument sets the dimensions of a blind hole.

Hole
^^^^

.. image:: assets/holes/hole_section.svg
    :align: center
    :width: 60%
    :alt: Plain hole labeled with its diameter and depth.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [Hole]
    :end-before: [Hole]

CounterSinkHole
^^^^^^^^^^^^^^^

``counter_sink_radius`` sets the opening radius. Set ``counter_sink_angle`` to
the screw head's included angle. The default is 82°, common for inch flat-head
screws. Many metric flat-head screws use 90°. ``depth`` starts at the surface
and includes the recess.

.. image:: assets/holes/counter_sink_hole_section.svg
    :align: center
    :width: 60%
    :alt: Countersunk hole with both diameters, the included angle, and the depth from the surface.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [CounterSinkHole]
    :end-before: [CounterSinkHole]

CounterBoreHole
^^^^^^^^^^^^^^^

Measure ``counter_bore_depth`` from the surface to the flat shoulder. Measure
``depth`` from the same surface to the bottom of the bore.

.. image:: assets/holes/counter_bore_hole_section.svg
    :align: center
    :width: 60%
    :alt: Counterbored hole with both diameters and both depths measured from the surface.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [CounterBoreHole]
    :end-before: [CounterBoreHole]

Counterdrill
------------

build123d has no dedicated counterdrill object. To model one, place a
:class:`~objects_part.CounterSinkHole` below the surface where the wider bore
ends. The countersink cone forms the shoulder between the two bore diameters.
Set ``counter_sink_radius`` to the wider bore's radius and ``counter_sink_angle``
to the larger drill's included point angle.

On the left, the cutter starts at the surface and forms a countersink. On the
right, the same cutter starts 10 units below the surface, so the counterdrill's
shoulder begins at that depth.

.. code-block:: build123d

    with BuildPart() as block:
        Box(100, 100, 40, align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations((-20, 0, 0)):
            CounterSinkHole(radius=5, counter_sink_radius=8, counter_sink_angle=118)
        with Locations((20, 0, -10)):
            CounterSinkHole(radius=5, counter_sink_radius=8, counter_sink_angle=118)
        # Expose both profiles in section.
        split(bisect_by=Plane.XZ, keep=Keep.BOTTOM)

For a blind counterdrill, measure ``depth`` from the cutter location to the end
of the narrow bore's full diameter. The wider cylinder extends the same distance
back toward the surface, so set ``depth`` at least as large as the offset.

.. image:: assets/holes/counter_drill_hole_section.svg
    :align: center
    :width: 60%
    :alt: Blind counterdrill with the offset measured to the shoulder and depth measured from there.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [Counter drill]
    :end-before: [Counter drill]

Drill points
------------

Set ``point_angle`` on any of the three hole objects to give a blind hole a
conical bottom. Use an included angle in degrees, strictly between 0° and 180°.
Omit ``point_angle`` for a flat bottom.

Give an explicit ``depth`` from the location to where the cylindrical bore
ends. The tip extends another ``radius / tan(point_angle / 2)`` beyond that
depth. The example uses a common twist-drill angle of 118°.

.. image:: assets/holes/hole_drill_point.svg
    :align: center
    :width: 60%
    :alt: Blind hole with depth to the end of the cylindrical bore and a conical point beyond it.

.. literalinclude:: holes.py
    :language: build123d
    :start-after: [Drill point]
    :end-before: [Drill point]

``docs/reference/holes.py`` generates the drawings on this page.
