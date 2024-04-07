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

Watch John Degenstein create three build123d designs being created in realtime with Visual 
Studio Code and the ocp-vscode viewer in a timed event from the TooTallToby 2023 Leadership 
Challenge: 
`build123d May 2023 TooTallToby Leaderboard Challenge <https://www.youtube.com/watch?v=fH8aW27jEiw>`_

cq-editor
=========

GUI editor based on PyQT.

See: `cq-editor <https://github.com/jdegenstein/jmwright-CQ-Editor>`_

yet-another-cad-viewer
======================

A CAD viewer capable of displaying OCP models (CadQuery/Build123d) in a
web browser. Mainly intended for deployment of finished models as a static
website. It also works for developing models with hot reloading, though
this feature may not be as mature as in ocp-vscode.

See: `yet-another-cad-viewer <https://github.com/yeicor-3d/yet-another-cad-viewer>`_


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
