.. _hello_world:

###########
Hello World
###########

With build123d :ref:`installed <installation>`, this is a complete first model:

.. code-block:: build123d

    from build123d import *

    box = Box(80, 60, 10)

.. image:: /getting_started/assets/hello_world_box.svg
    :align: center

A build123d model is an ordinary Python script, and
:class:`~objects_part.Box` creates a solid of the given length, width and
height.

**********
Viewing it
**********

build123d creates the model; a separate viewer displays it. With OCP Viewer
installed and running, as :ref:`installation` describes, two more lines send
the box to it:

.. code-block:: build123d

    from build123d import *
    from ocp_viewer import *

    box = Box(80, 60, 10)

    show(box)

Run the script, and the box appears in the browser page. The viewer inside
Visual Studio Code, one of those listed in :ref:`external`, is driven by the
same ``show``.

************
Exporting it
************

To use the model outside of Python, export it:

.. code-block:: build123d

    export_step(box, "box.step")
    export_stl(box, "box.stl")

STEP keeps the exact geometry for other CAD tools and STL is the usual input
for a 3D printing slicer; :doc:`/how_to/import_export` covers the other formats.

Before going further, :ref:`builder_and_algebra` explains the two ways of
writing a model that the rest of this documentation uses.
