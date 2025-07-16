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

Location
========

A :class:`~geometry.Location` represents a combination of translation and rotation
applied to a topological or geometric object. It encapsulates information
about the spatial orientation and position of a shape within its reference
coordinate system. This allows for efficient manipulation of shapes within
complex assemblies or transformations. The location is typically used to
position shapes accurately within a 3D scene, enabling operations like
assembly, and boolean operations. It's an essential component in build123d
for managing the spatial relationships of geometric entities, providing a
foundation for precise 3D modeling and engineering applications.

The topological classes (sub-classes of :class:`~topology.Shape`) and the geometric classes 
:class:`~geometry.Axis` and :class:`~geometry.Plane` all have a ``location`` property.
The :class:`~geometry.Location` class itself has ``position`` and ``orientation`` properties
that have setters and getters as shown below:


.. doctest::

    >>> from build123d import *
    >>> # Create an object and extract its location
    >>> b = Box(1, 1, 1)
    >>> box_location = b.location
    >>> box_location
    (p=(0.00, 0.00, 0.00), o=(-0.00, 0.00, -0.00))
    >>> # Set position and orientation independently
    >>> box_location.position = (1, 2, 3)
    >>> box_location.orientation = (30, 40, 50)
    >>> box_location.position
    Vector: (1.0, 2.0, 3.0)
    >>> box_location.orientation
    Vector: (29.999999999999993, 40.00000000000002, 50.000000000000036)

Combining the getter and setter enables relative changes as follows:

.. doctest::

    >>> # Relative change
    >>> box_location.position += (3, 2, 1)
    >>> box_location.position
    Vector: (4.0, 4.0, 4.0)

There are also four methods that are used to change the location of objects:

* :meth:`~topology.Shape.locate` - absolute change of this object
* :meth:`~topology.Shape.located` - absolute change of copy of this object
* :meth:`~topology.Shape.move` - relative change of this object
* :meth:`~topology.Shape.moved` - relative change of copy of this object

Locations can be combined with the ``*`` operator and have their direction flipped with
the ``-`` operator.

Selectors
=========

.. include:: selectors.rst
