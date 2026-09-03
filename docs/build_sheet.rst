##########
BuildSheet
##########

The ``BuildSheet`` context is used to create sheet metal parts — parts of
constant material thickness formed by folding a flat sheet. While the context
is active, it constructs a connected reference ``Shell`` from planar and
cylindrical faces. On exit, that shell is thickened into a ``Part``.

.. image:: assets/sheet_metal_box.png
    :align: center

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        bottom_edges = tray.edges().filter_by(GeomType.LINE)
        flange(bottom_edges, length=15, gaps=3.1)

*****************
Base sheet
*****************

Closed sketch regions exiting into ``BuildSheet`` become planar faces in the
reference shell. ``Mode.SUBTRACT`` regions cut holes and notches. Every
operation sews and validates the shell before replacing the previous result,
so selectors always work with current surface geometry.

Reusable surface components can be added with :func:`~operations_generic.insert`.
It accepts faces, sketches, shells, and compatible ``BuildSheet`` builders,
with optional 3D rotation and location placement. Inserted geometry must sew
into the current connected shell. Solids and Parts are not accepted because
``BuildSheet`` does not reverse-engineer reference surfaces from materialized
objects.

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
``BuildSheet`` converts it to the radius of the chosen reference surface using
the thickness, bend direction, and ``k_factor``.

In Algebra mode these three values are passed together as
``SheetMetalParameters``:

.. code-block:: python

    parameters = SheetMetalParameters(
        thickness=1,
        k_factor=0.4,
        sheet_surface=SheetSurface.NEUTRAL,
    )
    reference_sheet = Rectangle(100, 60)
    reference_shell = flange(
        reference_sheet.edges()[0],
        length=20,
        radius=2,
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

``tray.part`` is the placed, thickened ``Part`` created on context exit;
``tray.part_local`` is the same result in local construction coordinates. A
``BuildSheet`` nested in ``BuildPart`` publishes this Part to its parent.

*****************
Reference
*****************

.. py:module:: build_sheet

.. autoclass:: BuildSheet
    :members:

.. autoclass:: SheetMetalParameters
    :members:

.. autofunction:: operations_sheet.flange

.. autofunction:: operations_sheet.hem

.. autofunction:: operations_sheet.miter
