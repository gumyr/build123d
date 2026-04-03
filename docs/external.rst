.. _external:

############################
External Tools and Libraries
############################

The following sections describe tools and libraries external to build123d
that extend its functionality.

*****************
Editors & Viewers
*****************

ocp-vscode
==========

A viewer for OCP based Code-CAD (CadQuery, build123d) integrated into
VS Code.

See: `ocp-vscode <https://github.com/bernhard-42/vscode-ocp-cad-viewer>`_
(formerly known as cq_vscode)

Watch Jern create three build123d designs in realtime with Visual
Studio Code and the ocp-vscode viewer extension in a timed event from the TooTallToby 2024 Spring Open Tournament: 
`build123d entry video <https://www.youtube.com/watch?v=UhUmMInlJic>`_

cq-editor fork
==============

GUI editor based on PyQT. This fork has changes from jdegenstein to allow easier use with build123d.

See: `jdegenstein's fork of cq-editor <https://github.com/jdegenstein/jmwright-CQ-Editor>`_

Yet Another CAD Viewer
======================

A web-based CAD viewer for OCP models (CadQuery/build123d) that runs in any modern browser and supports
static site deployment. Features include interactive inspection of faces, edges, and vertices, 
measurement tools, per-model clipping planes, transparency control, and hot reloading via ``yacv-server``. 
It also has a build123d playground for editing and sharing models directly in the browser 
(`demo <https://yeicor-3d.github.io/yet-another-cad-viewer/#pg_code_url=https://raw.githubusercontent.com/gumyr/build123d/refs/heads/dev/examples/toy_truck.py>`_).

See: `Yet Another CAD Viewer <https://github.com/yeicor-3d/yet-another-cad-viewer>`_

PartCAD VS Code extension
=========================

A wrapper around ``ocp-vscode`` (see above) which requires build123d scripts to be
packaged using ``PartCAD`` (see below). While it requires the overhead of maintaining
the package, it provides some convenience features (such as UI controls to export models)
as well as functional features (such as UI controls to pass parameters into build123d scripts
and AI-based generative design tools).

It's also the most convenient tool to create new packages and parts. More PDM and PLM features are expected to arrive soon.

**************
Part Libraries
**************

bd_warehouse
============

On-demand generation of parametric parts that seamlessly integrate into
build123d projects.

Parts available include:

    * fastener - Nuts, Screws, Washers and custom holes
    * flange - Standardized parametric flanges
    * pipe - Standardized parametric pipes
    * thread - Parametric helical threads (Iso, Acme, Plastic, etc.)

See: `bd_warehouse <https://bd-warehouse.readthedocs.io/en/latest/index.html>`_

bd_beams_and_bars
=================

2D sections and 3D beams generation (UPN, IPN, UPE, flat bars, ...)

See: `bd_beams_and_bars <https://bd-beams-and-bars.3d.experimentslabs.com/>`_

Superellipses & Superellipsoids
===============================

Superellipses are a more sophisticated alternative to rounded
rectangles, with smoothly changing curvature. They are flexible
shapes that can be adjusted by changing the "exponent" to get a
result that varies between rectangular and elliptical, or from
square, through squircle, to circle, and beyond...

Superellipses can be found:

  * in typefaces such as Melior, Eurostyle, and Computer Modern
  * as the shape of airliner windows, tables, plates
  * clipping the outline of iOS app icons

They were named and popularized in the 1950s-1960s by the Danish
mathematician and poet Piet Hein, who used them in the winning
design for the Sergels Torg roundabout in Stockholm.

See: `Superellipses & Superellipsoids <https://github.com/fanf2/kbd/blob/model-b/keybird42/superellipse.py>`_

Public PartCAD repository
=========================

See `partcad.org <https://partcad.org/repository>`_ for all the models packaged and published
using ``PartCAD`` (see below). This repository contains individual parts,
as well as large assemblies created using those parts. See
`the OpenVMP robot <https://partcad.org/repository/package/robotics/multimodal/openvmp/robots/don1>`_
as an example of an assembly

py_gearworks generator
======================
A gear generation framework that allows easy creation of a wide range of gears and drives.

See `py_gearworks <https://github.com/GarryBGoode/py_gearworks>`_

bd_vslot
=================

A library of V-Slot linear rail components, including V-Slot rails.

See: `bd_vslot <https://bd-vslot.readthedocs.io>`_

*****
Tools
*****

blendquery
==========

CadQuery and build123d integration for Blender.

See: `blendquery <https://github.com/uki-dev/blendquery>`_

nething
=======

3D generative AI for CAD modeling. Now everyone is an engineer. Make your ideas real.

See: `nething <https://nething.xyz/>`_

Listen to the following podcast which discusses **nething** in detail:
`The Next Byte Podcast <https://pod.link/wevolver/episode/74b11c1ff2bfc977adc96e5c7b4cd162>`_

ocp-freecad-cam
===============

CAM for CadQuery and Build123d by leveraging FreeCAD library. Visualizes in CQ-Editor 
and ocp-cad-viewer. Spiritual successor of `cq-cam <https://github.com/voneiden/cq-cam>`_

See: `ocp-freecad-cam <https://github.com/voneiden/ocp-freecad-cam>`_

PartCAD
=======

A package manager for CAD models. Build123d is the most supported Code-CAD framework,
but CadQuery and OpenSCAD are also supported. It can be used by build123d designs
`to import parts <https://partcad.readthedocs.io/en/latest/use_cases.html#python-build123d>`_
from PartCAD repositories, and to
`publish build123d designs <https://partcad.readthedocs.io/en/latest/use_cases.html#publish-packages>`_
to be consumed by others.

MakerRepo library (mr)
======================

The ``makerrepo`` Python package (imported as ``mr``) is a lightweight library that
provides decorators such as ``@artifact``, ``@customizable``, and ``@cached`` to
annotate functions that build your models. The decorators have no effect on your
existing build123d code until it is discovered and run by tools such as the
`makerrepo-cli <https://docs.makerrepo.com/makerrepo-cli/>`_ or
`MakerRepo.com <https://makerrepo.com/>`_ CI. The goal is to enable a code-driven
workflow locally (e.g. command-line tools) or in CI. The library does not assume
how it will be consumed, so annotated functions can be used with other tools and
frameworks as well.

See `MakerRepo Library Docs <https://docs.makerrepo.com/makerrepo-library/>`_ for
more information and `LaunchPlatform/makerrepo <https://github.com/LaunchPlatform/makerrepo>`_
for source code.

makerrepo-cli
=============

Command-line tool (available as ``makerrepo-cli`` or ``mr``) to build artifacts,
run generators, snapshot artifacts, and manage cache locally. It scans the
current directory for Python packages and modules that use the MakerRepo library
decorators.

See `MakerRepo CLI <https://docs.makerrepo.com/makerrepo-cli/>`_ for
documentation and `LaunchPlatform/makerrepo-cli <https://github.com/LaunchPlatform/makerrepo-cli>`_
for source code.

dl4to4ocp
=========

Library that helps perform `topology optimization <https://en.wikipedia.org/wiki/Topology_optimization>`_ on
your `OCP <https://github.com/CadQuery/OCP>`_-based CAD
models (`CadQuery <https://github.com/CadQuery/cadquery>`_/`Build123d <https://github.com/gumyr/build123d>`_/...) using
the `dl4to <https://github.com/dl4to/dl4to>`_ library.

See: `dl4to4ocp <https://github.com/yeicor-3d/dl4to4ocp/>`_

OCP.wasm
========

This project ports the low-level dependencies required for build123d to run in a browser. 
For a fully featured frontend, check out ``Yet Another CAD Viewer`` (see above).

See: `OCP.wasm <https://github.com/yeicor/OCP.wasm>`_
