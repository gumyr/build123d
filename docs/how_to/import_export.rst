.. _import_export:

#######################
Importing and exporting
#######################

A model leaves build123d as a file, for a slicer, another CAD system, a
web page or a drawing, and geometry made elsewhere comes in the same way.
Which format to use depends on what the file has to carry, so this guide
starts there.

Export and import work on finished shapes, so everything here is the same
whether the shape was made in builder or algebra mode. In builder mode,
pass the builder's result: ``export_step(my_part.part, "part.step")``.

.. list-table::
    :header-rows: 1
    :widths: 50 50

    * - To
      - use
    * - exchange a model with another CAD system
      - ``export_step``, ``import_step``
    * - keep exact geometry for build123d or OpenCascade
      - ``export_brep``, ``import_brep``
    * - send a part to a slicer
      - ``export_stl``, or ``Mesher`` for 3MF
    * - show a model on the web or in a renderer
      - ``export_gltf``, ``export_obj``
    * - make a 2D drawing
      - ``ExportSVG``, ``ExportDXF``
    * - bring in a mesh
      - ``import_stl``, ``Mesher.read``
    * - bring in a drawing
      - ``import_svg``, ``import_dxf``
    * - turn an SVG outline into code
      - ``import_svg_as_buildline_code``

*******************
Choose a format
*******************

.. list-table::
    :header-rows: 1
    :widths: 10 30 12 14 12 22

    * - Format
      - Holds
      - Colour
      - Labels and tree
      - Units
      - Functions
    * - STEP
      - exact geometry
      - yes
      - yes
      - yes
      - :func:`~exporters3d.export_step`, :func:`~importers.import_step`
    * - BREP
      - exact geometry
      - no
      - no
      - no
      - :func:`~exporters3d.export_brep`, :func:`~importers.import_brep`
    * - 3MF
      - triangle meshes
      - yes
      - labels
      - yes
      - :class:`~mesher.Mesher`
    * - STL
      - triangles
      - no
      - no
      - no
      - :func:`~exporters3d.export_stl`, :func:`~importers.import_stl`,
        :class:`~mesher.Mesher`
    * - glTF
      - triangle meshes with materials
      - yes
      - \-
      - yes
      - :func:`~exporters3d.export_gltf` (export only)
    * - OBJ
      - triangle meshes with texture coordinates
      - no
      - no
      - no
      - :func:`~exporters3d.export_obj` (export only)
    * - SVG
      - 2D lines and filled shapes
      - yes
      - layers
      - yes
      - :class:`~exporters.ExportSVG`, :func:`~importers.import_svg`
    * - DXF
      - 2D lines and arcs
      - by layer
      - layers
      - yes
      - :class:`~exporters.ExportDXF`, :func:`~import_dxf.import_dxf`

*Exact geometry* means the surfaces themselves: a cylinder is saved as a
cylinder and comes back as one. A *mesh* is an approximation in flat
triangles, good for printing and display, and it cannot be turned back
into the surfaces it was made from.

An STL file holds triangles and nothing else: no colour, no names and no
units. Whoever reads it has to be told, or guess, what one unit of length
is.

The examples below save this small assembly, a plate and a knob, each with
a label and a colour:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [model]
    :end-before: [model]

********************************************
Exchange a model with another CAD system
********************************************

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [step]
    :end-before: [step]

STEP is the format to use between CAD systems. It carries the exact
geometry and, for an assembly, the tree of parts with their labels and
colours. The panel read back here is a ``Compound`` labelled ``panel``
with two children, ``plate`` and ``knob``, in their colours, and the hole
in the plate is still a cylinder.

A STEP file states its unit of length. build123d models are in
millimetres unless you decide otherwise, and ``unit`` says what the
numbers in this model mean:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [step_units]
    :end-before: [step_units]

``import_step`` converts to millimetres as it reads, so this panel would
come back 25.4 times as large.

BREP is the native format of the OpenCascade kernel that build123d is
built on. It is exact and quick to read and write, and it holds geometry
only: the two solids come back, without their labels, colours or tree.

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [brep]
    :end-before: [brep]

***************************
Send a part to a slicer
***************************

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [stl]
    :end-before: [stl]

:func:`~exporters3d.export_stl` writes the shape as triangles.
``tolerance`` is how far a triangle may lie from the true surface, and
``angular_tolerance`` limits how much the surface may turn from one
triangle to the next. Smaller values give a smoother part and a larger
file: the second file here is several times the size of the first.

3MF is the better format where the slicer accepts it. It holds one mesh
for each shape, with its label and colour, and states its units.
:class:`~mesher.Mesher` writes it, and can attach a part number and other
metadata:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [threemf]
    :end-before: [threemf]

``Mesher`` writes STL too: ``exporter.write("panel.stl")`` saves the same
meshes without the extras.

To lay several parts out on the bed before saving them, see
:ref:`packing`.

********************************************
Show a model on the web or in a renderer
********************************************

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [gltf]
    :end-before: [gltf]

glTF is the format web viewers and game engines read. It holds meshes
with their colours and, where a shape has a material, how that material
should be rendered. ``binary=True`` with a ``.glb`` name keeps everything
in one file. :ref:`materials` covers giving shapes an appearance.

Wavefront OBJ is a widely supported text-based mesh format.
:func:`~exporters3d.export_obj` exports triangulated geometry, including
vertex positions, normals and UV texture coordinates. UV coordinates map
each mesh face to a two-dimensional texture, allowing an external
application to paint or bake textures onto the model.

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [obj]
    :end-before: [obj]

By default the exporter packs the UV islands for all faces into one
normalized texture atlas. ``atlas_gutter`` reserves empty space around
every island, which avoids texture bleeding when the atlas is sampled
with interpolation.

The OBJ exporter writes geometry and UV data only. It does not create a material
library (``.mtl``) file or embed, reference, or assign texture image files. Use the
exported UV atlas with a separate texture-painting, baking, or material-authoring
workflow.

*********************
Make a 2D drawing
*********************

A drawing is made in two steps: get 2D shapes from the model, then hand
them to an exporter. There are two ways to get the shapes:

* **A view.** :meth:`~topology.Mixin3D.drawing_view` gives the edges of a
  shape as seen from a viewpoint, like a camera, split into ``visible``
  and ``hidden``. ``up`` sets the camera's orientation and ``look_at``
  where it points; by default it looks at the centre of the shape with Z
  up. :ref:`projection_view` covers it.
* **A section.** :func:`~operations_part.section` cuts the part with a
  plane and gives the cut as a sketch.

:class:`~exporters.ExportSVG` and :class:`~exporters.ExportDXF` work the
same way: create the document, add layers with their colours and line
types, add shapes to the layers, and write the file.

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [svg]
    :end-before: [svg]

``ExportSVG`` accepts the standard ``ColorLike`` interface for
layer fill and line colours. When a layer colour is omitted, a Face colour is used
for its SVG fill and an Edge or Wire colour is used for its SVG stroke. An
explicit layer colour, including ``None``, overrides the shape colour.

The older ``ColorIndex``, ``ezdxf.colors.RGB``, and 0–255 RGB tuple inputs are
deprecated for SVG export and will be removed at or before version 1.0.0. They
are converted with a ``DeprecationWarning`` during the transition. Use colour
names, hexadecimal values, or normalized RGB(A) tuples instead.

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [dxf]
    :end-before: [dxf]

A shape given to either exporter has to lie flat in the XY plane, as a
section by ``Plane.XY`` and the edges of a ``drawing_view`` do.

``ExportDXF`` accepts the standard ``ColorLike`` interface for
document and layer colours. ColorLike alpha is written as DXF layer transparency.
True-colour black is always ``0x000000``; unlike ACI 7, DXF viewers do not switch
it to white on dark backgrounds. DXF versions before R2004 have no true colour,
so for those the nearest AutoCAD Color Index is written instead. The older
``ColorIndex`` values remain supported
during the transition but emit a ``DeprecationWarning`` and will be removed at or
before version 1.0.0.

Line types
==========

ANSI (American National Standards Institute) and ISO (International Organization for 
Standardization) standards both define line types in drawings used in DXF and SVG
exported drawings:

* ANSI Standards:
   * ANSI/ASME Y14.2 - "Line Conventions and Lettering" is the standard that defines 
     line types, line weights, and line usage in engineering drawings in the United States.

* ISO Standards:
   * ISO 128 - "Technical drawings -- General principles of presentation" is the ISO 
     standard that covers the general principles of technical drawing presentation, 
     including line types and line conventions.
   * ISO 13567 - "Technical product documentation (TPD) -- Organization and naming of 
     layers for CAD" provides guidelines for the organization and naming of layers in 
     Computer-Aided Design (CAD) systems, which may include line type information.

These standards help ensure consistency and clarity in technical drawings, making it 
easier for engineers, designers, and manufacturers to communicate and interpret the 
information presented in the drawings.

The line types used by the 2D Exporters are defined by the :class:`~exporters.LineType` 
Enum and are shown in the following diagram:

.. image:: /how_to/assets/import_export/line_types.svg
    :align: center

.. image:: /how_to/assets/import_export/line_types.svg
    :align: center

******************************
Bring in a model or a mesh
******************************

``import_step`` and ``import_brep``, shown above, bring in exact
geometry, which can be selected from and built on like anything made in
build123d.

A mesh is different:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [stl_import]
    :end-before: [stl_import]

:func:`~importers.import_stl` returns a single faceted ``Face``, which
can be shown and measured and not much more. Its ``model_unit`` argument
says what unit the file's numbers are in, since the file does not.
Rebuilding a real model from such a mesh is the subject of
:ref:`stl_reconstruction_tutorial`, which uses
:func:`~build123d.detect_primitives` to find the planes, cylinders and
spheres in it.

A 3MF file is read with ``Mesher``, which returns one shape for each mesh
with its label and colour restored:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [threemf_import]
    :end-before: [threemf_import]

**********************
Bring in a drawing
**********************

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [svg_import]
    :end-before: [svg_import]

:func:`~importers.import_svg` returns a list: a ``Wire`` for each outline
and a ``Face``, with its colour, for each filled shape. By default the
drawing is moved so that its lower left corner is at the origin and
flipped so that Y points up, as build123d has it; ``align`` and
``flip_y`` change that.

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [dxf_import]
    :end-before: [dxf_import]

:func:`~import_dxf.import_dxf` returns the lines and arcs of the drawing
as separate edges, here four lines and a circle, ready for ``make_face``
or to be used as they are.

To turn an SVG outline into code that can be edited, not just geometry:

.. literalinclude:: /how_to/import_export.py
    :language: build123d
    :start-after: [svg_code]
    :end-before: [svg_code]

:func:`~importers.import_svg_as_buildline_code` returns the source of a
``BuildLine`` that draws the paths of the file, and the name it gave the
builder. :ref:`drawing_lines_and_curves` has more on using it.

************
See also
************

* :ref:`import_export_reference` lists every exporter and importer with
  its arguments.
* :ref:`projection_view` and :ref:`tech_drawing_tutorial` cover making
  drawings.
* :ref:`packing` arranges parts for a print bed.
* :ref:`materials` covers the appearance that glTF carries.
