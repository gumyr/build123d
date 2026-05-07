.. _stl_reconstruction_tutorial:

#############################################
Tutorial: Reconstructing a Design from an STL
#############################################

This tutorial describes a practical workflow for using
:func:`~build123d.detect_primitives` to help reconstruct a parametric build123d
model from an STL mesh.

This is not a push-button STL-to-CAD converter. It is a mesh-guided redesign
process. The goal is to extract enough analytic structure from a triangulated
model to make manual reconstruction faster and more reliable.

.. warning::

    Rebuilding a design from STL is usually slow, approximate, and manual.
    STL files contain triangles, not modeling intent. Even when
    :func:`~build123d.detect_primitives` finds useful planes, cylinders, and
    spheres, the final build123d model still needs to be designed deliberately.

Before working through this tutorial, review Steps 1-3 of
:ref:`design_tutorial`. The same ideas apply here:

* identify planes of symmetry
* identify likely axes of rotation
* choose a convenient origin before doing any serious work

These preparation steps often reduce the amount of mesh that needs to be
reconstructed to one half, one quarter, or even less.

Overview
********

The workflow described here is:

1. Import the STL with :class:`~mesher.Mesher`.
2. Split the mesh by symmetry planes and isolate the region to redesign.
3. Save that reduced mesh section as a BREP file.
4. Reload the BREP section while iterating on reconstruction.
5. Run :func:`~build123d.detect_primitives`.
6. Inspect the returned primitives, leftovers, and generated code.
7. Rebuild the design intentionally from those clues.

The key output of ``detect_primitives`` is guidance:

* ``primitives`` shows what was recognized analytically
* ``leftovers`` shows what was not covered
* ``code_lines`` provides algebra-mode fragments that often reveal common
  planes and likely sketch structure

Why Cache a Working Section as BREP?
************************************

Importing STL with :class:`~mesher.Mesher` is convenient, but large meshes can be
slow to load and process. Once a useful section of the part has been isolated,
save it as a BREP file and use that for repeated experimentation.

BREP files reload much more efficiently in build123d and are better suited to
an iterative reconstruction script.

Preparing the Mesh
******************

Start with the STL import and isolate the smallest useful section of the part.

.. code-block:: build123d

    from build123d import *

    importer = Mesher()
    full_mesh = importer.read("target_part.stl")[0]

    # Example: reduce the work to one quarter of a symmetric model
    quarter_mesh = split(full_mesh, Plane.YZ)
    quarter_mesh = split(quarter_mesh, Plane.XZ)

    export_brep(quarter_mesh, "target_part_quarter.brep")

The exact planes depend on the part. The point is not to begin running
``detect_primitives`` on the full mesh if symmetry can remove most of the work.

Reconstruction Script
*********************

Once the mesh section has been cached as BREP, iterate on a separate script or
enable a reconstruction section of the same script with a Boolean switch.

.. code-block:: build123d

    from build123d import *

    working_mesh = import_brep("target_part_quarter.brep")

    primitives, leftovers, code_lines = detect_primitives(working_mesh)

    print(*code_lines, sep="\n")

This call returns three complementary outputs:

``primitives``
    A :class:`~topology.ShapeList` of analytic faces that were recognized from
    the mesh. These are typically planes, cylinders, and spheres. Planar
    primitives are returned as rectangles sized to the planar region's
    bounding box, not as the original tessellated mesh patch.

``leftovers``
    Mesh faces that were not matched by the primitive detectors. These indicate
    freeform regions, noisy regions, or places where manual work is still
    required.

``code_lines``
    Generated algebra-mode code corresponding to the recognized primitives.

Inspecting the Results
**********************

The inspection step is the heart of this workflow.

1. Examine the primitives visually
==================================

Look at the returned ``primitives`` and decide what the detector found well.

Useful questions include:

* Are the expected planar faces present?
* Do fillets appear as cylinders?
* Do rounded corners appear as spheres?
* Are repeated features recognized consistently?

In a simple mechanical part, good output often consists of a small number of
common planes, repeated cylinders with similar radii, and only a few leftovers.

2. Examine the leftovers
========================

``leftovers`` show what still needs manual interpretation.

Large leftover regions often indicate one of three things:

* the part contains geometry that is not well approximated by planes,
  cylinders, or spheres
* the mesh is noisy or irregular
* the working section is still too large to interpret comfortably

If too much of the mesh appears in ``leftovers``, it may be better to refine
the working section, identify more symmetry, or redesign that area manually
instead of trying to automate it further.

3. Examine the generated code
=============================

The generated ``code_lines`` are intentionally written in Algebra mode and use
``Plane * Pos`` structure to make repeated placement patterns easier to spot.

This often helps answer questions such as:

* which faces lie on the same construction plane?
* which circles belong to the same sketch?
* which cylindrical or spherical regions are repeated instances of one feature?

Treat this code as an annotated report, not necessarily as the final model.

For planar parts in particular, the generated lines are often naturally grouped
by plane. A sequence such as ``Plane.XY.offset(...)`` with a few repeated
offset values usually indicates related structure that may belong to one sketch
or one construction stage.

Worked Example: Filleted Box
****************************

As a controlled example, consider a filleted box:

.. code-block:: build123d

    fillet_box = fillet(Box(1, 1, 1).edges(), 0.1)

Running ``detect_primitives`` on this geometry produces output like:

.. code-block:: build123d

    r00 = Plane.XY.offset(-0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    c01 = Plane.XY.offset(-0.4) * Pos(0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c02 = Plane.XY.offset(-0.4) * Pos(-0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c03 = Plane.XY.offset(-0.4) * Pos(-0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c04 = Plane.XY.offset(-0.4) * Pos(0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    r05 = Plane.XY.offset(0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    r06 = Plane.YZ.offset(-0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    c07 = Plane.YZ.offset(-0.4) * Pos(-0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c08 = Plane.YZ.offset(-0.4) * Pos(-0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c09 = Plane.YZ.offset(-0.4) * Pos(0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c10 = Plane.YZ.offset(-0.4) * Pos(0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    r11 = Plane.YZ.offset(0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    r12 = Plane.ZX.offset(-0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    c13 = Plane.ZX.offset(-0.4) * Pos(-0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c14 = Plane.ZX.offset(-0.4) * Pos(-0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c15 = Plane.ZX.offset(-0.4) * Pos(0.4, -0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    c16 = Plane.ZX.offset(-0.4) * Pos(0.4, 0.4) * Face.extrude(Circle(0.0999996).edge(), (0, 0, 0.8))
    r17 = Plane.ZX.offset(0.5) * Pos(-0.4, -0.4) * Rectangle(0.8, 0.8, align=Align.MIN)
    s18 = Pos((0.399999, -0.399999, 0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s19 = Pos((-0.399999, 0.399999, -0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s20 = Pos((-0.399999, -0.399999, -0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s21 = Pos((0.399999, 0.399999, -0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s22 = Pos((-0.399999, 0.400026, 0.399999)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s23 = Pos((-0.399999, -0.399999, 0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s24 = Pos((0.399999, 0.400026, 0.399999)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]
    s25 = Pos((0.399999, -0.399999, -0.400026)) * Sphere(0.099983).faces().filter_by(GeomType.SPHERE)[0]

This output is informative in several ways:

* the six box faces appear as rectangles on three principal planes
* the edge fillets appear as cylinders grouped around those same planes
* the corner blends appear as spheres near the eight cube corners

The generated code is also structured by plane:

* ``Plane.XY.offset(...)`` appears with three distinct offsets
* ``Plane.YZ.offset(...)`` appears with three distinct offsets
* ``Plane.ZX.offset(...)`` appears with three distinct offsets

That organization is often more useful than any one primitive by itself
because it suggests how the model could be regrouped into sketches and
construction steps.

Although this output is correct and useful, it still does not represent the
best final build123d model. The original design intent is much simpler:

.. code-block:: build123d

    fillet(Box(1, 1, 1).edges(), 0.1)

That is a good example of the main lesson of this tutorial: the generated code
helps reveal structure, but the final model should usually be rewritten in a
cleaner, higher-level form.

Turning Primitive Hints into Sketches
*************************************

Once repeated planes become obvious in ``code_lines``, start grouping related
features into sketches and features of your own.

For example:

* several rectangles on ``Plane.XY`` may indicate one base sketch and one or
  more extrusions
* repeated circles on one plane may indicate hole or boss locations
* a collection of cylinders with the same radius may indicate that a fillet or
  round was part of the original design intent

The generated code is often most useful when treated as:

* a list of candidate construction planes
* a list of likely sketch elements
* a list of repeated primitive sizes and placements

Signs of Good Output
********************

``detect_primitives`` is most helpful when:

* the mesh is reasonably clean
* the part is mostly mechanical
* many surfaces are planar, cylindrical, or spherical
* there are clear planes of symmetry or repeated features

In these cases, primitives and generated code often cluster into obvious
reconstruction steps.

Signs of Poor Output
********************

Expect more manual work when:

* the mesh contains freeform surfaces
* the STL is noisy or heavily tessellated
* the part has no obvious symmetry
* many important regions remain in ``leftovers``
* the generated code contains many tiny or redundant fragments

When this happens, it may be faster to use the mesh only as a visual reference
and rebuild the part manually from dimensions and intent.

Summary
*******

The STL reconstruction workflow in build123d is:

1. analyze the part as a designer, not as a mesh processor
2. isolate the smallest useful region with symmetry and splitting
3. cache that region as BREP
4. run :func:`~build123d.detect_primitives`
5. inspect primitives, leftovers, and code
6. rebuild the part intentionally in build123d

The most useful mindset is to treat ``detect_primitives`` as a design assistant.
It can show where the planes, cylinders, and spheres probably are, but the
final parametric model still comes from careful human interpretation.
