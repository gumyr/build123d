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

.. image:: build123d_logo.svg
  :align: center

build123d is an alternate to the `CadQuery <https://cadquery.readthedocs.io/en/latest/index.html>`_
Fluent API. It has several advantages over this API but the largest one is that build123d
enables the full python toolbox when designing objects - for loops, references to objects,
list sorting and filtering, etc. - unconstrained by the limitations of method chaining
used in CadQuery 2.x.

########
Overview
########

build123d uses the standard python context manager - e.g. the ``with`` statement often used when
working with files - as a builder of the object under construction. Once the object is complete
it can be extracted from the builders and used in other ways: for example exported as a STEP
file or used in an Assembly.  There are three builders available:

* **BuildLine**: a builder of one dimensional objects - those with the property
  of length but not of area or volume - typically used
  to create complex lines used in sketches or paths.
* **BuildSketch**: a builder of planar two dimensional objects - those with the property
  of area but not of volume - typically used to create 2D drawings that are extruded into 3D parts.
* **BuildPart**: a builder of three dimensional objects - those with the property of volume -
  used to create individual parts.

The three builders work together in a hierarchy as follows:

.. code-block:: python

    with BuildPart() as my_part:
        ...
        with BuildSketch() as my_sketch:
            ...
            with BuildLine() as my_line:
                ...
            ...
        ...

where ``my_line`` will be added to ``my_sketch`` once the line is complete and ``my_sketch`` will be
added to ``my_part`` once the sketch is complete.

As an example, consider the design of a simple bearing pillow block:

.. literalinclude:: ../examples/pillow_block.py
    :lines: 28-47


#################
Table Of Contents
#################

.. toctree::
    :maxdepth: 2

    introduction.rst
    installation.rst
    cheat_sheet.rst
    key_concepts.rst
    tutorials.rst
    advantages.rst
    builder_api_reference.rst
    direct_api_reference.rst

==================
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
