####################
Sheet Metal Tutorial
####################

This tutorial builds a small open-top sheet metal box with hemmed rims,
introducing the ``BuildSheet`` builder and the sheet metal operations
``flange`` and ``hem``.

**********************
Step 1: The base sheet
**********************

Sheet metal parts start from a flat base. Inside ``BuildSheet``, a closed
sketch region automatically becomes a sheet of the builder's thickness:

.. code-block:: python

    from build123d import *

    with BuildSheet(thickness=1, bend_radius=2) as box:
        with BuildSketch():
            Rectangle(100, 60)

**********************
Step 2: Fold the walls
**********************

``flange`` folds a wall from selected edges. Folds go away from the face
the edge was selected on, so we select the bottom face's edges to fold
upward. The gaps keep neighbouring walls from intersecting at the corners:

.. code-block:: python

        bottom = box.faces().sort_by(Axis.Z)[0]
        flange(
            bottom.edges().filter_by(GeomType.LINE),
            length=20,
            gap1=3.1,
            gap2=3.1,
        )

********************
Step 3: Hem the rims
********************

Raw sheet edges are sharp; a hem folds them back for a safe rim. The two
long walls each contribute two faces whose normal points along ``Axis.Y``
(their inner and outer surfaces); sorting those by ``Axis.Y`` and taking
the outermost one on each side selects the two long walls, and the top
edge of each (sorted by ``Axis.Z``) is the rim to hem:

.. code-block:: python

        long_walls = box.faces().filter_by(Axis.Y).sort_by(Axis.Y)
        rims = [
            long_walls[0].edges().sort_by(Axis.Z)[-1],
            long_walls[-1].edges().sort_by(Axis.Z)[-1],
        ]
        hem(rims, hem_type=HemType.OPEN, width=6, opening=2)

*****************
The result
*****************

``box.sheet`` is a regular ``Part`` — export it, measure it, combine it.
Its bend faces are intentionally kept separate (never unified), which is
what future flat-pattern unfolding needs — so don't ``clean()`` it.
