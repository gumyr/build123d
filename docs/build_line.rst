#########
BuildLine
#########

BuildLine is a python context manager that is used to create one dimensional
objects - objects with the property of length but not area - that are typically
used as part of a BuildSketch sketch or a BuildPart path.

The complete API for BuildLine is located at the end of this section.

*******************
Basic Functionality
*******************

The following is a simple BuildLine example:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 1]
    :end-before: [Ex. 1]

The ``with`` statement creates the ``BuildLine`` context manager with the
identifier ``example_1``. The objects and operations that are within the
scope (i.e. indented) of this context will contribute towards the object
being created by the context manager.  For ``BuildLine``, this object is
``line`` and it's referenced as ``example_1.line``.

The first object in this example is a ``Line`` object which is used to create
a straight line from coordinates (0,0) to (2,0) on the default XY plane.
The second object is a ``ThreePointArc`` that starts and ends at the two
ends of the line.

.. image:: assets/buildline_example_1.svg
    :align: center

***********
Constraints
***********

Building with constraints enables the designer to capture design intent and
add a high degree of robustness to their designs.  The following sections
describe creating positional and tangential constraints as well as using
object attributes to enable this type of design.

@ ``position_at`` Operator
===========================

In the previous example, the ``ThreePointArc`` started and ended at the
two ends of the ``Line`` but this was done by referring to the same
point ``(0,0)`` and ``(2,0)``.  This can be improved upon by specifying
constraints that lock the arc to those two end points, as follows:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 2]
    :end-before: [Ex. 2]

Here instance variables ``l1`` and ``l2`` are assigned to the two BuildLine
objects and the ``ThreePointArc`` references the beginning of the straight
line with ``l1 @ 0`` and the end with ``l1 @ 1``.  The ``@`` operator takes
a float (or integer) parameter between 0 and 1 and determines a position
at this fractional position along the line's length.

Values outside the usual 0-to-1 range are also accepted by ``position_at``,
``tangent_at``, and ``location_at``. On an ``Edge``, the underlying curve is
evaluated beyond the trimmed edge where supported: open curves can extrapolate
and periodic curves can wrap. On a ``Wire``, out-of-range values are clamped to
the first or last point (and its corresponding tangent or location frame).

This example can be improved on further by calculating the mid-point
of the arc as follows:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 3]
    :end-before: [Ex. 3]

Here ``l1 @ 0.5`` finds the center of ``l1`` while ``l1 @ 0.5 + (0, 1)`` does
a vector addition to generate the point ``(1,1)``.

To make the design even more parametric, the height of the arc can be calculated
from ``l1`` as follows:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 4]
    :end-before: [Ex. 4]

The arc height is now calculated as ``(0, l1.length / 2)`` by using the ``length``
property of ``Edge`` and ``Wire`` shapes.  At this point the ``ThreePointArc`` is
fully parametric and able to generate the same shape for any horizontal line.

% ``tangent_at`` Operator
=========================

The other operator that is commonly used within BuildLine is ``%`` the tangent at
operator. Here is another example:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 5]
    :end-before: [Ex. 5]

which generates (note that the circles show line junctions):

.. image:: assets/buildline_example_5.svg
    :align: center

The ``JernArc`` has the following parameters:

* ``start=l2 @ 1`` - start the arc at the end of line ``l2``,
* ``tangent=l2 % 1`` - the tangent of the arc at the start point is equal to the ``l2``\'s,
  tangent at its end (shown as a dashed line)
* ``radius=0.5`` - the radius of the arc, and
* ``arc_size=90`` the angular size of the arc.

The final line starts at the end of ``l3`` and ends at a point calculated from the length
of ``l2`` and the radius of arc ``l3``.

Building with constraints as shown here will ensure that your designs both fully represent
design intent and are robust to design changes.

************************
BuildLine to BuildSketch
************************

As mentioned previously, one of the two primary reasons to create BuildLine objects is to
use them in BuildSketch.  When a BuildLine context manager exits and is within the scope of a
BuildSketch context manager it will transfer the generated line to BuildSketch. The BuildSketch
:meth:`~operations_sketch.make_face` or :meth:`~operations_sketch.make_hull`  operations are then used
to transform the line (specifically a list of Edges) into a Face - the native BuildSketch
objects.

Here is an example of using BuildLine to create an object that otherwise might be
difficult to create:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 6]
    :end-before: [Ex. 6]

which generates:

.. image:: assets/buildline_example_6.svg
    :align: center

.. note:: SVG import to BuildLine

    The BuildLine code used in this example was generated by translating a SVG file
    into BuildLine source code with the :func:`~importers.import_svg_as_buildline_code`
    function. For example:

    .. code::

        svg_code, builder_name = import_svg_as_buildline_code("club.svg")

    would translate the "club.svg" image file's paths into BuildLine code much like
    that shown above. From there it's easy for a user to add constraints or otherwise
    enhance the original image and use it in their design.

**********************
BuildLine to BuildPart
**********************

The other primary reasons to use BuildLine is to create paths for BuildPart
:meth:`~operations_generic.sweep` operations. Here some curved and straight segments
define a path:

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 7]
    :end-before: [Ex. 7]

which generates:

.. image:: assets/buildline_example_7.svg
    :align: center

There are few things to note from this example:

* The @ and % operators are used to create a plane normal to the beginning of the
  path with which to create the circular section used by the sweep operation
  (this plane is not one of the ordinal planes).
* Both the path generated by BuildLine and the section generated by BuildSketch
  have been transferred to BuildPart when each of them exit.
* The BuildPart ``Sweep`` operation is using the path and section previously
  transferred to it (as "pending" objects) as parameters of the sweep. The
  ``Sweep`` operation "consumes" these pending objects as to not interfere with
  subsequence operations.

******************************
Publishing to other Placements
******************************

So far all of the examples were created in local ``Plane.XY`` coordinates and published
to the default placement. Sometimes it's convenient to publish the completed line to
another placement, especially when creating paths for BuildPart ``Sweep`` operations.

.. literalinclude:: objects_1d.py
    :language: build123d
    :start-after: [Ex. 8]
    :end-before: [Ex. 8]

which generates:

.. image:: assets/buildline_example_8.svg
    :align: center

Here the ``BuildLine`` object is constructed in local coordinates and the completed
line is published to ``Plane.YZ``. The local, unplaced result is available as
``line_local`` while the placed result is available as ``line``.

There are a few rules to keep in mind when publishing ``BuildLine`` output to
alternate placements:

#. ``BuildLine`` accepts a single placement, unlike ``BuildPart`` and ``BuildSketch``
   which can publish to multiple placements.
#. Values entered as tuples such as ``(1, 2)`` or ``(1, 2, 3)`` are interpreted in
   the builder's local coordinate system during construction. They are not converted
   by the placement as they are entered.
#. The placement is applied once to the completed line when ``line`` is requested or
   when the ``BuildLine`` exits and publishes to its parent.
#. Use ``line_local`` when you want to inspect or select from the construction result
   before placement. Use ``line`` when you want the published result.

.. code-block:: build123d

    with BuildLine(Plane.YZ) as path:
        Line((0, 0), (1, 0))

    show_object(path.line_local)  # line from (0, 0, 0) to (1, 0, 0)
    show_object(path.line)        # same line published to Plane.YZ

.. note::
    In earlier versions, ``BuildLine`` used the input plane during construction:
    tuple points were localized to that plane immediately. ``BuildLine`` now follows
    the same model as ``BuildPart`` and ``BuildSketch``: construction happens in the
    local coordinate system and the placement is applied at publication time.

    This does not restrict ``BuildLine`` to planar curves. Curve objects can still
    create non-planar geometry when given enough 3D information; the placement only
    controls where the completed curve is published.

Finally, a ``BuildLine`` placement need not be one of the predefined ordinal planes.
It can be any ``Plane``, ``Face``, or ``Location``, including one derived from a
surface of a ``BuildPart`` part that is currently under construction.

*********
Reference
*********
.. py:module:: build_line

.. autoclass:: BuildLine
    :members:
