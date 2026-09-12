.. _build_sheet:

##########
BuildSheet
##########

The ``BuildSheet`` context is used to create sheet metal parts: parts of
constant material thickness formed by folding a flat sheet. While the context
is active it constructs a connected reference ``Shell`` of planar and
cylindrical faces, and the sheet metal operations fold, cut and relieve that
shell. When nested in ``BuildPart``, the completed shell and its parameters
become pending input for :func:`~operations_part.thicken`.

This page describes the builder itself: what it takes in, what it does with
objects drawn inside it, and what it produces. The operations, the concepts
behind them and a tutorial are under :ref:`Sheet Metal <sheet_metal>`.

.. image:: assets/sheet_metal_box.png
    :align: center

.. code-block:: build123d

    with BuildPart() as tray_part:
        with BuildSheet(thickness=1, bend_radius=2) as tray:
            with BuildSketch():
                Rectangle(100, 60)
            flange(tray.rims(), length=15, gaps=3.1)
        thicken()

**********
Parameters
**********

``BuildSheet`` takes the material parameters once, and every operation inside
it uses them: ``thickness``, the default inside ``bend_radius``, the
``k_factor`` and the ``sheet_surface`` the shell represents. What each means
is under :ref:`sheet parameters <sheet_metal_parameters>`. Operations inside
the context must not be given ``sheet_parameters`` of their own.

**************
Sheet material
**************

Sheet material arrives as faces. A nested ``BuildSketch`` publishes its closed
regions into the sheet as planar faces, and ``Mode.SUBTRACT`` regions cut
holes and notches. A sketch object written directly inside ``BuildSheet`` is
never material: ``Rectangle(100, 60)`` on its own in the sheet context is
refused with ``Mode.ADD``, because a sheet is not assembled from 2D pieces the
way a sketch is. Plain shapes built before the ``BuildSheet`` block come in
with :func:`~operations_generic.insert`, which accepts faces, sketches, shells
and other ``BuildSheet`` builders, with optional rotation and placement.
Inserted geometry must sew into the current connected shell. Solids and Parts
are not accepted as sheet material, because ``BuildSheet`` does not
reverse-engineer a reference surface from a solid.

Every operation sews and validates the shell before replacing the previous
result, so selectors always work with the current surface, and a selection
made before an operation does not survive it, as described under
:ref:`selection lifetime <sheet_selection_lifetime>`.

*******
Cutters
*******

A sketch object written directly inside the ``BuildSheet`` context is not
material. With ``Mode.SUBTRACT`` it trims the sheet face it lies on, with
``Mode.PRIVATE`` it is simply built where it is for a later ``insert``, and
with ``Mode.ADD`` it is refused, since a sheet is never drawn from 2D pieces
the way a sketch is. A solid or Part in ``Mode.SUBTRACT`` cuts every face it
passes through, which is how a cutout crosses a bend. Both are covered under
:ref:`holes and cutouts <sheet_metal_cutouts>`.

*********************
Surface modifications
*********************

The general :func:`~operations_generic.chamfer` and
:func:`~operations_generic.fillet` operations modify vertices on the free
boundary of planar sheet faces. Vertices shared with another face, including
bend junctions, are rejected because modifying only one supporting face would
break the sewn shell.

:func:`~operations_generic.mirror` can add or replace faces, sketches and
shells. Mirrored face orientations are corrected automatically to preserve the
material-side normal convention, and the result must still sew into one
connected shell.

:func:`~operations_generic.split` divides selected sheet faces with a plane,
face or shell and resews the retained result. The seam a split leaves is a
fold line, which is how a blank gets a line for :ref:`bend <sheet_metal_bend>`
to fold along. ``BuildSheet`` splitting supports ``Mode.REPLACE`` and
``Mode.PRIVATE``.

*********
Selectors
*********

Besides the ``faces()``, ``edges()`` and ``vertices()`` every builder has,
``BuildSheet`` knows what a sheet is made of: ``flats()``, ``bends()``,
``rims()`` and ``fold_lines()``, each taking the usual ``Select`` argument.
They are described under :ref:`flats, bends, rims, fold lines
<sheet_metal_topology>`.

*******
Results
*******

``tray.sheet`` is the placed reference ``Shell`` and ``tray.sheet_local`` is
its local-coordinate counterpart; ``tray.sheet_parameters`` are the
parameters it was built with. There is no ``part``: a sheet is a surface
until :ref:`thicken <sheet_metal_thicken>` gives it material, and
:ref:`unfold <sheet_metal_unfold>` develops the same surface into the flat
pattern.

*********
Reference
*********

.. py:module:: build_sheet

.. autoclass:: BuildSheet
    :members:
