########
Tutorial
########

This tutorial provides a step by step guild to creating a script to build a parametric
Lego block.

*************
Step 1: Setup
*************

Before getting to the CAD operations, this lego script needs to import the build123d
environment. There are over 100 python classes in build123d so we'll just import them
all with an `from build123d import *` but there are other options that we won't explore
here.  In addition, the `Plane` object from `cadquery` will be used so we'll import
that class as well.

The dimensions of the lego block follow. A key parameter is `pip_count`, the length
of the Lego blocks in pips. This parameter must be at least 2.

.. code-block:: python

    from build123d import *
    from cadquery import Plane

    pip_count = 6

    lego_unit_size = 8
    pip_height = 1.8
    pip_diameter = 4.8
    block_length = lego_unit_size * pip_count
    block_width = 16
    base_height = 9.6
    block_height = base_height + pip_height
    support_outer_diameter = 6.5
    support_inner_diameter = 4.8
    ridge_width = 0.6
    ridge_depth = 0.3
    wall_thickness = 1.2


********************
Step 2: Part Builder
********************

The Lego block will be created by the `BuildPart` builder as it's a discrete three
dimensional part; therefore, we'll instantiate a `BuildPart` with the name `lego`.

.. code-block:: python

    with BuildPart() as lego:

**********************
Step 3: Sketch Builder
**********************

Lego blocks have quite a bit of internal structure. To create this structure we'll
draw a two dimensional sketch that will later be extruded into a three dimensional
object.  As this sketch will be part of the lego part, we'll create a sketch builder
in the context of the part builder as follows:

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:

Note that builder instance names are optional - we'll use `plan` to reference the sketch.

***************************
Step 4: Perimeter Rectangle
***************************

The first object in the sketch is going to be a rectangle the dimensions of the outside
of the lego block. The following step is going to refer to this rectangle, so it will
be assigned the identifier `perimeter`.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)

Once the `Rectangle` object is created the sketch appears as follows:

.. image:: tutorial_step4.svg
  :align: center

******************************
Step 5: Offset to Create Walls
******************************

To create the walls of the block the rectangle that we've created needs to be
hollowed out. This will be done with the `Offset` operation which is going to
create a new object from `perimeter`.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )

The first parameter to `Offset` is the reference object. The `amount` is a
negative value to indicate that the offset should be internal. The `kind`
parameter controls the shape of the corners - `Kind.INTERSECTION` will create
square corners. Finally, the `mode` parameter controls how this object will
be placed in the sketch - in this case subtracted from the existing sketch.
The result is shown here:

.. image:: tutorial_step5.svg
  :align: center

Now the sketch consists of a hollow rectangle.

****************************
Step 6: Create Internal Grid
****************************

The interior of the Lego block has small ridges on all four internal walls.
These ridges will be created as a double row and column of thin rectangles. To
space this grid a pair of `GridLocations` location contexts will be used which
provide one or more positions to all of the objects within their scope - in
this case a single `Rectangle`.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)

Here we can see that the first `GridLocations` create two positions which causes
two horizontal rectangles to be created.  The second `GridLocations` works in the same way
but creates `pip_count` positions and therefore vertical rectangles. Note that keyword
parameter are optional in this case.

The result looks like this:

.. image:: tutorial_step6.svg
  :align: center

*********************
Step 7: Create Ridges
*********************

To convert the internal grid to ridges, the center needs to be removed. This will be done
with another `Rectangle`.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)
            Rectangle(
                block_length - 2 * (wall_thickness + ridge_depth),
                block_width - 2 * (wall_thickness + ridge_depth),
                mode=Mode.SUBTRACT,
            )

The `Rectangle` is subtracted from the sketch to leave the ridges as follows:

.. image:: tutorial_step7.svg
  :align: center


**********************
Step 8: Hollow Circles
**********************

Lego blocks use a set of internal hollow cylinders that the pips push against
to hold two blocks together. These will be created with `Circle`.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)
            Rectangle(
                block_length - 2 * (wall_thickness + ridge_depth),
                block_width - 2 * (wall_thickness + ridge_depth),
                mode=Mode.SUBTRACT,
            )
            with GridLocations(
                x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
            ):
                Circle(radius=support_outer_diameter / 2)
                Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)

Here another `GridLocations` is used to position the centers of the circles.  Note
that since both `Circle` objects are in the scope of the location context, both
Circles will be positioned at these locations.

Once the Circles are added, the sketch is complete and looks as follows:

.. image:: tutorial_step8.svg
  :align: center

***********************************
Step 9: Extruding Sketch into Walls
***********************************

Now that the sketch is complete it needs to be extruded into the three dimensional
wall object.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)
            Rectangle(
                block_length - 2 * (wall_thickness + ridge_depth),
                block_width - 2 * (wall_thickness + ridge_depth),
                mode=Mode.SUBTRACT,
            )
            with GridLocations(
                x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
            ):
                Circle(radius=support_outer_diameter / 2)
                Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
        Extrude(base_height - wall_thickness)

Note how the `Extrude` operation is no longer in the `BuildSketch` scope and back into
the `BuildPart` scope. This causes `BuildSketch` to exit and transfer the sketch that
we've created to `BuildPart` for further processing by `Extrude`.

The result is:

.. image:: tutorial_step9.svg
  :align: center


*********************
Step 10: Adding a Top
*********************

Now that the walls are complete, the top of the block needs to be added. Although this
could be done with another sketch, we'll add a box to the top of the walls.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)
            Rectangle(
                block_length - 2 * (wall_thickness + ridge_depth),
                block_width - 2 * (wall_thickness + ridge_depth),
                mode=Mode.SUBTRACT,
            )
            with GridLocations(
                x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
            ):
                Circle(radius=support_outer_diameter / 2)
                Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
        Extrude(base_height - wall_thickness)
        with Locations((0, 0, lego.vertices().sort_by(SortBy.Z)[-1].z)):
            Box(
                length=block_length,
                width=block_width,
                height=wall_thickness,
                centered=(True, True, False),
            )

To position the top, we'll create a new location context `Locations` at the center
and at the height of the walls. To determine the height we'll exact that from the
`lego.part` by using the `vertices()` method which returns a list of the positions
of all of the vertices of the lego block so far. Since we're interested in the top,
we'll sort by the vertical (Z) axis and take the top of the list (index -1). Finally,
the `z` property of this vertex will return just the height of the top.

Within the scope of this `Locations` context, a `Box` is created, centered in over
the x and y axis but not in the z thus aligning with the top of the walls.

The base is closed now as shown here:

.. image:: tutorial_step10.svg
  :align: center

********************
Step 11: Adding Pips
********************

The final step is to add the pips to the top of the Lego block. To do this we'll create
a new workplane on top of the block where we can position the pips.

.. code-block:: python

    with BuildPart() as lego:
        with BuildSketch() as plan:
            perimeter = Rectangle(width=block_length, height=block_width)
            Offset(
                perimeter,
                amount=-wall_thickness,
                kind=Kind.INTERSECTION,
                mode=Mode.SUBTRACT,
            )
            with GridLocations(x_spacing=0, y_spacing=lego_unit_size, x_count=1, y_count=2):
                Rectangle(width=block_length, height=ridge_width)
            with GridLocations(lego_unit_size, 0, pip_count, 1):
                Rectangle(width=ridge_width, height=block_width)
            Rectangle(
                block_length - 2 * (wall_thickness + ridge_depth),
                block_width - 2 * (wall_thickness + ridge_depth),
                mode=Mode.SUBTRACT,
            )
            with GridLocations(
                x_spacing=lego_unit_size, y_spacing=0, x_count=pip_count - 1, y_count=1
            ):
                Circle(radius=support_outer_diameter / 2)
                Circle(radius=support_inner_diameter / 2, mode=Mode.SUBTRACT)
        Extrude(base_height - wall_thickness)
        with Locations((0, 0, lego.vertices().sort_by(SortBy.Z)[-1].z)):
            Box(
                length=block_length,
                width=block_width,
                height=wall_thickness,
                centered=(True, True, False),
            )
        with Workplanes(lego.faces().sort_by(SortBy.Z)[-1]):
            with GridLocations(lego_unit_size, lego_unit_size, pip_count, 2):
                Cylinder(
                    radius=pip_diameter / 2, height=pip_height, centered=(True, True, False)
                )

Much like the location contexts, the `Workplanes` context creates one or more planes that
can be used to position further features.  In this case, the workplane is created from the
top Face of the Lego block by using the `faces` method and then sorted as previously discussed.

On the new workplane, a grid of locations is created and a number of `Cylinder` are positioned there.

This completes the Lego block which would now be displayed or exported as a STL or STEP file.

.. image:: tutorial_step11.svg
  :align: center
