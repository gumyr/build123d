.. _debugging:

#################
Debugging a model
#################

A build123d model is a Python program, so everything that finds a bug in a
program works on it. But the most useful tools are the ones that let you
*see* what the model is doing: watch it being built one line at a time,
and look at what a selection picked before it is used. This guide starts
with those.

Nothing here depends on the mode a model is written in.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - watch the model being built line by line
      - the debugger, with OCP CAD Viewer open
    * - see what a selection picked
      - ``show(part, selection)``
    * - check a selection without a viewer
      - ``len(selection)``, and the type, size and place of each item
    * - check the part is the size it should be
      - ``bounding_box()``, ``volume``, ``len(part.solids())``
    * - check the part is sound
      - ``part.is_valid``, as a first check
    * - see the value of a plane, location or vector
      - ``print``
    * - see what a part is made of
      - ``show_topology()``
    * - see what the builders are doing
      - the ``build123d`` log

The examples use this bracket:

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [bracket]
    :end-before: [bracket]

*******************************
Watch the model being built
*******************************

An editor's debugger can stop a program at any line and run it one line at
a time. With `OCP CAD Viewer <https://github.com/bernhard-42/vscode-ocp-cad-viewer>`_
in Visual Studio Code that becomes a single step through the *design*:
each time the program stops, the viewer shows the model as it stands at
that line.

.. image:: /how_to/assets/debugging_logging/visual_debugging.png
    :align: center
    :alt: Visual Studio Code stopped at a breakpoint in the bracket script, with the half-built bracket shown in OCP CAD Viewer beside the code

Here the program has stopped at line 19, before the second ``mirror`` has
run, and the viewer shows what exists so far: one half of the bracket. The
tree lists every build123d object the program has made, ``bracket``,
``sketch`` and ``profile``, and each can be shown or hidden. Step once and
the other half appears.

To do it:

#. Open the viewer.
#. Click in the margin beside a line to set a *breakpoint*, the red dot.
#. Start the program with **Run > Start Debugging** (``F5``), not with a
   plain run. The status bar shows ``DEBUG`` beside the viewer's port when
   visual debugging is on.
#. When the program stops, step over one line at a time (``F10``) and
   watch the viewer, or continue to the next breakpoint (``F5``).

No ``show`` call is needed: the viewer displays the objects it finds in
the program at each stop. The Variables panel on the left holds every
Python value at that moment, so a wrong dimension can be found there
too.

This is the quickest way to find the line where a model goes wrong.
Instead of reasoning about which step put the hole in the wrong place,
step until it appears. The viewer's own documentation has more on
`visual debugging <https://bernhard-42.github.io/ocp_viewer_docs/viewers/ocp_vscode/visual_debugging/>`_.
Other editors and viewers may offer the same; the idea does not depend
on these two.

*******************************
See what a selection picked
*******************************

Most operations that do the wrong thing were given the wrong features.
A selection is a list, and it can be shown like anything else. Show it
beside the part before it is used:

.. code-block:: build123d

    corners = bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[-1]
    show(bracket, corners)

The selected edges are drawn on the part, and it is plain at once whether
they are the ones intended. When stepping in the debugger this needs no
code at all: ``corners`` is in the viewer's tree as soon as its line has
run.

Without a viewer, ask the selection about itself:

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [selection]
    :end-before: [selection]

Four straight edges, each as long as the material is thick, all at the
top of the bracket: the ends of the two arms, as wanted. An empty list, or
eight edges where four were expected, would be caught here and not three
lines later as a failed ``fillet``. :ref:`selecting_features` covers
building selections.

**********************
Measure the result
**********************

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [measure]
    :end-before: [measure]

A bounding box of the wrong size means a dimension went astray. More than
one solid means pieces that were meant to join did not touch. A volume
that did not change means an operation that was meant to add or cut did
nothing.

``is_valid`` asks the kernel whether the shape is sound. Treat it as a
first check and not as a verdict: its answer is not always right, so a
part that passes should still be looked at and measured.

****************
Print values
****************

The geometric types print themselves usefully:

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [printing]
    :end-before: [printing]

.. code-block:: text

    plane=Plane((0, 0, 1), (1, 0, 0), (0, 0, 1))
    plane.location=Location((0, 0, 1), (0, 0, 0))
    bbox: -25.0 <= x <= 25.0, 0.0 <= y <= 25.0, -12.5 <= z <= 12.5

A plane prints its origin, X direction and Z direction, and a location
its position and its three rotation angles. Shapes are different: a face
or an edge prints only its type and address, so print what you want to
know about it, such as its ``center()``, ``length`` or ``area``.

For the structure of a shape, :meth:`~topology.Shape.show_topology` gives
a tree:

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [topology]
    :end-before: [topology]

.. code-block:: text

    Compound         at 0x11fa524b0, Center(0, 0, 0)
    └── Solid        at 0x11fa52bf0, Center(0, 0, 0)
        └── Shell    at 0x11fa525b0, Center(0, 0, 0)
            ├── Face at 0x11fa520b0, Center(-0.5, 0, 0)
            ├── Face at 0x11fa51bb0, Center(0.5, 0, 0)
            ├── Face at 0x11fa52e70, Center(0, -0.5, 0)
            ├── Face at 0x11fa51b30, Center(0, 0.5, 0)
            ├── Face at 0x11fa51bb0, Center(0, 0, -0.5)
            └── Face at 0x11fa51270, Center(0, 0, 0.5)

****************
Read the log
****************

build123d reports what its builders are doing through Python's standard
``logging``, under the name ``build123d``. Nothing is shown until logging
is switched on, which takes one line at the top of a script:

.. code-block:: build123d

    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

With that in place, this:

.. literalinclude:: /how_to/debugging_examples.py
    :language: build123d
    :start-after: [logging]
    :end-before: [logging]

prints:

.. code-block:: text

    INFO: Entering BuildPart with mode=Mode.ADD which is in different scope as parent
    INFO: Completed integrating 1 object(s) into part with Mode=Mode.ADD
    INFO: GridLocations is pushing 4 points: [Location((-30, -20, 0), (0, 0, 0)), Location((-30, 20, 0), (0, 0, 0)), Location((30, -20, 0), (0, 0, 0)), Location((30, 20, 0), (0, 0, 0))]
    INFO: Completed integrating 4 object(s) into part with Mode=Mode.SUBTRACT
    INFO: GridLocations is popping 4 points
    INFO: BuildPart context requested by chamfer
    INFO: Completed integrating 1 object(s) into part with Mode=Mode.REPLACE
    INFO: Exiting BuildPart

The log shows each object as it is combined, with its mode, and each set
of locations as it comes into force and goes out again. It answers
questions such as "was this hole made four times or once?" and "was that
added or subtracted?".

To send the log to a file, give ``basicConfig`` a ``filename``:

.. code-block:: build123d

    logging.basicConfig(
        filename="my_model.log",
        level=logging.INFO,
        format="%(name)s-%(levelname)s %(asctime)s - %(message)s",
    )

************
See also
************

* :ref:`faq` answers the questions that most often lie behind a model that
  will not build.
* :ref:`tips` has habits that avoid problems in the first place.
* :ref:`selecting_features` covers selections, the usual place a model
  goes wrong.
