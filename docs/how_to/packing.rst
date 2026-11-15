.. _packing:

############################
Arranging parts for printing
############################

Parts are usually designed one at a time, each at or near the origin.
Shown or exported together they lie on top of each other.
:func:`~pack.pack` spreads a set of shapes out on a plane so that none
overlaps another, which is what a print bed or a parts overview wants.

.. literalinclude:: /how_to/pack_demo.py
    :language: build123d
    :start-after: [initial space]
    :end-before: [initial space]

.. image:: /how_to/assets/assemblies/pack_demo_initial_state.svg
    :align: center

*******************
Spread them out
*******************

.. literalinclude:: /how_to/pack_demo.py
    :language: build123d
    :start-after: [pack 2D]
    :end-before: [pack 2D]

.. image:: /how_to/assets/assemblies/pack_demo_packed_xy.svg
    :align: center

``pack`` returns moved copies of the shapes, in a compact, roughly square
layout, and leaves the originals where they were. It works from each
shape's bounding box, and ``padding`` is the gap it leaves between one
box and the next. Each shape keeps its own height:
the boxes here still sit at different levels in Z.

*************************
Stand them on the bed
*************************

.. literalinclude:: /how_to/pack_demo.py
    :language: build123d
    :start-after: [pack and align_z]
    :end-before: [pack and align_z]

.. image:: /how_to/assets/assemblies/pack_demo_packed_z.svg
    :align: center

``align_z=True`` also moves each shape so that its lowest point is at
``Z = 0``. That is the setting for a print plate: every part starts on the
bed, and where it does so is decided here and not left to the slicer.

***********************
Check that they fit
***********************

Put the result into a ``Compound`` and its bounding box is the space the
layout needs:

.. literalinclude:: /how_to/pack_demo.py
    :language: build123d
    :start-after: [bounding box]
    :end-before: [bounding box]

************
See also
************

* :func:`~pack.pack` in the operations reference.
* :ref:`import_export` covers saving the arranged parts.
