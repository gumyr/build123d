.. _tips:

####
Tips
####

There are many ways to make a given part in build123d. These are the habits
that experience has shown make designs quicker to write, more likely to
build, and easier to change. For answers to particular questions see
:ref:`faq`.

*************************************
Sketch in 2D before working in 3D
*************************************

Start a part as a sketch and turn the sketch into a solid, in preference to
carving it out of blocks. A 2D outline is simpler than the solid it becomes,
and operations on solids are slower and more likely to fail, so the more of
the shape that is settled in the sketch, the better.

.. code-block:: build123d

    with BuildPart() as my_part:
        with BuildSketch() as part_profile:
            ...
        extrude(amount=some_distance)
        ...

The sketch can hold many objects, combined and rounded before it is
extruded. :ref:`sketching` and :ref:`building_parts` cover both halves, and
:ref:`coming_from_openscad` is for anyone used to working the other way.

*****************************************
Leave fillets and chamfers until last
*****************************************

Chamfers and fillets can add complexity to a design by transforming simple vertices
or edges into arcs or non-planar faces. This can significantly increase the complexity
of the design. To avoid unnecessary processing costs and potential errors caused by a
needlessly complicated design, it's recommended to perform these operations towards
the end of the object's design. This is especially true for 3D shapes, as it is
sometimes necessary to fillet or chamfer in the 2D design phase. Luckily, these
2D fillets and chamfers are less likely to fail than their 3D counterparts.

:ref:`tutorial_selecting_and_finishing` shows the order in practice.

******************
Use parameters
******************

One of the most powerful features of build123d is the ability to design fully
parameterized parts. While it may be faster to use a GUI CAD package for the
initial iteration of a part, subsequent iterations can prove frustratingly
difficult. By using variables for critical dimensions and deriving other dimensions
from these key variables, not only can a single part be created, but a whole set
of parts can be readily available. When inevitable change requests arise, a simple
parameter adjustment may be all that's required to make necessary modifications.

:ref:`tutorial_parametric_part` builds a part this way.

***********************************************
Select from a face, not from the whole part
***********************************************

A feature is often easier to find through something larger. To get the rims
of the holes in the top of a plate, select the top face first and then the
circular edges of that face:

.. code-block:: build123d

    top_face = plate.faces().sort_by(Axis.Z)[-1]
    hole_edges = top_face.edges().filter_by(GeomType.CIRCLE)

:ref:`selecting_features` has a table of common selections.

*****************************************
Use shallow copies for repeated parts
*****************************************

Fasteners, bearings and chain links can appear tens or hundreds of times in
a design. Make the repeats with ``copy.copy``, which shares the geometry of
the original, and the model stays small and quick to save. Remember that the
copies really are the same geometry: change one and all of them change.
:ref:`Use one part many times <shallow_copy>` has the details and the
numbers.

**************************************
Avoid shapes that touch themselves
**************************************

Avoid creating objects that intersect themselves - even if at a single vertex - as these topologies
will almost certainly be invalid (even if :meth:`~topology.Shape.is_valid` reports a ``True`` value).
An example of where this may arise is with the thread of a screw (or any helical shape) where after
one complete revolution the part may contact itself. One is likely be more successful if the part
is split into multiple sections - say 180° of a helix - which are then stored in an assembly.

************************************************
When an operation will not work, try another
************************************************

Unfortunately, it's a reality that not all parts described using build123d can be
successfully constructed by the underlying CAD core. Designers may have to
explore different design approaches to get the OpenCascade CAD core to successfully
build the target object. For instance, if a multi-section :func:`~operations_generic.sweep`
operation fails, a :func:`~operations_part.loft` operation may be a viable alternative
in certain situations. It's crucial to remember that CAD is a complex field and
patience may be required to achieve the desired results.
