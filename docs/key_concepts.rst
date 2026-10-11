############
Key Concepts
############

The following key concepts will help new users understand build123d quickly.

.. _topology:

Topology
========

Topology, in the context of 3D modeling and computational geometry, is the
branch of mathematics that deals with the properties and relationships of
geometric objects that are preserved under continuous deformations. In the
context of CAD and modeling software like build123d, topology refers to the
hierarchical structure of geometric elements (vertices, edges, faces, etc.) and
their relationships in a 3D model. This structure defines how the components of
a model are connected, enabling operations like Boolean operations,
transformations, and analysis of complex shapes. Topology provides a formal
framework for understanding and manipulating geometric data in a consistent and
reliable manner.

The following are the topological objects that compose build123d objects:

:class:`~topology.Vertex`
    A Vertex is a data structure representing a 0D topological element. It
    defines a precise point in 3D space, often at the endpoints or intersections of
    edges in a 3D model. These vertices are part of the topological structure used
    to represent complex shapes in build123d.

:class:`~topology.Edge`
	An Edge in build123d is a fundamental geometric entity representing a 1D
	element in a 3D model. It defines the shape and position of a 1D curve within
	the model. Edges play a crucial role in defining the boundaries of faces and in
	constructing complex 3D shapes.

:class:`~topology.Wire`
	A Wire in build123d is a topological construct that represents a connected
	sequence of Edges, forming a 1D closed or open loop within a 3D model. Wires
	define the boundaries of faces and can be used to create complex shapes, making
	them essential for modeling in build123d.

:class:`~topology.Face`
	A Face in build123d represents a 2D surface in a 3D model. It defines the
	boundary of a region and can have associated geometric and topological data.
	Faces are vital for shaping solids, providing surfaces where other elements like
	edges and wires are connected to form complex structures.

:class:`~topology.Shell`
	A Shell in build123d represents a collection of Faces, defining a closed,
	connected volume in 3D space. It acts as a container for organizing and grouping
	faces into a single shell, essential for defining complex 3D shapes like solids
	or assemblies within the build123d modeling framework.

:class:`~topology.Solid`
	A Solid in build123d is a 3D geometric entity that represents a bounded
	volume with well-defined interior and exterior surfaces. It encapsulates a
	closed and watertight shape, making it suitable for modeling solid objects and
	enabling various Boolean operations such as union, intersection, and
	subtraction.

:class:`~topology.Compound`
	A Compound in build123d is a container for grouping multiple geometric
	shapes. It can hold various types of entities, such as vertices, edges, wires,
	faces, shells, or solids, into a single structure. This makes it a versatile
	tool for managing and organizing complex assemblies or collections of shapes
	within a single container.

:class:`~topology.Shape`
	A Shape in build123d represents a fundamental building block in 3D
	modeling. It encompasses various topological elements like vertices, edges,
	wires, faces, shells, solids, and compounds. The Shape class is the base class
	for all of the above topological classes.

One can use the :meth:`~topology.Shape.show_topology` method to display the
topology of a shape as shown here for a unit cube:

.. code::
	
	Solid                      at 0x7f94c55430f0, Center(0.5, 0.5, 0.5)
	└── Shell                  at 0x7f94b95835f0, Center(0.5, 0.5, 0.5)
	    ├── Face               at 0x7f94b95836b0, Center(0.0, 0.5, 0.5)
	    │   └── Wire           at 0x7f94b9583730, Center(0.0, 0.5, 0.5)
	    │       ├── Edge       at 0x7f94b95838b0, Center(0.0, 0.0, 0.5)
	    │       │   ├── Vertex at 0x7f94b9583470, Center(0.0, 0.0, 1.0)
	    │       │   └── Vertex at 0x7f94b9583bb0, Center(0.0, 0.0, 0.0)
	    │       ├── Edge       at 0x7f94b9583a30, Center(0.0, 0.5, 1.0)
	    │       │   ├── Vertex at 0x7f94b9583030, Center(0.0, 1.0, 1.0)
	    │       │   └── Vertex at 0x7f94b9583e70, Center(0.0, 0.0, 1.0)
	    │       ├── Edge       at 0x7f94b9583770, Center(0.0, 1.0, 0.5)
	    │       │   ├── Vertex at 0x7f94b9583bb0, Center(0.0, 1.0, 1.0)
	    │       │   └── Vertex at 0x7f94b9583e70, Center(0.0, 1.0, 0.0)
	    │       └── Edge       at 0x7f94b9583db0, Center(0.0, 0.5, 0.0)
	    │           ├── Vertex at 0x7f94b9583e70, Center(0.0, 1.0, 0.0)
	    │           └── Vertex at 0x7f94b95862f0, Center(0.0, 0.0, 0.0)
	...
	    └── Face               at 0x7f94b958d3b0, Center(0.5, 0.5, 1.0)
	        └── Wire           at 0x7f94b958d670, Center(0.5, 0.5, 1.0)
	            ├── Edge       at 0x7f94b958e130, Center(0.0, 0.5, 1.0)
	            │   ├── Vertex at 0x7f94b958e330, Center(0.0, 1.0, 1.0)
	            │   └── Vertex at 0x7f94b958e770, Center(0.0, 0.0, 1.0)
	            ├── Edge       at 0x7f94b958e630, Center(0.5, 1.0, 1.0)
	            │   ├── Vertex at 0x7f94b958e8b0, Center(1.0, 1.0, 1.0)
	            │   └── Vertex at 0x7f94b958ea70, Center(0.0, 1.0, 1.0)
	            ├── Edge       at 0x7f94b958e7b0, Center(1.0, 0.5, 1.0)
	            │   ├── Vertex at 0x7f94b958ebb0, Center(1.0, 1.0, 1.0)
	            │   └── Vertex at 0x7f94b958ed70, Center(1.0, 0.0, 1.0)
	            └── Edge       at 0x7f94b958eab0, Center(0.5, 0.0, 1.0)
	                ├── Vertex at 0x7f94b958eeb0, Center(1.0, 0.0, 1.0)
	                └── Vertex at 0x7f94b9592170, Center(0.0, 0.0, 1.0)
	
Users of build123d will often reference topological objects as part of the
process of creating the object as described below.

.. _empty_shapes:

Empty shapes
------------

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

Location
========

A :class:`~geometry.Location` represents a combination of translation and
rotation applied to a shape, wrapping a **position** and an **orientation**
(Euler angles). It is the fundamental object used to position and orient
geometry: every ``Shape`` (and ``Axis``, ``Plane`` and ``Location`` itself) has
a ``location`` property, and the components can be read and written through
``shape.position`` and ``shape.orientation``.

The full treatment - how to build a ``Location`` with ``Pos``/``Rot``/
``Location``, the direct movement methods, and how they are used in builder and
algebra mode - is on the :ref:`Moving Objects page <moving_objects_location>`.

As a quick reference, the four methods that change an object's location:

.. list-table:: Direct location methods
    :header-rows: 1

    * - Method
      - Positioning
      - Changes
      - Returns
    * - :meth:`~topology.Shape.locate`
      - absolute
      - in place
      - ``self``
    * - :meth:`~topology.Shape.located`
      - absolute
      - copy
      - new shape
    * - :meth:`~topology.Shape.move`
      - relative
      - in place
      - ``self``
    * - :meth:`~topology.Shape.moved`
      - relative
      - copy
      - new shape

Locations compose with the ``*`` operator and flip direction with the ``-``
operator.

Selectors
=========

.. include:: selectors.rst
