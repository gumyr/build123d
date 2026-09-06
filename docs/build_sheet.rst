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

Sketch objects belong to ``BuildSketch``, so ``Rectangle(100, 60)`` written
directly inside a ``BuildSheet`` context raises, exactly as it would inside
``BuildPart``. Build the region in a nested ``BuildSketch`` and let it publish
into the sheet, or construct plain shapes before the ``BuildSheet`` block and
bring them in with :func:`~operations_generic.insert`.

That nesting is what makes hole patterns convenient: a ``BuildSketch`` on the
plane of a selected face, in ``Mode.SUBTRACT``, cuts the pattern into that face
alone. The face can only be selected from inside the context, which is exactly
where the nested sketch lives:

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        flange(tray.edges().filter_by(GeomType.LINE).sort_by(Axis.Y)[-1], length=20)

        wall = tray.faces().filter_by(GeomType.PLANE).sort_by(Axis.Z)[-1]
        with BuildSketch(Plane(wall), mode=Mode.SUBTRACT):
            with GridLocations(20, 8, 3, 2):
                Circle(2)

Cutting this way is limited to the face the sketch plane matches. A cutout that
has to cross a bend needs a solid cutter, described below.

Reusable surface components can be added with :func:`~operations_generic.insert`.
It accepts faces, sketches, shells, and compatible ``BuildSheet`` builders,
with optional 3D rotation and location placement. Inserted geometry must sew
into the current connected shell. Solids and Parts are not accepted as sheet
material because ``BuildSheet`` does not reverse-engineer reference surfaces
from materialized objects.

A Solid or Part is accepted as a *cutter* with ``Mode.SUBTRACT``. Unlike a
face cutter, which only removes area from a sheet face it is coplanar with, a
solid cuts every face it passes through, so a cutout may cross a bend:

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

*****************
Folding
*****************

:func:`~operations_sheet.flange` adds a cylindrical bend and planar wall to
selected free shell edges. :func:`~operations_sheet.hem` terminates an edge
with a flat, open, teardrop, or rolled profile. Positive angles fold toward the
normal of the face bordering the selected edge.

:func:`~operations_sheet.miter` angles a planar flange side without changing
the cylindrical bend. It takes vertices at the ends of a free flange rim;
positive angles trim the flange and negative angles extend it.

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
sheet shared by two coplanar faces, and the face named as ``fixed_face`` is
the one that stays put - everything on the far side of the line swings through
the angle, carrying whatever is attached to it. Naming a face rather than a
side or a handedness is what keeps the result predictable: nothing about the
fold is inferred from which piece happens to be larger.

The bend takes a strip of the sheet with it as it rolls up, as wide as its own
arc on the reference surface, so the sheet keeps the length it was drawn with.
``BendPosition`` says where that strip sits relative to the fold line:
``BEND_OUTSIDE`` puts all of it past the line and leaves ``fixed_face``
untouched, ``CENTER`` straddles the line, and the two mould line positions put
the corner of the formed part on it - the inside corner for
``MATERIAL_INSIDE`` and the outside corner for ``MATERIAL_OUTSIDE``. The mould
lines are where the extended faces of the formed part meet, so they are
undefined for a 180 degree fold, where those faces never do.

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

``ROUND`` takes a ``radius``, ``SQUARE`` a ``size`` and ``OBROUND`` a
``length`` and a ``width``. ``CONSTANT_WIDTH`` takes only a ``depth``: its
width is measured from the part, continuing the gap the two flanges already
leave, so the separation carries on unchanged through the corner instead of
pinching. That makes it meaningful only where two flanges meet, and it is the
one shape ``bend_relief`` does not accept.

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
        bend_relief(tray.faces().filter_by(GeomType.CYLINDER), ReliefType.SQUARE)

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
overlap. That corner belongs to ``corner_relief``, which opens it in a single
cut, and ``bend_relief`` reports the collision rather than cutting.

``ROUND``, ``SQUARE`` and ``OBROUND`` are cut in the flat blank before the
part is formed, so they are trimmed in the developed pattern and keep their
shape there rather than on the folded part. ``CONSTANT_WIDTH`` is the
exception: it is defined by the formed part, so it is cut in 3D.

*****************
Bend topology
*****************

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

.. autofunction:: operations_sheet.corner_relief
    :noindex:

.. autofunction:: operations_sheet.bend_relief
    :noindex:

.. autofunction:: operations_sheet.unfold
    :noindex:
