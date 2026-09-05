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

.. autofunction:: operations_sheet.unfold
    :noindex:
