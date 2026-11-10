.. _hello_world:

###########
Hello World
###########

With build123d :doc:`installed <installation>`, this is a complete first model:

.. code-block:: build123d

    from build123d import *

    box = Box(80, 60, 10)

.. image:: /assets/general_ex1.svg
    :align: center

A build123d model is an ordinary Python script, and
:class:`~objects_part.Box` creates a solid of the given length, width and
height.

**********
Viewing it
**********

build123d creates the model; a separate viewer displays it. With one of the
viewers listed in :ref:`external` installed - *ocp_vscode*, for example - add
``show(box)`` to the end of the script.

*********
Saving it
*********

To use the model outside of Python, export it:

.. code-block:: build123d

    export_step(box, "box.step")
    export_stl(box, "box.stl")

STEP keeps the exact geometry for other CAD tools and STL is the usual input
for a 3D printing slicer; :doc:`import_export` covers the other formats.

:ref:`where_next` suggests what to read from here.
