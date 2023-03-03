#####################
Introductory Examples
#####################

The examples on this page can help you learn how to build objects with Build123d, and are intended as a general overview of Build123d.

They are organized from simple to complex, so working through them in order is the best way to absorb them.

.. note::

    Some important lines are omitted below to save space, so you will most likely need to add 1 & 2 to the provided code below for them to work:

       1. ``from build123d import *``
       2. If you are using CQ-editor add the line e.g. ``show_object(ex15.part)`` at the end. Other viewers may have different commands to view the object.
       3. Similarly, you can use e.g. ``show_object(ex15.sketch)`` and ``show_object(ex15.line)`` to view sketches and lines respectively.
       4. If you want to save your resulting file from CQ-editor as an STL, it is currently best to use e.g. ``show_object(ex15.part.wrapped)``.

.. contents:: List of Examples
    :backlinks: entry

1. Simple Rectangular Plate
---------------------------------------------------

Just about the simplest possible example, a rectangular :class:`~build_part.Box`.

.. image:: assets/general_ex1.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 1]
    :end-before: [Ex. 1]

2. Plate with Hole
---------------------------------------------------

A rectangular box, but with a hole added. In this case we are using
:class:`~build_enums.Mode` ``.SUBTRACT`` to cut the :class:`~build_part.Cylinder`
from the :class:`~build_part.Box`.

.. image:: assets/general_ex2.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 2]
    :end-before: [Ex. 2]

3. An extruded prismatic solid
---------------------------------------------------

Build a prismatic solid using extrusion. This time we can first create a 2D
:class:`~build_sketch.BuildSketch` with a subtracted Rectangle and then use
:class:`~build_part.BuildPart`'s :class:`~build_part.Extrude` feature.

.. image:: assets/general_ex3.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 3]
    :end-before: [Ex. 3]

4. Building Profiles using lines and arcs
---------------------------------------------------

Sometimes you need to build complex profiles using lines and arcs. This example
builds a prismatic solid from 2D operations. It is not necessary to create
variables for the line segments, but it will be useful in a later example.
:class:`~build_sketch.BuildSketch` operates on closed Faces, and the operation
:class:`~build_sketch.MakeFace` is used to convert the pending line segments
from :class:`~build_line.BuildLine` into a closed Face. Note that to build a
closed face it requires line segments that form a closed shape.

.. image:: assets/general_ex4.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 4]
    :end-before: [Ex. 4]

5. Moving the current working point
---------------------------------------------------

Using :class:`~build_common.Locations` we can place one (or multiple) objects
at one (or multiple) places.

.. image:: assets/general_ex5.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 5]
    :end-before: [Ex. 5]

6. Using Point Lists
---------------------------------------------------

Sometimes you need to create a number of features at various
:class:`~build_common.Locations`. You can use a list of points to construct
multiple objects at once.

.. image:: assets/general_ex6.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 6]
    :end-before: [Ex. 6]

7. Polygons
---------------------------------------------------

You can create :class:`~build_sketch.RegularPolygon` for each stack point if
you would like.

.. image:: assets/general_ex7.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 7]
    :end-before: [Ex. 7]

8. Polylines
---------------------------------------------------

:class:`~build_line.Polyline` allows creating a shape from a large number
of chained points connected by lines. This example uses a polyline to create
one half of an i-beam shape, which is :class:`~build_generic.Mirror` ed to
create the final profile.

.. image:: assets/general_ex8.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 8]
    :end-before: [Ex. 8]

9. Selectors, Fillets, and Chamfers
---------------------------------------------------

This example introduces multiple useful and important concepts. Firstly :class:`~build_generic.Chamfer`
and :class:`~build_generic.Fillet` can be used to "bevel" and "round" edges respectively. Secondly,
these two methods require an edge or a list of edges to operate on. To select all
edges, you could simply pass-in ``*ex9.edges()``. Note that the star (\*) unpacks
the list.

Note that :meth:`~topolory.ShapeList.group_by` ``(Axis.Z)`` returns a list of lists of edges that is grouped by
their z-position. In this case we want to use the ``[-1]`` group which, by
convention, will be the highest z-dimension group.

.. image:: assets/general_ex9.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 9]
    :end-before: [Ex. 9]


10. Select Last and Hole
---------------------------------------------------

Using :class:`~build_enums.Select` ``.LAST`` you can select the most recently modified edges. It is used to perform a :class:`~build_generic.Fillet` in
this example. This example also makes use of :class:`~build_part.Hole` which automatically cuts through the entire part.

.. image:: assets/general_ex10.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 10]
    :end-before: [Ex. 10]

11. Use a face as a plane for BuildSketch and introduce GridLocations
----------------------------------------------------------------------------

:class:`~build_sketch.BuildSketch` accepts a Plane or a Face, so in this case we locate the Sketch
on the top of the part. Note that the face used as input to BuildSketch needs
to be Planar or unpredictable behavior can result. Additionally :class:`~build_common.GridLocations`
can be used to create a grid of points that are simultaneously used to place 4
pentagons.

Lastly, :class:`~build_part.Extrude` can be used with a negative amount and ``Mode.SUBTRACT`` to
cut these from the parent. Note that the direction implied by positive or negative
inputs to amount is relative to the normal direction of the face or plane. As a
result of this, unexpected behavior can occur if the extrude direction and mode
(ADD or SUBTRACT) are not correctly set.

.. image:: assets/general_ex11.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 11]
    :end-before: [Ex. 11]

12. Defining an Edge with a Spline
---------------------------------------------------

This example defines a side using a spline curve through a collection of points. Useful when you have an
edge that needs a complex profile.

The star (\*) operator is again used to unpack the list.

.. image:: assets/general_ex12.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 12]
    :end-before: [Ex. 12]

13. CounterBoreHoles, CounterSinkHoles and PolarLocations
-------------------------------------------------------------

We use a face to establish a location for :class:`~build_common.Workplanes`. :class:`~build_common.PolarLocations` creates a list of
points that are radially distributed.

Counter-sink and counter-bore holes are useful for creating recessed areas for fasteners.

.. image:: assets/general_ex13.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 13]
    :end-before: [Ex. 13]


14. Position on a line with '\@', '\%' and introduce Sweep
------------------------------------------------------------

Build123d includes a feature for finding the position along a line segment. This
is normalized between 0 and 1 and can be accessed using the :meth:`~topolory.Mixin1D.position_at` operator.
Similarly the :meth:`~topolory.Mixin1D.tangent_at` operator returns the line direction at a given point.

These two features are very powerful for chaining line segments together without
having to repeat dimensions again and again, which is error prone, time
consuming, and more difficult to maintain.

It is also possible to use :class:`~geometry.Vector` addition (and other vector math operations)
as seen in the ``l3`` variable.

The :class:`~build_part.Sweep` method takes any pending faces and sweeps them through the provided
path (in this case the path is taken from the pending edges from ``ex14_ln``).
:class:`~build_part.Revolve` requires a single connected wire. The pending faces must lie on the
path.

.. image:: assets/general_ex14.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 14]
    :end-before: [Ex. 14]

15. Mirroring Symmetric Geometry
---------------------------------------------------

Here mirror is used on the BuildLine to create a symmetric shape with fewer line segment commands.
Additionally the '@' operator is used to simplify the line segment commands.

``(l4 @ 1).Y`` is used to extract the y-component of the ``l4 @ 1`` vector.

.. image:: assets/general_ex15.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 15]
    :end-before: [Ex. 15]

16. Mirroring 3D Objects
---------------------------------------------------

Mirror can also be used with BuildPart (and BuildSketch) to mirror 3D objects. The ``Plane.offset()``
method shifts the plane in the normal direction (positive or negative).

.. image:: assets/general_ex16.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 16]
    :end-before: [Ex. 16]

17. Mirroring From Faces
---------------------------------------------------

Here we select the farthest face in the Y-direction and turn it into a :class:`~geometry.Plane` using the
``Plane()`` class.

.. image:: assets/general_ex17.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 17]
    :end-before: [Ex. 17]

18. Creating Workplanes on Faces
---------------------------------------------------

Here we start with an earlier example, select the top face, draw a rectangle and then use Extrude
with a negative distance and Mode.SUBTRACT to cut it out from the main body.

.. image:: assets/general_ex18.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 18]
    :end-before: [Ex. 18]

19. Locating a Workplane on a vertex
---------------------------------------------------

Here a face is selected and passed to :class:`~build_common.Workplanes`, and two different strategies are used to select vertices.
Firstly ``vtx`` uses :meth:`~topolory.ShapeList.group_by` and ``Axis.X`` to select a particular vertex. The second strategy uses a custom
defined Axis ``vtx2Axis`` that is pointing roughly in the direction of a vertex to select, and then :meth:`~topolory.ShapeList.sort_by`
this custom Axis. Then the X and Y positions of these vertices are selected and passed to :class:`~build_common.Locations`
as the center points for a :class:`~build_sketch.BuildSketch` which is used to place two circles that cuts through the main part.
Note that if you passed the variable ``vtx`` directly to :class:`~build_common.Locations` then the part would be offset from
the Workplane by the vertex z-position.

.. image:: assets/general_ex19.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 19]
    :end-before: [Ex. 19]

20. Offset Sketch Workplane
---------------------------------------------------

The ``pln`` variable is set to be coincident with the farthest face in the
negative x-direction. The resulting Plane is offset from the original position.

.. image:: assets/general_ex20.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 20]
    :end-before: [Ex. 20]

21. Create a Workplanes in the center of another shape
-------------------------------------------------------

One cylinder is created, and then the origin and z_dir of that part are used to create a new Plane for
positioning another cylinder perpendicular and halfway along the first.

.. image:: assets/general_ex21.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 21]
    :end-before: [Ex. 21]

22. Rotated Workplanes
---------------------------------------------------

It is also possible to create a rotated workplane, building upon some of the concepts in an earlier
example with the :meth:`~geometry.Plane.rotated` method.

:class:`~build_common.GridLocations` places 4 Circles on 4 points on this rotated workplane, and then the Circles are
extruded in the "both" (positive and negative) normal direction.

.. image:: assets/general_ex22.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 22]
    :end-before: [Ex. 22]

23. Revolve
---------------------------------------------------

Here we build a sketch with a :class:`~build_line.Polyline`,
:class:`~build_line.Line`, and a :class:`~build_sketch.Circle`. It is
absolutely critical that the sketch is only on one side of the axis of rotation
before Revolve is called.

To that end, Split is used with Plane.ZY to keep only one side of the Sketch.

It is highly recommended to view your sketch before you attempt to call revolve. In CQ-editor this
can be accomplished e.g. like this: ``show_object(ex23_sk.sketch)``.

.. image:: assets/general_ex23.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 23]
    :end-before: [Ex. 23]

24. Loft
---------------------------------------------------

Loft is a very powerful tool that can be used to join dissimilar shapes. In this case we make a
conical-like shape from a circle and a rectangle that is offset vertically. In this case
:class:`~build_part.Loft` automatically takes the pending faces that were added by the two BuildSketches.
Loft can behave unexpectedly when the input faces are not parallel to each other.

.. image:: assets/general_ex24.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 24]
    :end-before: [Ex. 24]

25. Offset Sketch
---------------------------------------------------

BuildSketch faces can be transformed with a 2D :class:`~build_generic.Offset`. They can be offset inwards or outwards,
and with different techniques for extending the corners (see :class:`~build_enums.Kind` in the Offset docs).

.. image:: assets/general_ex25.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 25]
    :end-before: [Ex. 25]

26. Offset Part To Create Thin features
---------------------------------------------------

BuildPart parts can also be transformed using an offset, but in this case with
a 3D :class:`~build_generic.Offset`. Also commonly known as a shell, this allows creating thin walls
using very few operations. This can also be offset inwards or outwards. Faces
can be selected to be "deleted" using the ``openings`` parameter of :class:`~build_generic.Offset`.

Note that self intersecting edges and/or faces can break both 2D and 3D offsets.

.. image:: assets/general_ex26.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 26]
    :end-before: [Ex. 26]

27. Splitting an Object
---------------------------------------------------

You can split an object using a plane, and retain either or both halves. In this case we select
a face and offset half the width of the box.

.. image:: assets/general_ex27.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 27]
    :end-before: [Ex. 27]

28. Locating features based on Faces
---------------------------------------------------

We create a triangular prism with ``Mode.PRIVATE`` and then later use the faces of this object to
cut holes in a sphere. We are able to create multiple Workplanes at the same time by unpacking the
list of faces.

.. image:: assets/general_ex28.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 28]
    :end-before: [Ex. 28]

29. The Classic OCC Bottle
---------------------------------------------------

Build123d is based on the OpenCascade.org (OCC) modeling Kernel. Those who are familiar with OCC
know about the famous ‘bottle’ example. We use a 3D Offset and the openings parameter to create
the bottle opening.

.. image:: assets/general_ex29.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 29]
    :end-before: [Ex. 29]

30. Bezier Curve
---------------------------------------------------

Here ``pts`` is used as an input to both :class:`~build_line.Polyline` and
:class:`~build_line.Bezier` and ``wts`` to Bezier alone. These two together
create a closed line that is made into a face and extruded.

.. image:: assets/general_ex30.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 30]
    :end-before: [Ex. 30]

31. Nesting Locations
---------------------------------------------------

Locations contexts can be nested to create groups of shapes. Here 24 triangles, 6 squares, and
1 hexagon are created and then extruded. Notably :class:`~build_common.PolarLocations`
rotates any "children" groups by default.

.. image:: assets/general_ex31.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 31]
    :end-before: [Ex. 31]

32. Python For-Loop
---------------------------------------------------

In this example, a standard python for-loop is used along with a list of faces extracted from a BuildSketch
to progressively modify the extrusion amount. There are 7 faces in the BuildSketch, so this results in 7
separate calls to :class:`~build_part.Extrude`. ``Mode.PRIVATE`` is used in :class:`~build_sketch.BuildSketch`
to avoid adding these faces until the for-loop.

.. image:: assets/general_ex32.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 32]
    :end-before: [Ex. 32]

33. Python Function and For-Loop
---------------------------------------------------

Building on the previous example, a standard python function is used to return
a :class:`~build_sketch.BuildSketch` as a function of several inputs to
progressively modify the size of each square.

.. image:: assets/general_ex33.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 33]
    :end-before: [Ex. 33]

34. Embossed and Debossed Text
---------------------------------------------------

The text "Hello" is placed on top of a rectangle and embossed (raised) by placing a BuildSketch on the
top face (``topf``). Note that :class:`~build_enums.Align` is used to control the text placement. We re-use
the ``topf`` variable to select the same face and deboss (indented) the text "World". Note that if we simply
ran ``BuildSketch(ex34.faces().sort_by(Axis.Z)[-1])`` for both ``ex34_sk1&2`` it would incorrectly locate
the 2nd "World" text on the top of the "Hello" text.

.. image:: assets/general_ex34.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 34]
    :end-before: [Ex. 34]

35. Slots
---------------------------------------------------

Here we create a :class:`~build_sketch.SlotCenterToCenter` and then use a
:class:`~build_line.BuildLine` and :class:`~build_line.RadiusArc` to create an
arc for two instances of :class:`~build_sketch.SlotArc`.

.. image:: assets/general_ex35.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 35]
    :end-before: [Ex. 35]

36. Extrude Until
---------------------------------------------------

Sometimes you will want to extrude until a given face that can be not planar or
where you might not know easily the distance you have to extrude to. In such
cases you can use :class:`~build_part.Extrude` :class:`~build_enums.Until`
with ``Until.NEXT`` or ``Until.LAST``.

.. image:: assets/general_ex36.svg
    :align: center

.. literalinclude:: general_examples.py
    :start-after: [Ex. 36]
    :end-before: [Ex. 36]
