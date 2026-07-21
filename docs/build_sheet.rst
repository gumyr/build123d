##########
BuildSheet
##########

The ``BuildSheet`` context is used to create sheet metal parts — parts of
constant material thickness formed by folding a flat sheet.

.. image:: assets/sheet_metal_box.png
    :align: center

.. code-block:: python

    with BuildSheet(thickness=1, bend_radius=2) as tray:
        with BuildSketch():
            Rectangle(100, 60)
        bottom_edges = tray.faces().sort_by(Axis.Z)[0].edges().filter_by(GeomType.LINE)
        flange(bottom_edges, length=15, gap1=3.1, gap2=3.1)

*****************
Base sheet
*****************

Closed sketch regions exiting into ``BuildSheet`` are automatically padded
by ``thickness`` — no explicit ``extrude`` is needed. ``Mode.SUBTRACT``
regions cut holes. For open profiles (brake-formed parts) use
:func:`~operations_part.make_brake_formed` with a ``BuildLine`` profile;
note it takes an explicit ``thickness`` and requires bend arcs to be drawn
into the profile (e.g. with ``FilletPolyline``).

*****************
Folding
*****************

:func:`~operations_sheet.flange` folds a wall up from selected sheet
edges; :func:`~operations_sheet.hem` folds an edge back onto itself
(flat, open, teardrop or rolled). Both fold **away from the sheet face**
the selected edge borders: select a bottom-face edge to fold upward.

*****************
Bend topology
*****************

Sheet metal parts keep every bend's cylindrical faces and their flat
"fan" shaped end-caps as separate faces — they are deliberately never
unified. This preserved topology is what future unfolding tools use to
detect bends and compute flat patterns (with the ``k_factor`` stored on
the builder). For this reason **do not call** ``clean()`` on a sheet
metal part.

*****************
Reference
*****************

.. py:module:: build_sheet

.. autoclass:: BuildSheet
    :members:

.. autofunction:: operations_sheet.flange

.. autofunction:: operations_sheet.hem
