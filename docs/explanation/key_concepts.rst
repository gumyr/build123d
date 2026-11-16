.. _key_concepts:

############
Key concepts
############

A handful of ideas lie underneath everything in build123d, in both of its
modes. This page sets them out: what a shape is made of, the difference
between a shape and its geometry, the three kinds of object a design is
built from, and the ways of saying where something is.

.. _topology:

*****************************
Shapes are made of shapes
*****************************

A solid is bounded by faces, a face by edges, and an edge by vertices. This
structure, which element is made of which and how they are joined, is the
*topology* of a shape. It is what lets a model be asked for "the top face"
or "the edges of that face", and what an operation such as a fillet works
on.

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [hierarchy]
    :end-before: [hierarchy]

The topological objects that make up build123d shapes are:

:class:`~topology.Vertex`
    A Vertex is a 0D element. It defines a precise point in 3D space, often
    at the endpoints or intersections of edges in a 3D model.

:class:`~topology.Edge`
    An Edge is a 1D element: a single piece of a curve, such as a straight
    line, an arc or a spline, between two vertices. Edges define the
    boundaries of faces, and are what paths and outlines are drawn with.

:class:`~topology.Wire`
    A Wire is a connected sequence of Edges, joined end to end, forming an
    open path or a closed loop. Wires define the boundaries of faces: every
    face has one outer wire, and an inner wire for each hole in it.

:class:`~topology.Face`
    A Face is a 2D element: a bounded piece of a surface, flat or curved.
    Faces are what solids are enclosed by, and a flat face is what a sketch
    is made of.

:class:`~topology.Shell`
    A Shell is a set of Faces joined along their edges into one connected
    surface. A shell may be *closed*, enclosing a volume, as the skin of a
    solid is; or *open*, as a sheet metal part's reference surface is, or a
    surface model that is not yet watertight.

:class:`~topology.Solid`
    A Solid is a 3D element: a volume bounded by a closed, watertight shell,
    with a well-defined inside and outside. Solids are what the boolean
    operations of union, intersection and subtraction work on.

:class:`~topology.Compound`
    A Compound is a container that groups shapes of any kind, vertices,
    edges, wires, faces, shells, solids and other compounds, into a single
    shape. It is how a part made of several solids, a sketch of several
    faces, or an assembly of many parts is held as one object.

:class:`~topology.Shape`
    Shape is the base class of all of the above. What every shape can do,
    be moved, be selected from, be measured, is defined there.

Three more classes are built on ``Compound``, and they are the ones a design
is mostly made of. They are described :ref:`below <part_sketch_curve_concept>`:

:class:`~topology.Part`
    A Part is a Compound of Solids: a 3D object.

:class:`~topology.Sketch`
    A Sketch is a Compound of Faces lying in one plane: a 2D object.

:class:`~topology.Curve`
    A Curve is a Compound of Edges and Wires: a 1D object.

:meth:`~topology.Shape.show_topology` prints the structure of a shape. Here
is the top face of the box, with its one wire, four edges and their
vertices:

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [topology]
    :end-before: [topology]

.. code-block:: text

    Face               at 0x11e611a70, Center(0, 0, 2)
    └── Wire           at 0x11db5e7f0, Center(0, 0, 2)
        ├── Edge       at 0x11e4fb0b0, Center(-1, 0, 2)
        │   ├── Vertex at 0x11e5f2630, Center(-1, 1.5, 2)
        │   └── Vertex at 0x11e18a2b0, Center(-1, -1.5, 2)
        ├── Edge       at 0x11e18a2b0, Center(0, 1.5, 2)
        │   ├── Vertex at 0x11e4fb0b0, Center(1, 1.5, 2)
        │   └── Vertex at 0x11e611cb0, Center(-1, 1.5, 2)
        ├── Edge       at 0x11e5f2130, Center(1, 0, 2)
        │   ├── Vertex at 0x11e4fb0b0, Center(1, 1.5, 2)
        │   └── Vertex at 0x11e18a2b0, Center(1, -1.5, 2)
        └── Edge       at 0x11e18a2b0, Center(0, -1.5, 2)
            ├── Vertex at 0x11e5f2130, Center(1, -1.5, 2)
            └── Vertex at 0x11e611f70, Center(-1, -1.5, 2)

Picking out particular faces, edges and vertices is the subject of
:ref:`selecting_features`.

*************************
Topology and geometry
*************************

The topology of a shape says what is joined to what. It does not say what
shape anything is. That is the *geometry*: the curve an edge lies on and the
surface a face lies on.

An edge is a piece of a curve, cut off at two points. A face is a piece of a
surface, cut off along its wires. The curve may be a line, a circle or a
spline, and the surface a plane, a cylinder, a sphere or something freer,
and each element knows which:

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [geometry]
    :end-before: [geometry]

A cylinder has two flat faces and one cylindrical one, two circular edges
and one straight one, the seam where the curved face meets itself.

This is what it means that build123d's geometry is exact. The curved face of
the can is a cylinder, held as an axis and a radius, not as a ring of flat
facets. Its radius can be read back, it meets the end faces in true circles,
and a hole cut in it has the true curve of that intersection. Triangles
appear only when a model is exported to a mesh.

.. _part_sketch_curve_concept:

******************************
Parts, sketches and curves
******************************

A design is seldom one solid or one face. A part with a loose pin has two
solids, a sketch of four holes has four faces, and a path drawn in pieces
has several edges. build123d therefore works in three kinds of object, one
for each dimension, each able to hold any number of pieces:

.. list-table::
    :header-rows: 1
    :widths: 15 15 30 40

    * - Object
      - Dimension
      - Made of
      - Built with
    * - ``Curve``
      - 1D
      - edges and wires
      - ``BuildLine``, or lines and arcs joined with ``+``
    * - ``Sketch``
      - 2D
      - faces in one plane
      - ``BuildSketch``, or sketch objects such as ``Rectangle``
    * - ``Part``
      - 3D
      - solids
      - ``BuildPart``, or part objects such as ``Box``

Each is a ``Compound``, and the ready-made objects belong to them:

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [kinds]
    :end-before: [kinds]

The kind is kept through every operation. Two parts added together make a
part, a sketch with a hole cut in it is still a sketch, and a builder hands
back the kind it is named for: ``BuildPart`` a ``Part``, ``BuildSketch`` a
``Sketch`` and ``BuildLine`` a ``Curve``. This is also why objects of
different dimensions cannot be added to one another: a sketch is turned
into a part by an operation such as ``extrude``, not by arithmetic.

***************************************
Vectors, axes, planes and locations
***************************************

Four different things are used to say where something is, and they are
easily confused.

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [places]
    :end-before: [places]

A **Vector** is three numbers. It serves as a point, as a direction, or as
a displacement from one point to another, and wherever a point is wanted a
plain tuple such as ``(1, 2, 3)`` will do.

An **Axis** is a line with a direction: a point it passes through and the
way it points. It is what something is revolved about, sorted along or
filtered by. ``Axis.X``, ``Axis.Y`` and ``Axis.Z`` are the three through the
origin.

A **Plane** is a flat surface with a coordinate system of its own: an
origin, an X direction and a normal, which is its Z direction. It is what a
sketch is drawn on. ``Plane.XY``, ``Plane.XZ``, ``Plane.YZ`` and their
relatives are the ones through the origin.

A **Location** is a position together with a rotation. It is what moves a
shape: it says where the shape's own origin goes and which way the shape is
turned there. ``Pos`` makes a location with a position only, and ``Rot`` one
with a rotation only.

A plane and a location hold the same information, an origin and an
orientation, and each can be made from the other. They differ in use: a
plane is something to draw on, a location something to place with. An axis
holds less, since it has no notion of which way is "up" around itself.

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [conversions]
    :end-before: [conversions]

Planes and axes can also be taken from the model, which is how a feature is
put on an existing face or turned about an existing edge.
:ref:`placing_sketches` and :ref:`moving_objects` cover using all four.

**************************
A shape has a location
**************************

Every shape carries a location of its own, which says where its geometry
sits in space. Moving a shape changes that location and nothing else. The
geometry is not recomputed.

.. literalinclude:: /explanation/key_concepts.py
    :language: build123d
    :start-after: [location]
    :end-before: [location]

``moved`` returns a new shape that shares the geometry of the first and has
a different location, which is why a hundred copies of one screw cost little
more than one. ``Pos(5, 0, 0) * first`` does the same thing. The methods
come in pairs: ``moved`` and ``located`` return a new shape, and ``move``
and ``locate`` change the shape they are called on.

When a shape is part of an assembly its location is relative to its parent,
so moving the assembly carries its parts with it. :ref:`assembly` covers
that.

.. _empty_shapes:

************
Empty shapes
************

Every shape class has an empty value, made by its constructor with no
arguments: ``Solid()``, ``Face()``, ``Part()``, ``Sketch()``, ``Curve()`` and so
on, including ``Vertex()``. An empty shape is a shape with nothing in it that
still knows what kind of shape it is. It is what an operation returns when it
legitimately leaves nothing, so a model that cuts a feature away entirely, or
intersects two parts that do not meet, carries on with an empty ``Part`` rather
than ``None`` or an error.

An empty shape behaves like the number zero:

* ``bool(shape)`` is ``False`` and ``shape.is_empty`` is ``True``
* ``a + Part()`` is ``a``, ``Part() - a`` is ``Part()`` and ``a & Part()`` is ``Part()``
* ``a - a`` is the empty ``Part``, ``Rectangle(1, 1) - Rectangle(1, 1)`` the empty ``Sketch``
* every selector returns an empty ``ShapeList``: ``Solid().faces() == []``
* ``volume``, ``area`` and the moments of an empty shape are ``0``
* moving, copying and pickling an empty shape give an empty shape
* ``shape.intersect(other)`` returns an empty ``ShapeList`` when nothing intersects
* ``shape.split(plane)`` returns the empty shape for a side with nothing on it

An empty shape has no place or direction, so asking for one raises
``ValueError``: ``Solid().center()`` says "An empty Solid has no center", and
``location``, ``position``, ``normal_at`` and the like do the same. Exporting
an empty shape raises too, since there is nothing to write.

A builder that has not yet built anything holds the empty shape of its type:
``BuildPart().part`` is ``Part()`` until something is added. A first operation
that removes - ``Mode.SUBTRACT`` or ``Mode.INTERSECT`` on nothing - still
raises, as it can only be a mistake.

To test whether a result has anything in it, use its truth value or
``is_empty``; a shape result is never ``None``. Geometry is different: a
``Vector``, ``Axis`` or ``Plane`` is a value rather than a set of points, so it
has no empty form, and an intersection of geometry that finds nothing, such as
two parallel axes, returns ``None``. Either kind of "nothing" reads as false, so
``if not a & b:`` works for shapes and geometry alike.
