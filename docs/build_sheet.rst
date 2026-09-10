##########
BuildSheet
##########

The ``BuildSheet`` context is used to create sheet metal parts — parts of
constant material thickness formed by folding a flat sheet. While the context
is active, it constructs a connected reference ``Shell`` from planar and
cylindrical faces. When nested in ``BuildPart``, the completed shell and its
parameters become pending input for :func:`~operations_part.thicken`.

.. image:: assets/sheet_metal_box.png
    :align: center

.. code-block:: python

    with BuildPart() as tray_part:
        with BuildSheet(thickness=1, bend_radius=2) as tray:
            with BuildSketch():
                Rectangle(100, 60)
            bottom_edges = tray.edges().filter_by(GeomType.LINE)
            flange(bottom_edges, length=15, gaps=3.1)
        thicken()

*****************
Base sheet
*****************

Closed sketch regions exiting into ``BuildSheet`` become planar faces in the
reference shell. ``Mode.SUBTRACT`` regions cut holes and notches. Every
operation sews and validates the shell before replacing the previous result,
so selectors always work with current surface geometry.

Sheet material is drawn in a nested ``BuildSketch``, which publishes its faces
into the sheet; plain shapes built before the ``BuildSheet`` block come in with
:func:`~operations_generic.insert`. A sketch object written directly inside the
``BuildSheet`` context - ``Rectangle(100, 60)`` on its own - is refused with
``Mode.ADD``, since a sheet is never drawn from 2D pieces the way a sketch is.
It is taken as a *cutter*: with ``Mode.SUBTRACT`` it trims the sheet face it
lies on, and with ``Mode.PRIVATE`` it is simply built where it is used, for a
later ``insert``. Where it lies is where it cuts, so a circle drawn on the
default plane trims the base and one placed on a wall's plane trims the wall:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges().filter_by(GeomType.LINE).sort_by(Axis.X)[-1], length=20)

        with GridLocations(30, 30, 2, 2):
            Circle(3, mode=Mode.SUBTRACT)  # holes in the base
        with Locations(Plane(tray.flats().sort_by(Axis.Z)[-1])):
            Circle(3, mode=Mode.SUBTRACT)  # a hole in the wall

A nested ``BuildSketch`` in ``Mode.SUBTRACT`` cuts the same way, and is what
makes hole patterns on one face convenient: a ``BuildSketch`` on the plane of a
selected face cuts the pattern into that face alone, and the face can only be
selected from inside the context, which is exactly where the nested sketch
lives:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1], length=20)

        wall = tray.flats().sort_by(Axis.Z)[-1]
        with BuildSketch(Plane(wall), mode=Mode.SUBTRACT):
            with GridLocations(20, 8, 3, 2):
                Circle(2)

Cutting this way is limited to the face the cutter lies on, and a face lying on
no sheet face is refused rather than ignored. A cutout that has to cross a bend
needs a solid cutter, described below.

Reusable surface components can be added with :func:`~operations_generic.insert`.
It accepts faces, sketches, shells, and compatible ``BuildSheet`` builders,
with optional 3D rotation and location placement. Inserted geometry must sew
into the current connected shell. Solids and Parts are not accepted as sheet
material because ``BuildSheet`` does not reverse-engineer reference surfaces
from materialized objects.

A Solid or Part is accepted as a *cutter* with ``Mode.SUBTRACT``. Unlike a
face cutter, which only removes area from a sheet face it is coplanar with, a
solid cuts every face it passes through, so a cutout may cross a bend - the
*drawn cutout*, *normal cut* or *cut across a bend* of sheet metal packages:

.. code-block:: python

    punch = Pos(0, 0, -5) * Cylinder(4, 20)

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1], length=20)
        insert(punch, mode=Mode.SUBTRACT)

Part objects are cutters too, so holes can be placed with the usual location
contexts:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        with GridLocations(50, 50, 2, 2):
            Hole(5)

Trimming changes the boundary of a face without changing its supporting
surface, so the sheet keeps its planar and cylindrical geometry. Three things
are worth noting:

* The cutter must reach the *reference* surface, which for
  ``SheetSurface.INSIDE`` or ``SheetSurface.OUTSIDE`` is one side of the
  material rather than its middle. A cutter placed against the opposite
  material face will miss the shell entirely.
* A cut that separates the sheet into disconnected pieces is rejected, since
  the reference shell must stay connected.
* A cutter removes the area it covers where it crosses the reference surface.
  Shaped cutters such as ``CounterSinkHole`` therefore leave a plain opening
  of that size rather than forming the material.

``BuildSheet`` is not the context for
:func:`~operations_part.make_brake_formed`; that remains an independent
``BuildPart`` operation.

*********************
Surface modifications
*********************

The general :func:`~operations_generic.chamfer` and
:func:`~operations_generic.fillet` operations modify vertices on the free
boundary of planar sheet faces. Vertices shared with another face, including
bend junctions, are rejected because modifying only one supporting face would
break the sewn shell.

:func:`~operations_generic.mirror` can add or replace faces, sketches, and
shells. Mirrored face orientations are corrected automatically to preserve the
material-side normal convention. The result must still sew into one connected
shell.

:func:`~operations_generic.split` divides selected sheet faces with a plane,
face, or shell and atomically resews the retained result. BuildSheet splitting
supports ``Mode.REPLACE`` and ``Mode.PRIVATE``.

*****************
Reference surface
*****************

``sheet_surface`` specifies which continuous material surface the shell
represents: ``SheetSurface.INSIDE``, ``OUTSIDE``, ``MID``, or ``NEUTRAL``.
The default is ``INSIDE``. Face normals point from the outside material side
toward the designated inside side; the initial XY face therefore points in
``+Z``. Positive flange angles fold toward that normal and negative angles
fold away from it.

The bend ``radius`` is always the physical radius on the locally concave side.
``SheetMetalParameters.bend_radius`` provides the default used when an operation
doesn't specify its own radius. It defaults to the sheet thickness. The radius
is converted to the chosen reference surface using the thickness, bend
direction, and ``k_factor``.

``k_factor`` places the neutral axis - the layer of the sheet whose length a
bend leaves unchanged - as a fraction of the thickness from the *inside* of
the bend, whichever face of the sheet that is. So the length of flat a bend
consumes, its bend allowance, is the same whichever reference surface the shell
is drawn at and whichever way the sheet is bent; only the radius the bend is
drawn with changes. The ``NEUTRAL`` reference surface coincides with the
neutral axis for bends toward the sheet's normal, and sits ``(1 - k_factor)``
of the thickness from the inside of a bend the other way.

In Algebra mode these values are passed together as
``SheetMetalParameters``:

.. code-block:: python

    parameters = SheetMetalParameters(
        thickness=1,
        bend_radius=2,
        k_factor=0.4,
        sheet_surface=SheetSurface.NEUTRAL,
    )
    reference_sheet = Rectangle(100, 60)
    reference_shell = flange(
        reference_sheet.edges()[0],
        length=20,
        sheet_parameters=parameters,
    )

Inside a ``BuildSheet`` context, operations obtain ``sheet_parameters`` from
the builder automatically and the argument must be omitted.

The sheet itself is a ``Shell``, and what makes a shell a sheet - flats and
bends, meaning planar and cylindrical faces, sewn into one connected manifold
shell - is enforced by :meth:`~topology.Shell.make_sheet`. It is what
``BuildSheet`` calls to take faces in, and the way to assemble a sheet from
faces in Algebra mode; ``merge_coplanar`` joins touching coplanar pieces, as
the builder does for material arriving in pieces, while by default a seam
between coplanar faces is kept because on a sheet it may be a fold line.
:meth:`~topology.Shell.cut_sheet` trims a sheet with solids, which cut every
face they pass through, or with faces coplanar with one of its flats.

*****************
Folding
*****************

:func:`~operations_sheet.flange` adds a cylindrical bend and planar wall to
selected free shell edges. :func:`~operations_sheet.hem` terminates an edge
with a flat, open, teardrop, or rolled profile. Positive angles fold toward the
normal of the face bordering the selected edge.

By default the bend starts at the edge and everything the flange adds lies past
it, so a face meant to end at a corner of the part has to be drawn short, to
the bend's tangent line. A drawing dimensions to the sharp corners instead, and
``position`` lets the face be drawn that way: ``BendPosition.MATERIAL_INSIDE``
or ``MATERIAL_OUTSIDE`` sets the bend back onto the face so the inside or
outside corner of the formed part lands on the edge, and ``CENTER`` straddles
it. The strip of the face the bend takes rolls into it, so ``unfold`` gives back
the blank the face was drawn as. Only the bend's own span between the ``gaps``
is taken, and the face beside it keeps its edge as a tab reaching the corner;
where two flanged edges meet, each bend's strip would take material the other
one needs, so the gaps there have to be wider than the setback.

The wall's ``length`` is the flat wall by default, measured from the bend's
tangent line, where a drawing usually gives the overall size to a virtual sharp
- the corner the part would have if it were folded sharp. ``length_mode`` takes
the length the drawing's way, as ``PolarLine`` does with its own ``length_mode``:
``FlangeLength.INNER_SHARP`` measures from the corner the inner faces make and
``OUTER_SHARP`` from the outer one, and the flange works out the wall. With
``position`` placing the other corner on the edge, a part can be modelled from
its drawing dimensions without working back to tangent lines by hand:

.. code-block:: python

    flange(plate.edges().filter_by(Axis.Y), length=65, gaps=30, angle=60,
           position=BendPosition.MATERIAL_OUTSIDE,
           length_mode=FlangeLength.OUTER_SHARP)

:func:`~operations_sheet.miter` angles the side of a flange. It takes vertices
at the ends of a free flange rim; positive angles trim the flange and negative
angles extend it. Two miters that eat past each other meet inside the flange
and leave a triangle, as does a lone one whose cut leaves through the far side.

By default the cut stops where the wall meets its bend. ``through_bend=True``
carries it on to the fold line, which is what a mitered corner is in the flat
pattern: one straight cut across the whole flange to the edge of the blank. The
angle is held in the flat pattern rather than on the reference surface, since
that is where a miter is laid out, so the cut is slightly skewed on the formed
bend by however far the neutral axis lies from the reference surface. A
trimming miter narrows the bend to match the flange and an extending one
widens it. Mitered bends are what let flanges folded into a hole meet at its
corners instead of being held apart by a gap:

.. code-block:: python

    miter(walls.vertices().group_by(Axis.Z)[-1], 45, through_bend=True)

:func:`~operations_sheet.unfold` develops the reference shell into its flat
pattern - the blank the part is cut from. Each bend is developed at its neutral
radius, so the operation needs the sheet parameters and takes them from the
enclosing ``BuildSheet``. The pattern is built on ``Plane.XY``; ``align``
places it within that plane, defaulting to ``Align.NONE`` so it stays
registered with the source sheet, while ``Align.MIN`` corners it on the origin
for nesting or cutting. The underlying :meth:`~topology.Shell.unfold` method
accepts them optionally and falls back to each bend's geometric radius, which
produces a pattern that will not fold back to the requested part; prefer the
operation unless you specifically want the geometric development.

Hem profile parameters are specific to the selected type: ``FLAT`` requires
``width``; ``OPEN`` requires ``width`` and ``opening``; ``TEARDROP`` requires
``width`` and optionally accepts ``radius`` and ``opening``; and ``ROLLED``
accepts ``radius`` and ``roll_angle``. These parameters are keyword-only, and
parameters that do not apply to the selected type are rejected.

:func:`~operations_sheet.bend` folds material the sheet already has, where
``flange`` adds material beyond a free edge. It folds along an edge of the
sheet shared by two coplanar faces. That edge lies between the two, so which
one stays put is the single thing the line cannot say on its own - and the way
it was selected answers it. An edge picked off a face records that face on its
``topo_path``, and ``bend`` takes the innermost face of that route as the side
that holds still - whether the edge came off the face or off one of its wires:

.. code-block:: python

    bend(sheet.flats().sort_by(Axis.X)[-1].fold_lines()[0], angle=90)

Everything on the far side of the line swings through the angle, carrying
whatever is attached to it. An edge whose route never passed through a face -
taken straight off the shell, as ``sheet.edges()`` does - is refused rather
than guessed at, because the topology cannot settle it either: both faces are
equally the edge's own. Selecting the same edge through the face that stays is
the answer, and it is no more work than reaching for the face separately.

The bend takes a strip of the sheet with it as it rolls up, as wide as the bend
allowance - the arc of the neutral axis - so that ``unfold`` gives back the
length the blank was drawn with. Whatever the blank's outline does across that
strip - a taper, a corner round, a notch, a hole - rolls into the bend with it;
the strip need not be the same width at both ends.
``BendPosition`` says where that strip sits relative to the fold line, as it
does for ``flange``: ``BEND_OUTSIDE`` puts all of it past the line and leaves
the fixed face untouched, ``CENTER`` straddles the line, and the two mould line
positions put the corner of the formed part on it - the inside corner for
``MATERIAL_INSIDE`` and the outside corner for ``MATERIAL_OUTSIDE``. The mould
lines are where the extended faces of the formed part meet, so they are
undefined for a 180 degree fold, where those faces never do.

:func:`~operations_sheet.jog` steps a sheet sideways: a bend, a straight run
and a bend back the other way, leaving the far side parallel to where it was.
It takes a fold line the way ``bend`` does, selected through the face that
stays, and moves everything on the far side across by ``offset`` - measured
between the reference surfaces of the two flats, so it is the step between the
same face of the sheet on either side, positive toward the face normal. Given a
free edge instead, as ``flange`` takes one, the jog is a stepped flange running
on for ``length`` beyond the second bend. ``angle`` is how steeply the run
climbs, 90 for a square step; the two bends climb ``(r1 + r2)(1 - cos angle)``
between them and the run makes up the rest, so a jog needs at least that much
offset. Both bends take their allowance of the blank and ``position`` places
the first one on its line as it does for ``bend``, so ``unfold`` gives the
blank back:

.. code-block:: python

    jog(sheet.flats().sort_by(Axis.X)[0].fold_lines()[0], offset=10)

A blank has to carry the fold line as a real edge before it can be folded
along one, which means a shell of coplanar faces rather than a single face.
How such a blank is produced - imported with its outline, or marked on a
sketch - is a separate question from the fold itself.

*****************
Relief
*****************

Relief cuts material away where forming would otherwise fail: where two
flanges would collide as they fold, and where a bend stops inside the sheet
rather than running out to the edge of the blank. Both operations name their
shape with ``ReliefType``, which says what the relief looks like rather than
where it goes - each operation places it.

:func:`~operations_sheet.corner_relief` opens the corner where two bends meet,
so the flanges do not run into each other. It takes corner vertices of a
planar face, each with a bend on both sides of it:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges(), length=20, gaps=3.1)

        base = tray.faces().sort_by(Axis.Z)[0]
        corner_relief(
            base.vertices().group_by(SortBy.DISTANCE)[-1],
            ReliefType.ROUND,
            radius=3,
        )

A corner the sheet wraps around rather than stops at - the corner of a
flanged hole, say - is relieved the same way. There the sheet fills three
quadrants instead of one and both bends unroll into the fourth, each taking
whatever part of the profile lands on it. Mitered through their bends they
meet along a seam there and the cut is divided between them; square-ended
they cover the same ground on the blank, and each is cut where the profile
crosses it.

A relief is laid out on the blank, so that is where it comes out its own shape:
a ``ROUND`` relief is a circle on the flat pattern rather than on the formed
sheet, where the parts crossing a bend read smaller. That is why these
operations need ``sheet_parameters`` - the blank is measured on the neutral
axis, whose position depends on the k factor.

``ROUND`` takes a ``radius``, ``SQUARE`` a ``size`` and ``OBROUND`` a
``length`` and a ``width``. ``CONSTANT_WIDTH`` takes only a ``depth``: its
width is measured from the part, continuing the gap the two flanges already
leave, so the separation carries on unchanged through the corner instead of
pinching. That makes it meaningful only where two flanges meet on a corner the
sheet stops at, and it is the one shape ``bend_relief`` does not accept.

:func:`~operations_sheet.bend_relief` notches the end of a bend that stops
inside the sheet. Such an end leaves a corner where the sheet has to fold on
one side of the fold line and stay flat on the other, which tears when it is
formed; the notch lets the fold line end on a free edge instead. It takes the
cylindrical bend faces themselves and relieves both ends of each, so a
selection acts as a filter - an end that already runs out to the edge of the
blank needs nothing and is left alone:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges().filter_by(Axis.X), length=20, gaps=2)
        bend_relief(tray.bends(), ReliefType.SQUARE)

Sizes left out follow the usual shop rule, measured from the fold line: the
relief reaches the bend radius plus one thickness into the sheet and is one
thickness wide. ``SQUARE`` and ``OBROUND`` take that pair as ``depth`` and
``width`` and cut only into the face beside the bend, differing in whether the
far end is square-cornered or rounded. ``ROUND`` is a hole centred on the end
of the fold line, so it shortens the bend as well as notching the sheet beside
it; its ``radius`` also sets how far it reaches past the bend end, so it
defaults to one thickness rather than to that same reach.

The two operations divide on how many fold lines run through the site: two at
a corner, one at a bend end. Where flange ``gaps`` leave a corner open both
bends stop inside the sheet, so both ends want relief and their notches
overlap - and between them cut the corner of the sheet loose, which
``bend_relief`` reports. That corner belongs to ``corner_relief``, which opens
it in a single cut.

``ROUND``, ``SQUARE`` and ``OBROUND`` are cut in the flat blank before the
part is formed, so they are trimmed in the developed pattern and keep their
shape there rather than on the folded part. ``CONSTANT_WIDTH`` is the
exception: it is defined by the formed part, so it is cut in 3D.

*****************
Bend topology
*****************

A sheet reads as flats joined by bends, and ``tray.bends()`` and
``tray.flats()`` say that directly - the cylindrical and planar faces of the
reference shell. Its edges have names too: ``tray.rims()`` are the free edges
of the flats, what ``flange`` and ``hem`` consume, and ``tray.fold_lines()``
are the straight edges shared by two coplanar flats, where ``bend`` can fold.
All four take the same ``Select`` argument as the other selectors, so
``tray.bends(Select.LAST)`` narrows to the last operation, and ``Shell``
carries the same four for Algebra mode. A flat has ``fold_lines()`` and
``rims()`` of its own, selected through it, which is how a fold line says
which side stays put. A bend's ``length`` runs along its axis, which is the
length of the fold line, so bends sort by the size they look like they are:

.. code-block:: python

    long_bends = tray.bends().sort_by(SortBy.LENGTH)[-2:]


``tray.sheet`` is the placed reference ``Shell`` and ``tray.sheet_local`` is
its local-coordinate counterpart. Cylindrical bend faces remain distinct from
planar regions so future unfolding can use their analytic geometry.

A ``BuildSheet`` nested in ``BuildPart`` publishes the reference shell and its
``SheetMetalParameters`` to ``BuildPart.pending_sheets``. Calling ``thicken()``
without arguments consumes those pending sheets and creates the physical
``Part``. In Algebra mode both values are explicit:

.. code-block:: python

    tray_part = thicken(tray.sheet, sheet_parameters=tray.sheet_parameters)

*****************
Reference
*****************

.. py:module:: build_sheet

.. autoclass:: BuildSheet
    :members:

.. autoclass:: build123d.sheet_utils.SheetMetalParameters
    :members:

.. autofunction:: operations_sheet.flange
    :noindex:

.. autofunction:: operations_sheet.hem
    :noindex:

.. autofunction:: operations_sheet.miter
    :noindex:

.. autofunction:: operations_sheet.bend
    :noindex:

.. autofunction:: operations_sheet.jog
    :noindex:

.. autofunction:: operations_sheet.corner_relief
    :noindex:

.. autofunction:: operations_sheet.bend_relief
    :noindex:

.. autofunction:: operations_sheet.unfold
    :noindex:
