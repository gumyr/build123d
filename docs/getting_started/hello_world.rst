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

A simple model needs nothing more than this: an ordinary Python script, here
with a single line of substance, in which :class:`~objects_part.Box` creates
a solid from its length, width and height.

Because a model is Python, it can grow in the way any software does. A larger
design is usually a project rather than one script: parts written as classes
in files of their own, dimensions kept in data files such as JSON or YAML,
tests that check the parts, and documentation generated from the code. Parts
that are needed again and again can be gathered into a library and shared.
All the tools and habits of software development are available, and none of
them is needed to begin.

**********
Viewing it
**********

build123d only creates the model; displaying it requires a separate viewer.
With OCP Viewer installed and running, as :ref:`installation` describes, two
more lines send the box to it:

.. code-block:: build123d

    from build123d import *
    from ocp_viewer import *

    box = Box(80, 60, 10)

    show(box)

Run the script, and the box appears in the browser page. If you would rather
use another viewer, such as the one inside Visual Studio Code, the script does
not change, because those listed in :ref:`external` are driven by the same
``show``.

************
Exporting it
************

So far the box exists only while the script is running. To use it anywhere
else, in another CAD program or in a slicer, export it to a file:

.. code-block:: build123d

    export_step(box, "box.step")
    export_stl(box, "box.stl")

The two formats serve different purposes: STEP keeps the exact geometry, which
is what other CAD tools want, while STL is a mesh of triangles, the usual
input for a 3D printing slicer. :doc:`/how_to/import_export` covers the other
formats.

Before going further, :ref:`builder_and_algebra` explains the two ways of
writing a model that the rest of this documentation uses.
