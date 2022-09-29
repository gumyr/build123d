When using a GUI based CAD system the user will often click on a feature to select
it for some operation. How does a user "click" when CAD is done entirely in code?
Selectors are recipes for how to isolate a feature from a design using python
filter and sorting methods typically implemented as a set of custom python
operations.

Quick Reference
---------------

The following tables describes the build123d selectors:

+-------------+-----------------------------------+-------------------+-------------------+
| Selector    | Applicability                     | Description       | Example           |
+=============+===================================+===================+===================+
| vertices()  | BuildLine, BuildSketch, BuildPart | Vertex extraction | `part.vertices()` |
+-------------+-----------------------------------+-------------------+-------------------+
| edges()     | BuildLine, BuildSketch, BuildPart | Edge extraction   | `part.edges()`    |
+-------------+-----------------------------------+-------------------+-------------------+
| wires()     | BuildLine, BuildSketch, BuildPart | Wire extraction   | `part.wires()`    |
+-------------+-----------------------------------+-------------------+-------------------+
| faces()     | BuildSketch, BuildPart            | Face extraction   | `part.faces()`    |
+-------------+-----------------------------------+-------------------+-------------------+
| solids()    | BuildPart                         | Solid extraction  | `part.solids()`   |
+-------------+-----------------------------------+-------------------+-------------------+

+----------+--------------+--------------------------------------------------+----------------------------------+
| Operator | Operand      | Description                                      | Example                          |
+==========+==============+==================================================+==================================+
| >        | SortBy, Axis | Sort ShapeList by operand                        | `part.vertices() > Axis.Z`       |
+----------+--------------+--------------------------------------------------+----------------------------------+
| <        | SortBy, Axis | Reverse sort ShapeList by operand                | `part.faces() < Axis.Z`          |
+----------+--------------+--------------------------------------------------+----------------------------------+
| >>       | SortBy, Axis | Sort ShapeList by operand and return last value  | `part.solids() >> Axis.X`        |
+----------+--------------+--------------------------------------------------+----------------------------------+
| <<       | SortBy, Axis | Sort ShapeList by operand and return first value | `part.faces() << Axis.Y`         |
+----------+--------------+--------------------------------------------------+----------------------------------+
| %        | GeomType     | Filter ShapeList by GeomType                     | `part.edges() % GeomType.CIRCLE` |
+----------+--------------+--------------------------------------------------+----------------------------------+
| \|       | Axis         | Filter and sort ShapeList by Axis                | `part.faces() \| Axis.Z`         |
+----------+--------------+--------------------------------------------------+----------------------------------+
| []       |              | Standard python list indexing and slicing        | `part.faces()[-2:]`              |
+----------+--------------+--------------------------------------------------+----------------------------------+

The operand types are: Axis, SortBy, and GeomType. An Axis is a base object with an origin and a
direction with several predefined values such as ``Axis.X``, ``Axis.Y``, and ``Axis.Z``; however,
any Axis could be used as an operand (e.g. ``Axis((1,2,3),(0.5,0,-0.5))`` is valid) - see
:ref:`API Reference/Axis <axis>` for a complete description. SortBy and GeomType are python
Enum class described here:

.. py:module:: build_common
    :noindex:

.. autoclass:: build_common.SortBy
    :members:
    :noindex:

.. autoclass:: build_common.GeomType
    :members:
    :noindex:


ShapeList Class
---------------

The builders include methods to extract Edges, Faces, Solids, Vertices, or Wires from the objects
they are building. All of these methods return objects of a subclass of `list`, a `ShapeList` with
custom filtering and sorting methods and operations as follows. The full ShapeList API is can be
found in :ref:`API Reference/ShapeList <shape_list>`.

Custom Sorting and Filtering
----------------------------

It is important to note that standard list methods such as `sorted` or `filtered` can
be used to easily build complex selectors beyond what is available with the predefined
sorts and filters. Here is an example of a custom filters:

.. code-block:: python

    with BuildSketch() as din:
        ...
        outside_vertices = filter(
            lambda v: (v.Y == 0.0 or v.Y == height)
            and -overall_width / 2 < v.X < overall_width / 2,
            din.vertices(),
        )
