.. _coming_from_openscad:

####################
Coming from OpenSCAD
####################

If you write models in OpenSCAD, much of build123d will be familiar, and a
few things will change how you design. This page sets out which is which.

********************
What is the same
********************

A model is a program, in which dimensions are variables, repetition is a loop,
and a part that is wanted twice is a function. All of that carries over
unchanged, with the whole of Python behind it.

Constructive solid geometry carries over too. build123d has the primitive
solids, and they are added, subtracted and intersected:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /explanation/openscad.py
            :language: build123d
            :start-after: [csg]
            :end-before: [csg]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /explanation/openscad.py
            :language: build123d
            :start-after: [csg_algebra]
            :end-before: [csg_algebra]

An OpenSCAD model can be translated more or less line for line this way,
and for some parts it is the right way to build them.
:ref:`tutorial_combining_solids` shows when.

*********************
What is different
*********************

Three things are different, and each one is something to use, not just to get
used to.

**The geometry is exact.** OpenSCAD works with meshes: a cylinder is a
prism with ``$fn`` sides. build123d works with the surfaces themselves, so
a cylinder is a cylinder, at any size and from any distance, and there is no
``$fn`` to tune. Triangles appear only when a model is exported to a mesh
format such as STL, and their fineness is set there.

**A part usually starts as a sketch.** The common way to make a solid in
build123d is to draw its outline in 2D and then extrude, revolve, loft or
sweep it. This is how most CAD systems work, and for good reason: a flat
outline is easier to get right than the same shape carved out of blocks, and
it leaves fewer operations to be done on solids, which are the slower and more
delicate ones.

**The model can be asked about itself.** A build123d part knows its own
faces, edges and vertices, and they can be selected: the top face, the
vertical edges, the inside corners. A feature such as a fillet is then
applied to the edges it belongs on. In OpenSCAD there is nothing to
select, so a rounded corner has to be assembled from extra solids.

**************************
An example: angle iron
**************************

A length of angle iron with a rounded inside corner shows all three.

.. image:: /explanation/assets/openscad/AngleIron.png

In OpenSCAD the part is a block with material taken away. What is taken
away is two smaller blocks and a cylinder, placed so that the material left
between them in the corner is rounded:

.. code-block:: openscad

    $fn = 100; // Increase the resolution for smooth fillets

    // Dimensions
    length = 100;  // 10 cm long
    width = 30;    // 3 cm wide
    thickness = 4; // 4 mm thick
    fillet = 5;    // 5 mm fillet radius
    delta = 0.001; // a small number

    // Create the angle iron
    difference() {
        // Outer shape
        cube([width, length, width], center = false);
        // Inner shape
        union() {
            translate([thickness+fillet,-delta,thickness+fillet])
                rotate([-90,0,0])
                    cylinder(length+2*delta, fillet,fillet);
            translate([thickness,-delta,thickness+fillet])
                cube([width-thickness,length+2*delta,width-fillet],center=false);
            translate([thickness+fillet,-delta,thickness])
                cube([width-fillet,length+2*delta,width-thickness],center=false);
            
        }
    }

Here it is in build123d:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /explanation/openscad.py
            :language: build123d
            :start-after: [angle_iron]
            :end-before: [angle_iron]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /explanation/openscad.py
            :language: build123d
            :start-after: [angle_iron_algebra]
            :end-before: [angle_iron_algebra]

* The L-shaped profile is two rectangles in a sketch, and ``extrude``
  makes it 10 cm long.
* ``filter_by(Convexity.CONCAVE)`` selects the one edge where the part
  turns inward, the inside corner, and ``fillet`` rounds it. The fillet
  is a true cylindrical surface.
* There is no ``delta``, because it is only OpenSCAD that needs the cutting
  shapes to poke a little way out of the block to cut cleanly; an exact
  modeller does not.
* To change the radius, change one number. To round the outside corner as
  well, select it too.

**************************
Finding the equivalent
**************************

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - OpenSCAD
      - build123d
    * - ``cube``, ``cylinder``, ``sphere``
      - :class:`~objects_part.Box`, :class:`~objects_part.Cylinder`,
        :class:`~objects_part.Sphere`. They are centred on the origin
        unless given ``align``.
    * - ``square``, ``circle``, ``polygon``, ``text``
      - :class:`~objects_sketch.Rectangle`, :class:`~objects_sketch.Circle`,
        :class:`~objects_sketch.Polygon`, :class:`~objects_sketch.Text`
    * - ``union()``, ``difference()``, ``intersection()``
      - ``+``, ``-``, ``&``, or ``mode=`` in a builder
    * - ``translate``, ``rotate``
      - ``Pos(x, y, z) *``, ``Rot(x, y, z) *``, or ``Locations`` in a
        builder
    * - ``scale``, ``mirror``
      - :func:`~operations_generic.scale`, :func:`~operations_generic.mirror`
    * - ``linear_extrude``
      - :func:`~operations_part.extrude`
    * - ``rotate_extrude``
      - :func:`~operations_part.revolve`
    * - ``offset``
      - :func:`~operations_generic.offset`, which works on solids as well
        as on sketches
    * - ``hull()``
      - :func:`~operations_sketch.make_hull`, in 2D only. There is no 3D
        hull yet.
    * - ``minkowski()``
      - no general equivalent. Its usual job, growing a shape by a circle
        or a sphere, is done by :func:`~operations_generic.offset`.
    * - ``for`` loops over positions
      - a Python loop, or :class:`~build_common.GridLocations`,
        :class:`~build_common.PolarLocations` and
        :class:`~build_common.HexLocations`
    * - ``module``
      - a Python function or class
    * - ``$fn``, ``$fa``, ``$fs``
      - not needed; see the tolerances of the mesh exporters
    * - ``import("part.stl")``
      - :func:`~importers.import_stl`, and ``import_step`` for exact
        geometry
    * - rounded edges built from solids
      - :func:`~operations_generic.fillet` and
        :func:`~operations_generic.chamfer` on selected edges

********************
Where to go next
********************

* :ref:`tutorial_sketch_then_extrude` is the first of the core tutorials,
  and introduces the sketch-first way of working.
* :ref:`tutorial_combining_solids` covers constructive solid geometry in
  build123d, and when it is and is not the better tool.
* :ref:`selecting_features` covers picking out the faces and edges to work
  on.
* :ref:`moving_objects` covers ``Pos``, ``Rot`` and locations.
