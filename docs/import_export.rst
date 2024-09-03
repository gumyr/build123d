#############
Import/Export
#############

Methods and functions specific to exporting and importing build123d objects are defined below.

For example:

.. code-block:: python

    with BuildPart() as box_builder:
        Box(1, 1, 1)
    export_step(box_builder.part, "box.step")

File Formats
============

3MF
---

The 3MF (3D Manufacturing Format) file format is a versatile and modern standard 
for representing 3D models used in additive manufacturing, 3D printing, and other 
applications. Developed by the 3MF Consortium, it aims to overcome the limitations 
of traditional 3D file formats by providing a more efficient and feature-rich solution. 
The 3MF format supports various advanced features like color information, texture mapping, 
multi-material definitions, and precise geometry representation, enabling seamless 
communication between design software, 3D printers, and other manufacturing devices. 
Its open and extensible nature makes it an ideal choice for exchanging complex 3D data 
in a compact and interoperable manner.

BREP
----

The BREP (Boundary Representation) file format is a widely used data format in 
computer-aided design (CAD) and computer-aided engineering (CAE) applications. 
BREP represents 3D geometry using topological entities like vertices, edges, 
and faces, along with their connectivity information. It provides a precise 
and comprehensive representation of complex 3D models, making it suitable for 
advanced modeling and analysis tasks. BREP files are widely supported by various 
CAD software, enabling seamless data exchange between different systems. Its ability 
to represent both geometric shapes and their topological relationships makes it a 
fundamental format for storing and sharing detailed 3D models.

DXF
---

The DXF (Drawing Exchange Format) file format is a widely used standard for 
representing 2D and 3D drawings, primarily used in computer-aided design (CAD) 
applications. Developed by Autodesk, DXF files store graphical and geometric data, 
such as lines, arcs, circles, and text, as well as information about layers, colors, 
and line weights. Due to its popularity, DXF files can be easily exchanged and 
shared between different CAD software. The format's simplicity and human-readable 
structure make it a versatile choice for sharing designs, drawings, and models 
across various CAD platforms, facilitating seamless collaboration in engineering 
and architectural projects.

glTF
----

The glTF (GL Transmission Format) is a royalty-free specification for the efficient 
transmission and loading of 3D models and scenes by applications. Developed by the 
Khronos Group, glTF is designed as a compact, interoperable format that enables the 
quick display of assets across various platforms and devices. glTF supports a rich 
feature set, including detailed meshes, materials, textures, skeletal animations, 
and more, facilitating complex 3D visualizations. It streamlines the process of 
sharing and deploying 3D content in web applications, game engines, and other 
visualization tools, making it the "JPEG of 3D." glTF's versatility and efficiency 
have led to its widespread adoption in the 3D content industry.

STL
---

The STL (STereoLithography) file format is a widely used file format in 3D printing 
and computer-aided design (CAD) applications. It represents 3D geometry using 
triangular facets to approximate the surface of a 3D model. STL files are widely 
supported and can store both the geometry and color information of the model. 
They are used for rapid prototyping and 3D printing, as they provide a simple and 
efficient way to represent complex 3D objects. The format's popularity stems from 
its ease of use, platform independence, and ability to accurately describe the 
surface of intricate 3D models with a minimal file size.

STEP
----

The STEP (Standard for the Exchange of Product model data) file format is a widely 
used standard for representing 3D product and manufacturing data in computer-aided 
design (CAD) and computer-aided engineering (CAE) applications. It is an ISO standard 
(ISO 10303) and supports the representation of complex 3D geometry, product structure, 
and metadata. STEP files store information in a neutral and standardized format, 
making them highly interoperable across different CAD/CAM software systems. They 
enable seamless data exchange between various engineering disciplines, facilitating 
collaboration and data integration throughout the entire product development and 
manufacturing process.

SVG
---

The SVG (Scalable Vector Graphics) file format is an XML-based standard used for 
describing 2D vector graphics. It is widely supported and can be displayed in modern 
web browsers, making it suitable for web-based graphics and interactive applications. 
SVG files define shapes, paths, text, and images using mathematical equations, 
allowing for smooth scalability without loss of quality. The format is ideal for 
logos, icons, illustrations, and other graphics that require resolution independence. 
SVG files are also easily editable in text editors or vector graphic software, making 
them a popular choice for designers and developers seeking flexible and versatile graphic 
representation.


2D Exporters 
============

Exports to DXF (Drawing Exchange Format) and SVG (Scalable Vector Graphics) 
are provided by the 2D Exporters: ExportDXF and ExportSVG classes. 

DXF is a widely used file format for exchanging CAD (Computer-Aided Design) 
data between different software applications. SVG is a widely used vector graphics
format that is supported by web browsers and various graphic editors.  

The core concept to these classes is the creation of a DXF/SVG document with 
specific properties followed by the addition of layers and shapes to the documents.
Once all of the layers and shapes have been added, the document can be written
to a file. 

3D to 2D Projection
-------------------

There are a couple ways to generate a 2D drawing of a 3D part:

* Generate a section: The  :func:`~operations_part.section` operation can be used to
  create a 2D cross section of a 3D part at a given plane.
* Generate a projection: The :meth:`~topology.Shape.project_to_viewport` method can be
  used to create a 2D projection of a 3D scene. Similar to a camera, the ``viewport_origin``
  defines the location of camera, the ``viewport_up`` defines the orientation of the camera,
  and the ``look_at`` parameter defined where the camera is pointed.  By default, 
  ``viewport_up`` is the positive z axis and ``look_up`` is the center of the shape.  The
  return value is a tuple of lists of edges, the first the visible edges and the second
  the hidden edges.  
  
Each of these Edges and Faces can be assigned different line color/types and fill colors
as described below (as ``project_to_viewport`` only generates Edges, fill doesn't apply).  
The shapes generated from the above steps are to be added as shapes 
in one of the exporters described below and written as either a DXF or SVG file as shown
in this example:

.. code-block:: python

    view_port_origin=(-100, -50, 30)
    visible, hidden = part.project_to_viewport(view_port_origin)
    max_dimension = max(*Compound(children=visible + hidden).bounding_box().size)
    exporter = ExportSVG(scale=100 / max_dimension)
    exporter.add_layer("Visible")
    exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
    exporter.add_shape(visible, layer="Visible")
    exporter.add_shape(hidden, layer="Hidden")
    exporter.write("part_projection.svg")

LineType
--------

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

.. image:: assets/line_types.svg
    :align: center


ExportDXF
---------

.. autoclass:: exporters.ExportDXF
    :noindex:

ExportSVG
---------

.. autoclass:: exporters.ExportSVG
    :noindex:

3D Exporters
============

.. py:module:: exporters3d

.. autofunction:: export_brep
   :noindex:

.. autofunction:: export_gltf
   :noindex:

.. autofunction:: export_step
   :noindex:

.. autofunction:: export_stl
   :noindex:

3D Mesh Export
--------------

Both 3MF and STL export (and import) are provided with the :class:`~mesher.Mesher` class.
As mentioned above, the 3MF format it provides is feature-rich and therefore has a slightly
more complex API than the simple Shape exporters.

For example:

.. code-block:: python

    # Create the shapes and assign attributes
    blue_shape = Solid.make_cone(20, 0, 50)
    blue_shape.color = Color("blue")
    blue_shape.label = "blue"
    blue_uuid = uuid.uuid1()
    red_shape = Solid.make_cylinder(5, 50).move(Location((0, -30, 0)))
    red_shape.color = Color("red")
    red_shape.label = "red"

    # Create a Mesher instance as an exporter, add shapes and write
    exporter = Mesher()
    exporter.add_shape(blue_shape, part_number="blue-1234-5", uuid_value=blue_uuid)
    exporter.add_shape(red_shape)
    exporter.add_meta_data(
        name_space="custom",
        name="test_meta_data",
        value="hello world",
        metadata_type="str",
        must_preserve=False,
    )
    exporter.add_code_to_metadata()
    exporter.write("example.3mf")
    exporter.write("example.stl")

.. autoclass:: mesher.Mesher

.. note::

    If you need to align multiple components for 3D printing, you can use the  :ref:`pack() <pack>` function to arrange the objects side by side and align them on the same plane. This ensures that your components are well-organized and ready for the printing process.


2D Importers
============
.. py:module:: importers

.. autofunction:: import_svg
.. autofunction:: import_svg_as_buildline_code

3D Importers
============

.. autofunction:: import_brep
.. autofunction:: import_step
.. autofunction:: import_stl

3D Mesh Import
--------------

Both 3MF and STL import (and export) are provided with the :class:`~mesher.Mesher` class.

For example:

.. code-block:: python

    importer = Mesher()
    cone, cyl = importer.read("example.3mf")
    print(
        f"{importer.mesh_count=}, {importer.vertex_counts=}, {importer.triangle_counts=}"
    )
    print(f"Imported model unit: {importer.model_unit}")
    print(f"{cone.label=}")
    print(f"{cone.color.to_tuple()=}")
    print(f"{cyl.label=}")
    print(f"{cyl.color.to_tuple()=}")

.. code-block:: none

    importer.mesh_count=2, importer.vertex_counts=[66, 52], importer.triangle_counts=[128, 100]
    Imported model unit: Unit.MM
    cone.label='blue'
    cone.color.to_tuple()=(0.0, 0.0, 1.0, 1.0)
    cyl.label='red'
    cyl.color.to_tuple()=(1.0, 0.0, 0.0, 1.0)
