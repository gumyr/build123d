.. _installation:

############
Installation
############

build123d requires Python 3.11 to 3.14. It is installed with ``pip``, best
into a virtual environment of its own:

.. code-block:: bash

    pip install build123d

To check that it worked, ask it for the volume of a box:

.. code-block:: bash

    python -c "from build123d import *; print(Box(1, 2, 3).volume)"

which prints ``6.0``.

If ``pip`` reports conflicting dependencies, it is usually out of date.
Upgrade it with ``python -m pip install --upgrade pip`` and try again.

***********************
Install a viewer
***********************

build123d makes models and does not display them, so a viewer is needed to
see what a script has made. The simplest to set up is OCP Viewer, which is
one more package in the same Python environment and shows the model in a
web browser:

.. code-block:: bash

    pip install ocp-viewer
    ocp-viewer

The second command starts the viewer and prints an address, by default
``http://127.0.0.1:3939``. Open it in a browser and leave it running. A
script then sends a model to it with ``show``, as :ref:`hello_world` does
next.

There is nothing else to download and no editor to change: write the script
in whatever you already use, and run it with the Python that build123d is
installed in.

Other viewers, including an extension that puts the same viewer inside
Visual Studio Code, are listed in :ref:`external`.

***********************
Other ways to install
***********************

With uv
=======

Most trouble with installing build123d comes from the Python environment
rather than from build123d: the wrong Python, or a package installed into
one environment and a script run with another.
`uv <https://docs.astral.sh/uv/>`_ avoids both, because it downloads the
Python it is asked for and keeps the environment in the folder the work is
done in. It is installed with the single command given on its own site, and
the commands below are then the same on Linux, macOS and Windows.

First create a virtual environment in a work folder, and install build123d
and the viewer into it:

.. code-block:: bash

    cd work_folder                       # the folder your scripts will be in
    uv venv --python 3.14                # create a fresh virtual environment
    uv pip install build123d ocp-viewer  # install build123d and the viewer

Next start the viewer from the same folder, so that ``uv`` finds the
environment just created, and leave it running:

.. code-block:: bash

    cd work_folder
    uv run ocp-viewer

Then, in a second terminal, run a script from that folder in the same way:

.. code-block:: bash

    cd work_folder
    uv run python hello_world.py

Because ``uv run`` uses the environment in the folder it is run from, there
is nothing to activate, and the script and the viewer cannot end up with
different Pythons.

With poetry
===========

In a project managed by `poetry <https://python-poetry.org/>`_, add the
release as a dependency:

.. code-block:: bash

    poetry add build123d

For the development version, name the branch, since build123d's default
branch is ``dev``:

.. code-block:: bash

    poetry add git+https://github.com/gumyr/build123d.git@dev

The latest development version
==============================

To get changes that have not yet been released, install from GitHub:

.. code-block:: bash

    python -m pip install git+https://github.com/gumyr/build123d

For working on build123d itself
===============================

Clone the repository and install it in
`development mode <https://setuptools.pypa.io/en/latest/userguide/development_mode.html>`_,
with the tools the project's tests and checks use:

.. code-block:: bash

    git clone https://github.com/gumyr/build123d.git
    cd build123d
    python -m pip install -e ".[development]"

Type stubs for the kernel
=========================

If you work directly with the OpenCascade layer, ``OCP``, the type stubs
let an editor and a type checker understand it:

.. code-block:: bash

    python -m pip install "build123d[stubs]"
