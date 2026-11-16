.. _why_build123d:

##############
Why build123d
##############

    "I made 5,127 prototypes of my vacuum before I got it right. There were
    5,126 failures. But I learned from each one."

    -- James Dyson

Design is iteration. Requirements change, and some things are only learned
by making the part. A CAD system is therefore judged less by how quickly it
produces the first version of a design than by how well it copes with the
second, the tenth and the fiftieth.

Software developers have the same problem, at a larger scale, and have spent
decades on tools for it: ways to hide complexity behind a simple interface,
to record every change and who made it, to review a change before it is
accepted, and to check automatically that a change has not broken anything.
build123d exists to bring those tools to the design of physical objects. A
build123d model is a Python program, and everything that works on programs
works on it.

**************
An example
**************

.. image:: /explanation/assets/why_build123d/bearing_unit.png
    :align: center
    :width: 60%
    :alt: An oval flanged bearing housing with a bearing pressed into it and a cap screw at each end

This is a flanged bearing unit: a cast housing with a bearing pressed into
its seat, and a lug at each end with a screw to bolt it to a machine. The
sides of the housing lean slightly so that it will come out of the mould,
and its edges are rounded as a casting's are. This is the whole of the
program that makes it:

.. code-block:: build123d

    import copy

    from bd_warehouse.bearing import PressFitHole, SingleRowAngularContactBallBearing
    from bd_warehouse.fastener import ClearanceHole, SocketHeadCapScrew
    from build123d import *
    from ocp_vscode import show

    bearing = SingleRowAngularContactBallBearing("M17-47-14")
    screw = SocketHeadCapScrew("M10-1.5", length=30 * MM, simple=False)

    A, A1, Db2, H, J = 26, 11, 57, 98.5, 76.5
    with BuildPart() as oval_flanged_bearing_unit:
        with BuildSketch() as plan:
            housing = Circle(Db2 / 2)
            with GridLocations(J, 0, 2, 1) as bolt_centers:
                Circle((H - J) / 2)
            make_hull()
        extrude(amount=A1)
        extrude(housing, amount=A)
        drafted_faces = oval_flanged_bearing_unit.faces().filter_by(Axis.Z, reverse=True)
        draft(drafted_faces, Plane.XY, 4)
        fillet(oval_flanged_bearing_unit.edges(), 1)
        with Locations(oval_flanged_bearing_unit.faces().sort_by(Axis.Z)[-1]):
            PressFitHole(bearing)
        with Locations(Pos(Z=A1)):
            with Locations(*bolt_centers):
                ClearanceHole(screw, counter_sunk=False)

    oval_flanged_bearing_unit.part.color = Color(0x4C6377)

    # Create an assembly of all the positioned parts
    oval_flanged_bearing_unit_assembly = Compound(
        children=[oval_flanged_bearing_unit.part, bearing.moved(bearing.hole_locations[0])]
        + [copy.copy(screw).moved(l) for l in screw.hole_locations]
    )
    show(oval_flanged_bearing_unit_assembly)

The bearing and the screws come from bd_warehouse, a library of standard
parts described below, which has to be installed for this to run. A version
of the housing that needs only build123d is among the
:ref:`examples <examples-cast_bearing_unit>`.

The rest of this page uses this one part to show what follows from a
design being a program.

************************************
A design is described, not drawn
************************************

The program for the housing reads much as one would describe the part
aloud. Draw a circle for the body and a smaller one at each bolt centre,
and wrap an outline round them. Extrude it to make the flange, and the
circle alone to make the body. Lean the sides. Round the edges. Make a
press-fit hole for the bearing, and a clearance hole for a screw at each
bolt centre.

Its dimensions are a handful of names at the top: the bolt spacing, the
overall length, the diameter and height of the body. Everything else is
worked out from them. The lugs are placed from the bolt spacing, so
changing one number moves both lugs, their holes and the outline that
wraps them. The change request that always arrives is then a new number,
not a new drawing, and a whole family of housings in different sizes is
the same program run with different values.

******************************
Parts carry their own data
******************************

A housing like this exists for the sake of two other parts, a bearing and
the screws that hold it down, and most of its critical dimensions belong
to them. The seat is the diameter of the bearing, less a little for the
press fit, and as deep as the bearing is wide. The bolt holes are the
diameter of the screws, plus a little for clearance.

In a drawing those are numbers typed into the housing. When the load on
the machine changes and a larger bearing is chosen, or the bearing comes
from another maker, someone has to find each of them and retype it, and
may miss one.

In a program the bearing and the screw can be objects that carry their
own dimensions, and the housing can ask them. Programmers call this
*encapsulation*: the knowledge lives with the thing it is about. That is
how the bearing unit is written. Its program names a bearing and a screw
by their designations and contains no diameter for the seat or the bolt
holes. It says only that there is a press-fit hole for *this bearing* and
a clearance hole for *this screw*, and when either is changed its hole
follows.

***************************************
bd_warehouse: parts with attributes
***************************************

`bd_warehouse <https://bd-warehouse.readthedocs.io/en/latest/index.html>`_
is build123d's companion library of standard parts, and it is that idea
carried through. It has screws, nuts and washers to the common standards,
ball and roller bearings, bushings, pipes and flanges, gears, sprockets,
threads, O-rings, retaining rings and shaft keys.

A part in it is not a file to download. It is made on demand from its
designation, the size of a screw or the catalogue number of a bearing, and
its dimensions come from tables of the published standard. The part that
results is real geometry, exact to those figures, and it keeps the figures
with it: its diameters, its lengths, and the sizes of hole that the standard
gives for it.

That last point is what changes how a design is written. The holes are part
of the library too, and each takes the part it is for. A clearance hole is
given the screw and makes itself the right size for it, a tap hole
likewise, and a press-fit hole is given the bearing and an interference.
The design never states a hole diameter, so there is none to get wrong and
none to update. The part records where its holes were made, and copies of
the screw or bearing can then be placed at exactly those places to build
the assembly.

So a design that uses bd_warehouse says what it is fastened with and what
it carries, and the sizes follow. The bearing and the screws in the picture
are bd_warehouse parts, sitting in holes that were made from them. Change
the screws from one standard to another, or the bearing to the next size
up, and every hole and seat that depends on it is remade to suit.

**********************
A change is a diff
**********************

When a design is a drawing, reviewing a change means putting two drawings
side by side and looking for the difference. When it is text, the change
*is* the difference. Widening the bolt spacing of the housing is one
altered line, and a reviewer is shown that line, before and after, and
nothing else.

A version control system such as Git records every such change with its
author, its date and its reason, and can return to any earlier state.
Several people can work on one design at once and have their work merged.
A proposed change can be reviewed and discussed before it is accepted. All
of this is ordinary practice for software, and it comes with build123d
for free because a model is a text file.

**************************
A design can be tested
**************************

A design has rules it must keep. For the bearing unit one would be a
minimum thickness of metal between the bearing's seat and the outside of
the body; another, that the heads of the screws clear the body. Usually
such rules live in the designer's head or in a checklist.

In code a rule can be written down once, as a test that measures the
model and compares the result with the limit, and it is then checked
every time the design changes. Fit a larger bearing to the same housing
and the wall becomes too thin: the test fails and says so, at once, and
nobody had to notice.

Tests like this are run automatically, by the same tools that test
software, whenever a change is proposed. They are what make it safe to
change a design that someone else wrote.

*************************
The geometry is exact
*************************

build123d is built on the Open Cascade kernel, the same kind of *boundary
representation* (BREP) modeller that commercial CAD systems use. The seat
in the housing is a true cylinder, not a ring of flat facets. That is why
a press fit can be specified to a few hundredths of a millimetre, why a
part can be asked for its faces and edges, and why models go to other CAD
systems as STEP files without loss. Triangles appear only on export to a
mesh format for printing or display.

****************
It is Python
****************

A build123d model is ordinary Python, so the whole language is there:
loops, functions, classes, and an editor with completion and a debugger
that can step through a design as it is built.

So is everything else written in Python. A dimension can come from a
calculation in NumPy, an equation solved by SymPy, a spreadsheet, a
database or a web service. Nothing has to be re-entered by hand, and no
separate scripting language has to be learned.

*********************
It is open source
*********************

build123d is free to use and its source is open, under the Apache 2.0
licence. Anyone can read how an operation works, fix it, extend it, or
build a product on it. A design made with it is never held by a file
format that only one vendor's program can open, and it will still build
when a subscription has lapsed.

***********************
Where it comes from
***********************

build123d is derived from portions of
`CadQuery <https://cadquery.readthedocs.io/en/latest/index.html>`_, but is
extensively refactored and restructured into an independent framework over
`Open Cascade <https://dev.opencascade.org/>`_.

********************
Where to go next
********************

* :ref:`getting_started` installs build123d and makes a first part.
* :ref:`tutorials` teach it step by step, starting with
  :ref:`tutorial_sketch_then_extrude`.
* :ref:`examples` has the bearing unit and many other finished models,
  with their code.
* :ref:`coming_from_openscad` is for those arriving from another code-CAD
  system.
