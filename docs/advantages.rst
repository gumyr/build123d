As mentioned previously, the most significant advantage is that build123d is more pythonic.
Specifically:

Standard Python Context Manager
===============================

The creation of standard instance variables, looping and other normal python operations
is enabled by the replacement of method chaining (fluent programming) with a standard
python context manager.

.. code-block:: python

    # CadQuery Fluent API
    pillow_block = (cq.Workplane("XY")
        .box(height, width, thickness)
        .edges("|Z")
        .fillet(fillet)
        .faces(">Z")
        .workplane()
        ...
    )

.. code-block:: python

    # build123d API
    with BuildPart() as pillow_block:
        with BuildSketch() as plan:
            Rectangle(width, height)
            fillet(plan.vertices(), radius=fillet)
        extrude(thickness)
        ...

The use of the standard `with` block allows standard python instructions to be
inserted anyway in the code flow.  One can insert a CQ-editor `debug` or standard `print`
statement anywhere in the code without impacting functionality. Simple python
`for` loops can be used to repetitively create objects instead of forcing users
into using more complex `lambda` and `iter` operations.

Instantiated Objects
====================

Each object and operation is now a class instantiation that interacts with the
active context implicitly for the user. These instantiations can be assigned to
an instance variable as with standard python programming for direct use.

.. code-block:: python

    with BuildSketch() as plan:
        r = Rectangle(width, height)
        print(r.area)
        ...

Operators
=========

New operators have been created to extract information from objects created previously
in the code. The `@` operator extracts the position along an Edge or Wire while the
`%` operator extracts the tangent along an Edge or Wire. The position parameter are float
values between 0.0 and 1.0 which represent the beginning and end of the line. In the following
example, a spline is created from the end of l5 (`l5 @ 1`) to the beginning of l6 (`l6 @ 0`)
with tangents equal to the tangents of l5 and l6 at their end and beginning respectively.
Being able to extract information from existing features allows the user to "snap" new
features to these points without knowing their numeric values.

.. code-block:: python

    with BuildLine() as outline:
        ...
        l5 = Polyline(...)
        l6 = Polyline(...)
        Spline(l5 @ 1, l6 @ 0, tangents=(l5 % 1, l6 % 0))


Last Operation Objects
======================
All of the `vertices()`, `edges()`, `faces()`, and `solids()` methods of the builders
can either return all of the objects requested or just the objects changed during the
last operation. This allows the user to easily access features for further refinement,
as shown in the following code where the final line selects the edges that were added
by the last operation and fillets them. Such a selection would be quite difficult
otherwise.

.. literalinclude:: ../examples/intersecting_pipes.py
    :lines: 30, 39-49


Extensions
==========
Extending build123d is relatively simple in that custom objects or operations
can be created as new classes without the need to monkey patch any of the
core functionality. These new classes will be seen in IDEs which is not
possible with monkey patching the core CadQuery classes.

Enums
=====

All `Literal` strings have been replaced with `Enum` which allows IDEs to
prompt users for valid options without having to refer to documentation.

Selectors replaced by Lists
===========================
String based selectors have been replaced with standard python filters and
sorting which opens up the full functionality of python lists. To aid the 
user, common operations have been optimized as shown here along with
a fully custom selection:

.. code-block:: python

    top = rail.faces().filter_by_normal(Axis.Z)[-1]
    ...
    outside_vertices = filter(
        lambda v: (v.Y == 0.0 or v.Y == height) and -width / 2 < v.X < width / 2,
        din.vertices(),
    )
