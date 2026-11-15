.. _faq:

##########################
Frequently asked questions
##########################

These are questions that come up again and again from people using
build123d, with short answers and a pointer to where each is covered in
full. The code is the same in builder and algebra mode unless an answer says
otherwise.

*******************
Getting started
*******************

How should I install build123d?
===============================

In a virtual environment of its own, with ``pip install build123d``. The
installation page in Getting Started has the details and the alternatives.

Why does nothing appear in my viewer?
=====================================

Almost always because the editor is running a different Python from the one
build123d and the viewer were installed into. Check which interpreter the
editor has selected, and that ``import build123d`` works in it.

Is build123d GPU accelerated?
=============================

No. The geometry is computed by the OpenCascade kernel, which runs on the
CPU. A viewer uses the GPU to draw the result, and that is all.

.. _are_glob_imports_bad_practice:

Isn’t ``from build123d import *`` bad practice?
===============================================

Glob imports like ``from build123d import *`` are generally frowned upon when writing software, and for
good reason. They pollute the global namespace, cause confusing collisions, and are not future-proof, as
future changes to the library being imported could collide with other names. It would be much safer to do 
something like ``import build123d as bd`` and then reference every item with, for example, ``bd.BuildPart()``.
If your goal is to integrate build123d into a larger piece of software, which many people work on, or where
long-term maintainability is a priority, using this approach is definitely a good idea! Why then, are
glob imports so often used in build123d code and official examples?

build123d is most commonly used not as a library within a larger application, but as a `Domain-Specific Language <https://en.wikipedia.org/wiki/Domain-specific_language>`__
which, together with something like the OCP CAD Viewer, acts as the user interface for a CAD application.
Writing build123d often involves live coding in a REPL or typing in editors with limited space due to
the rest of the CAD GUI taking up screen space. Scripts are usually centred around build123d usage, with
usage of other libraries being limited enough that naming conflicts are easily avoided. In this context,
it’s entirely reasonable to prioritise developer ergonomics over “correctness” by making build123d’s primitives
available in the global namespace.

When a script does need explicit imports, there is a tool to write them.
``deglob.py``, in the ``tools`` folder of the build123d repository, reads a
script, finds the build123d names it uses, and prints the import line to
replace the glob with:

.. code-block:: text

    $ python tools/deglob.py my_script.py
    from build123d import Axis, Box, BuildPart, fillet

With ``--write`` it makes the replacement in the file.

***********************
Sketches and planes
***********************

Where is my sketch actually drawn?
==================================

Flat, in its own X and Y, whatever plane it was given. The plane is applied
afterwards, to the finished sketch. So inside a sketch, positions and
selections are in the sketch's own coordinates, where Z is always zero.
Builders do not inherit a placement from the builder they are nested in:
each draws at its own origin and is placed when it finishes.
:ref:`sketching_on_other_planes` covers this.

Why is the origin of a sketch on a face at the centre of the face?
==================================================================

A face has no natural origin, so ``Plane(face)`` puts one at its centre. To
measure from somewhere else, move the origin there:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [face_origin]
    :end-before: [face_origin]

:ref:`placing_sketches` has more.

Why does my sketch come out turned on a face?
=============================================

A face says which way it faces and not which way is "along", so
``Plane(face)`` has to choose an X direction, and it may not be yours. Say
which way X should point:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [face_x_dir]
    :end-before: [face_x_dir]

Why does extrude go the wrong way?
==================================

``extrude`` goes the way the sketch faces. A sketch on a face of a part
faces out of the part, so a positive amount adds material outside and a
negative one cuts in:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [extrude_direction]
    :end-before: [extrude_direction]

Why is my mirrored part in the wrong place?
===========================================

``mirror`` reflects in a plane, and unless told otherwise that plane is
``Plane.XZ``, through the origin. A part away from the origin lands on the
other side of it. Name the plane you mean, which can be a face of the part:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [mirror_plane]
    :end-before: [mirror_plane]

**********************
Lines and outlines
**********************

Why is there no “current point” when drawing lines?
===================================================

build123d keeps no hidden cursor. Each object says where it starts, and to
carry on from the last one you ask that one where it ended:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [current_point]
    :end-before: [current_point]

Nothing is typed twice, and the pieces cannot drift apart when a dimension
changes. :ref:`drawing_with_constraints` covers ``@`` and its relatives.

Why will my outline not make a face?
====================================

Because it is not closed. ``make_face`` needs the lines to return to where
they started, and raises ``ValueError: Face can only be created with closed
wires`` when they do not:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [closed_outline]
    :end-before: [closed_outline]

End the last object at ``first @ 0``, or give ``Polyline`` ``close=True``.
An outline that crosses itself will not make a valid face either.

*************
Selecting
*************

Why does my selection pick a different edge after I change the model?
=====================================================================

Because it was taken by position in an unsorted list. ``part.edges()[3]``
means "whichever edge the kernel happened to list fourth", and that changes
when the model does. Sort, group or filter first, so that the selection
describes the feature: ``part.edges().sort_by(Axis.Z)[-1]`` is the highest
edge whatever else changes. :ref:`selecting_features` covers how.

Why does my selector return nothing?
====================================

Usually because the test does not fit the kind of feature it is applied to:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [selector_kinds]
    :end-before: [selector_kinds]

An edge can be a ``CIRCLE`` and a face a ``CYLINDER``, never the reverse.
``filter_by(Axis.Z)`` keeps straight edges that run along Z, and faces whose
normal or axis is along Z, so a curved edge is never matched by it.

How do I select what the last operation made?
=============================================

Ask the selector for it. ``Select.LAST`` gives the features the last
operation brought in or created, and ``Select.NEW`` only those that existed
in no form before:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [select_last]
    :end-before: [select_last]

This works on shapes made in algebra mode too. See :ref:`when`.

**********
Solids
**********

What does ``mode`` do?
======================

It says how a new object combines with what a builder already holds:
``Mode.ADD`` joins it on, ``Mode.SUBTRACT`` cuts it out, ``Mode.INTERSECT``
keeps what the two share, ``Mode.REPLACE`` discards what was there, and
``Mode.PRIVATE`` makes the object without adding it at all. In algebra mode
the first three are ``+``, ``-`` and ``&``.

Why does my fillet fail?
========================

Most often because the radius is too large for the part: a fillet cannot be
wider than the material beside the edge. The error says so, and
``max_fillet`` will find the limit:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [fillet_limit]
    :end-before: [fillet_limit]

Fillets also fail more on complicated geometry, which is one reason to
leave them until last; see :ref:`tips`.

Why does an operation fail, or give an invalid part?
====================================================

The usual causes are features much smaller than the rest of the model,
shapes that touch themselves along an edge or at a point, and operations
applied to a part that was already invalid. Check ``part.is_valid`` after
the step you suspect, and see :ref:`tips` for ways round.

Why is my model slow to build?
==============================

Operations on solids are the expensive part, and they get slower as the
part gets more complicated. Do as much as possible in the sketch, leave
fillets until last, use shallow copies for repeated parts, and group
finished parts in a ``Compound`` in preference to fusing them.
:ref:`algebra_performance` has more on combining many objects.

************************
Assemblies and files
************************

Why did my part move when I attached a joint?
=============================================

That is what ``attach`` is for. It is called on a joint of the part that
stays put and given a joint of the part to move:

.. literalinclude:: /how_to/faq.py
    :language: build123d
    :start-after: [attach_moves]
    :end-before: [attach_moves]

See :ref:`joints`.

Should I export STEP or STL?
============================

STEP for anything that will be opened in another CAD system: it holds the
exact surfaces, with labels and colours. STL for a slicer: it holds
triangles and nothing else. :ref:`import_export` compares all the formats.

Why does ``import_dxf`` give me lines and not faces?
====================================================

A DXF file holds lines and arcs, and that is what comes back, as separate
edges. Pass the ones that form a closed outline to ``make_face``.
