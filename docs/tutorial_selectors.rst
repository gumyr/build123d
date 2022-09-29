#################
Selector Tutorial
#################

This tutorial provides a step by step guide in using selectors as we create
this part:

.. image:: selector_after.svg
    :align: center


*************
Step 1: Setup
*************

Before getting to the CAD operations, this selector script needs to import the build123d
environment.

.. literalinclude:: selector_example.py
    :lines: 27

**********************************
Step 2: Create Base with BuildPart
**********************************

To start off, the part will be based on a cylinder so we'll use the ``Cylinder`` object
of ``BuildPart``:

.. literalinclude:: selector_example.py
    :lines: 27,39-40
    :emphasize-lines: 2-3


************************
Step 3: Create Workplane
************************

The remainder of the features in this design will be created on the top of the cylinder
so we'll create a workplane centered on the top of the cylinder.  To locate this
workplane we'll use the cylinder's top Face as shown here:

.. literalinclude:: selector_example.py
    :lines: 27,39-40,41
    :emphasize-lines: 4

Here we're using selectors to find that top Face - let's break down
``example.faces() >> Axis.Z``:

Step 3a: Extract Faces from a part
----------------------------------

The first sub-step is the extraction of all of the Faces from the part that we're
building. The identifier of ``example`` was assigned when ``BuildPart`` when
it was instantiated so ``example.faces()`` will extract all of the Faces from
our part into a custom type of python ``list`` - a ``ShapeList`` (see
:ref:`API Reference/ShapeList <shape_list>` for a full description).

Step 3b: Get top Face
---------------------

The next sub-step is to sort the ShapeList of Faces by their position with
respect to the Z Axis. The ``>>`` operator will sort the list by relative position
of the object's center to the ``Axis.Z`` and also
select the last item on that list - or return the top Face of the ``example`` part.

*******************************
Step 4: Create a six sided hole
*******************************

The object has a hexagon hole in the top which we'll build on the previously created
workplane.

.. literalinclude:: selector_example.py
    :lines: 27,39-40,41,42-44
    :emphasize-lines: 5-7

Step 4a: Draw a hexagon on top of the part
------------------------------------------

``BuildSketch`` is the tool for drawing on planar surfaces so we'll create one
with the use of ``RegularPolygon`` with six sides.

Step 4b: Extrude the hexagon and create a hole
----------------------------------------------

To create the hole we'll extrude the sketch we created in the previous step
in a negative direction - i.e. down - and subtract this hexagon shape from the
``example`` part.  Note the use of ``mode=Mode.SUBTRACT`` which is how we
instruct the builder to cut the hexagon from the part.

*********************************
Step 5: Create a central cylinder
*********************************

To create the internal cylindrical feature we'll repeat Step 4 but with
a ``Circle`` and ``mode=Mode.ADD`` (which is the default) which adds
the feature to the ``example`` part.

.. literalinclude:: selector_example.py
    :lines: 27,39-40,41,42-44,45-47
    :emphasize-lines: 8-10

At this point the part looks like:

.. image:: selector_before.svg
    :align: center

*************************************
Step 6: Fillet the top perimeter Edge
*************************************

The final step is to apply a fillet to the top perimeter.

.. literalinclude:: selector_example.py
    :lines: 27,39-40,41,42-44,45-47,49
    :emphasize-lines: 11

Here we're using the ``Fillet`` operation which needs two things:
the edge(s) to fillet and the radius of the fillet. To provide
the edge, we'll use more selectors as described in the following
sub-steps.

Step 6a: Extract all the Edges
------------------------------

Much like selecting Faces in Step 3a, we'll select all of the ``example``
part's edges with ``example.edges()``.

Step 6b: Filter the Edges for circles
-------------------------------------

Since we know that the edge we're looking for is a circle, we can
filter the edges selected in Step 6a for just those that are of
geometric type ``CIRCLE`` with ``example.edges() % GeomType.CIRCLE``.
This step removes all of the Edges of the hexagon hole.

Step 6c: Sort the circles by radius
-----------------------------------

The perimeter are the largest circles - the central cylinder must be
excluded - so we'll sort all of the circles by their radius with:
``example.edges() % GeomType.CIRCLE > SortBy.RADIUS``.

Step 6d: Slice the list to get the two largest
----------------------------------------------

We know that the ``example`` part has two perimeter circles so we'll
select just the top two edges from the sorted circle list with:
``(example.edges() % GeomType.CIRCLE > SortBy.RADIUS)[-2:]``.  The
syntax of this slicing operation is standard python list slicing.

Step 6e: Select the top Edge
----------------------------

The last sub-step is to select the top perimeter edge, the one with
the greatest Z value which we'll do with the ``>>`` operator just like
Step 3b - note that the operators work on all Shape objects (Edges, Wires,
Faces, Solids, and Compounds) - with:
``(example.edges() % GeomType.CIRCLE > SortBy.RADIUS)[-2:] >> Axis.Z``.

**********
Conclusion
**********

By using selectors as we have in this example we've used methods
of identifying features that are robust to features changing within
the part. We've also avoided the classic CAD "Topological naming problem"
by never referring to features with names or tags that could become obsolete
as the part changes.

When possible, avoid using static list indices to refer to features
extracted from methods like ``edges()`` as the order within the list
is not guaranteed to remain the same.
