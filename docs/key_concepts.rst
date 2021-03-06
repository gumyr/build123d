############
Key Concepts
############

The following key concepts will help new users understand build123d quickly.

********
Builders
********

The three builders, `BuildLine`, `BuildSketch`, and `BuildPart` are tools to create
new objects - not the objects themselves. Each of the objects and operations applicable
to these builders create objects of the standard CadQuery Direct API, most commonly
`Compound` objects.  This is opposed to CadQuery's Fluent API which creates objects
of the `Workplane` class which frequently needed to be converted back to base
class for further processing.

One can access the objects created by these builders by referencing the appropriate
instance variable. For example:

.. code-block:: python

    with BuildPart() as my_part:
        ...

    show_object(my_part.part)

.. code-block:: python

    with BuildSketch() as my_sketch:
        ...

    show_object(my_sketch.sketch)

.. code-block:: python

    with BuildLine() as my_line:
        ...

    show_object(my_line.line)

****************
Operation Inputs
****************

When one is operating on an existing object, e.g. adding a fillet to a part,
a sequence of objects is often required. A python sequence of objects is
simply either a single object or a string of objects separated by commas.
To pass an array into a sequence, precede it with a `*` operator.
When a sequence is followed by another parameter, that parameter must be
entered as a keyword parameter (e.g. radius=1) to separate this parameter
from the preceding sequence.

Here is the definition of `FilletPart` to help illustrate:

.. code-block:: python

    class FilletPart(Compound):
        def __init__(self, *edges: Edge, radius: float):

To use this fillet operation, a sequence of edges must be provided followed by
a fillet radius as follows:

.. code-block:: python

    with BuildPart() as pipes:
        Box(10, 10, 10, rotation=(10, 20, 30))
        ...
        FilletPart(*pipes.edges(Select.LAST), radius=0.2)

Here the list of edges from the last operation of the `pipes` builder are converted
to a sequence and a radius is provided as a keyword argument.

*****************
Combination Modes
*****************
Almost all objects or operations have a `mode` parameter which is defined by the
`Mode` Enum class as follows:

.. code-block:: python

    class Mode(Enum):
        ADD = auto()
        SUBTRACT = auto()
        INTERSECT = auto()
        REPLACE = auto()
        PRIVATE = auto()

The `mode` parameter describes how the user would like the object or operation to
interact with the object within the builder. For example, `Mode.ADD` will
integrate a new object(s) in with an existing `part`.  Note that a part doesn't
necessarily have to be a single object so multiple distinct objects could be added
resulting is multiple objects stored as a `Compound` object. As one might expect
`Mode.SUBTRACT`, `Mode.INTERSECT`, and `Mode.REPLACE` subtract, intersect, or replace
(from) the builder's object. `Mode.PRIVATE` instructs the builder that this object
should not be combined with the builder's object in any way.

Most commonly, the default `mode` is `Mode.ADD` but this isn't always true.
For example, the `Hole` classes use a default `Mode.SUBTRACT` as they remove
a volume from the part under normal circumstances. However, the `mode` used in
the `Hole` classes can be specified as `Mode.ADD` or `Mode.INTERSECT` to
help in inspection or debugging.

*********************************
Pushing Points & Rotating Objects
*********************************

build123d stores points (to be specific `Locations`) internally to be used as
positions for the placement of new objects.  By default, a single location
will be created at the origin of the given workplane such that:

.. code-block:: python

    with BuildPart() as pipes:
        Box(10, 10, 10, rotation=(10, 20, 30))

will create a single 10x10x10 box centered at (0,0,0) - by default objects are
centered. One can create multiple objects by pushing points prior to creating
objects as follows:

.. code-block:: python

    with BuildPart() as pipes:
        PushPointsToPart((-10, -10, -10), (10, 10, 10))
        Box(10, 10, 10, rotation=(10, 20, 30))

which will create two boxes.  Note that whenever points are pushed, previous
points are replaced.

To orient a part, a `rotation` parameter is available on `BuildSketch`` and
`BuildPart` APIs. When working in a sketch, the rotation is a single angle in
degrees so the parameter is a float. When working on a part, the rotation is
a three dimensional `Rotation` object of the form
`Rotation(<about x>, <about y>, <about z>)` although a simple three tuple of
floats can be used as input.  As 3D rotations are not cumulative, one can
combine rotations with the `*` operator like this:
`Rotation(10, 20, 30) * Rotation(0, 90, 0)` to generate any desired rotation.

.. hint::
    Experts Only

    `PushPoints` will accept `Location` objects for input which allows one
    to specify both the position and orientation.  However, the orientation
    is often determined by the `Plane` that an object was created on.
    `Rotation` is a subclass of `Location` and therefore will also accept
    a position component.

*************************
Builder's Pending Objects
*************************

When a builder exits, it will push the object created back to its parent if
there was one.  Here is an example:

.. code-block:: python

    with BuildPart() as pillow_block:
        with BuildSketch() as plan:
            Rectangle(width, height)
            FilletSketch(*plan.vertices(), radius=fillet)
        Extrude(thickness)

`BuildSketch` exits after the `FilletSketch` operation and when doing so it transfers
the sketch to the `pillow_block` instance of `BuildPart` as the internal instance variable
`pending_faces`. This allows the `Extrude` operation to be immediately invoked as it
extrudes these pending faces into `Solid` objects. Likewise, `Loft` will take all of the
`pending_faces` and attempt to create a single `Solid` object from them.

Normally the user will not need to interact directly with pending objects.

*************************************
Multiple Work Planes - BuildPart Only
*************************************

When `BuildPart` is invoked it will by default select the XY plane for the user to work on.
One can work on any plane by overriding this `workplane` parameter. The `workplane` can be changed
at any time to one or more planes which is most commonly used to create workplanes from
existing object Faces. The `WorkplanesFromFaces` class is used to do this as shown below:

.. code-block:: python

    with BuildPart() as pipes:
        Box(10, 10, 10, rotation=(10, 20, 30))
        WorkplanesFromFaces(*pipes.faces(), replace=True)
        with BuildSketch() as pipe:
            Circle(4)
        Extrude(-5, mode=Mode.SUBTRACTION)

In this example a `Box` is created and workplanes are created from each of the box's faces.
The following sketch is then created on each of these workplanes and the `Extrude` operation
creates holes in each of the faces of the box.
