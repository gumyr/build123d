Moving Objects
==============

In build123d, there are several methods to move objects. These methods vary 
based on the mode of operation and provide flexibility for object placement 
and orientation. Below, we outline the three main approaches to moving objects: 
builder mode, algebra mode, and direct manipulation methods.

Builder Mode
------------
In builder mode, object locations are defined before the objects themselves are 
created. This approach ensures that objects are positioned correctly during the 
construction process. The following tools are commonly used to specify locations:

1. :class:`~build_common.Locations` Use this to define a specific location for the objects within the `with` block.
2. :class:`~build_common.GridLocations` Arrange objects in a grid pattern.
3. :class:`~build_common.PolarLocations` Position objects in a circular pattern.
4. :class:`~build_common.HexLocations` Arrange objects in a hexagonal grid.

.. note::
   The location(s) of an object must be defined prior to its creation when using builder mode.

Example:

.. code-block:: python

    with Locations((10, 20, 30)):
        Box(5, 5, 5)

Algebra Mode
------------
In algebra mode, object movement is expressed using algebraic operations. The 
:class:`~geometry.Pos` function, short for Position, represents a location, which can be combined 
with objects or planes to define placement.

1. ``Pos() * shape``: Applies a position to a shape.
2. ``Plane() * Pos() * shape``: Combines a plane with a position and applies it to a shape.

Rotation is an important concept in this mode. A :class:`~geometry.Rotation` represents a location 
with orientation values set, which can be used to define a new location or modify 
an existing one.

Example:

.. code-block:: python

    rotated_box = Rotation(45, 0, 0) * box

Direct Manipulation Methods
---------------------------
The following methods allow for direct manipulation of a shape's location and orientation 
after it has been created. These methods offer a mix of absolute and relative transformations.

Position
^^^^^^^^
- **Absolute Position:** Set the position directly.
  
.. code-block:: python

    shape.position = (x, y, z)
  
- **Relative Position:** Adjust the position incrementally.

.. code-block:: python

    shape.position += (x, y, z)
    shape.position -= (x, y, z)
  

Orientation
^^^^^^^^^^^
- **Absolute Orientation:** Set the orientation directly.

.. code-block:: python

      shape.orientation = (X, Y, Z)

- **Relative Orientation:** Adjust the orientation incrementally.

.. code-block:: python

    shape.orientation += (X, Y, Z)
    shape.orientation -= (X, Y, Z)

Movement Methods
^^^^^^^^^^^^^^^^
- **Relative Move:**

.. code-block:: python

    shape.move(Location)
  
- **Relative Move of Copy:**

.. code-block:: python

    relocated_shape = shape.moved(Location)
  
- **Absolute Move:**

.. code-block:: python

    shape.locate(Location)
  
- **Absolute Move of Copy:**

.. code-block:: python

    relocated_shape = shape.located(Location)
  

Transformation a.k.a. Translation and Rotation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    These methods don't work in the same way as the previous methods in that they don't just change
    the object's internal :class:`~geometry.Location` but transform the base object itself which
    is quite slow and potentially problematic.

- **Translation:** Move a shape relative to its current position.

.. code-block:: python

    relocated_shape = shape.translate(x, y, z)
  
- **Rotation:** Rotate a shape around a specified axis by a given angle.

.. code-block:: python

    rotated_shape = shape.rotate(Axis, angle_in_degrees)
