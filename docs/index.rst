..
    build123d readthedocs documentation

    by:   Gumyr
    date: July 13th 2022

    desc: This is the documentation for build123d on readthedocs

    license:

        Copyright 2022 Gumyr

        Licensed under the Apache License, Version 2.0 (the "License");
        you may not use this file except in compliance with the License.
        You may obtain a copy of the License at

            http://www.apache.org/licenses/LICENSE-2.0

        Unless required by applicable law or agreed to in writing, software
        distributed under the License is distributed on an "AS IS" BASIS,
        WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
        See the License for the specific language governing permissions and
        limitations under the License.


.. highlight:: python

.. image:: /assets/build123d_logo/logo-banner.svg
  :align: center
  :alt: build123d logo

########
About
########

build123d is a Python library for 2D and 3D CAD. A model is a Python
program: shapes are made, placed and combined in code, dimensions are
variables, and changing one and running the program again gives the new
part. It is built on the Open Cascade geometric kernel, the boundary
representation (BREP) kernel behind FreeCAD, so its models are exact
geometry, suitable for 3D printing, CNC machining and laser cutting, and
can be exported as STEP to FreeCAD, SolidWorks and other CAD systems.

.. raw:: html

    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    <model-viewer poster="_images/tea_cup.png" src="_static/tea_cup.glb" alt="A tea cup modelled in build123d" auto-rotate camera-controls style="width: 100%; height: 50vh;"></model-viewer>

This tea cup is about forty lines of Python. :ref:`See how it is made
<tea_cup>`, in both of the styles build123d can be written in.

*****************
Where to start
*****************

This documentation is organised on the `Diátaxis <https://diataxis.fr/>`_
framework, which sorts documentation by what the reader needs at the time:
tutorials for learning, how-to guides for getting a task done, reference
for looking something up, and explanation for understanding.

* **New to build123d?** :ref:`getting_started` covers installation, a first
  model, and the two modes a model can be written in.
* **Learning it?** The :ref:`tutorials` each build a complete part, step by
  step.
* **Working on a design?** The :ref:`how_to_guides` are organised by task,
  and the :ref:`cheat_sheet` lists everything on one page.
* **Deciding whether to use it, or wondering why it works the way it
  does?** Start with :ref:`why_build123d`.
* **Looking for ideas?** The :ref:`examples` are finished models with their
  code.
* **Want to test what you have learned?** The :ref:`challenges` each give
  a drawing of a part to model, and the mass your result should come to.

.. note::


  This documentation is available in
  `pdf <https://build123d.readthedocs.io/_/downloads/en/latest/pdf/>`_ and
  `epub <https://build123d.readthedocs.io/_/downloads/en/latest/epub/>`_ formats
  for reference while offline.

.. note::

  There is a `Discord <https://discord.com/invite/Bj9AQPsCfx>`_ server (shared with CadQuery) where
  you can ask for help in the build123d channel.

#################
Table Of Contents
#################

.. toctree::
    :maxdepth: 2

    getting_started/index.rst
    tutorials/index.rst
    how_to/index.rst
    reference/index.rst
    explanation/index.rst
    examples/index.rst
    challenges/index.rst

==================
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
