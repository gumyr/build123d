.. _custom_objects:

############################
Making your own objects
############################

``Box``, ``Circle`` and the rest of build123d's objects are ordinary Python
classes built on a small set of base classes, and the same base classes are
there for your own objects. A design made into a class of its own this way
can be placed, rotated, aligned, added and subtracted exactly as the
built-in objects are, in builder mode and in algebra mode.

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - To
      - use
    * - make a reusable 3D object
      - a subclass of ``BasePartObject``
    * - make a reusable 2D object
      - a subclass of ``BaseSketchObject``
    * - make a reusable line or curve
      - a subclass of ``BaseEdgeObject``, ``BaseLineObject`` or
        ``BaseCurveObject``
    * - give it rotation, alignment and a mode
      - pass them on to ``super().__init__``

***********************
Choose the base class
***********************

The base class follows from the dimension of what is being made:

.. list-table::
   :header-rows: 1

   * - Object being created
     - Base class
     - Builder
   * - 3D solid or part
     - :class:`~objects_part.BasePartObject`
     - :class:`~build_part.BuildPart`
   * - 2D face or sketch
     - :class:`~objects_sketch.BaseSketchObject`
     - :class:`~build_sketch.BuildSketch`
   * - Single 1D edge
     - :class:`~objects_curve.BaseEdgeObject`
     - :class:`~build_line.BuildLine`
   * - Connected 1D wire
     - :class:`~objects_curve.BaseLineObject`
     - :class:`~build_line.BuildLine`
   * - General 1D curve
     - :class:`~objects_curve.BaseCurveObject`
     - :class:`~build_line.BuildLine`


***********************
Write the class
***********************

A custom object follows one pattern:

#. Create a class that inherits from the base class.
#. Put the dimensions that vary in the parameters of ``__init__``, with
   ``rotation``, ``align`` and ``mode`` after them.
#. Build the shape with the ordinary build123d tools.
#. Pass the finished shape to ``super().__init__``, with the rotation,
   alignment and mode.

The shape can be built in either mode. This peg is the same object written
both ways:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/custom_objects.py
            :language: build123d
            :start-after: [class]
            :end-before: [class]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/custom_objects.py
            :language: build123d
            :start-after: [class_algebra]
            :end-before: [class_algebra]

Keeping the inputs as attributes, as ``self.diameter`` does, lets later code
ask an object what it is.

***********************
Use it
***********************

The class is used wherever a built-in object would be:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /how_to/custom_objects.py
            :language: build123d
            :start-after: [use]
            :end-before: [use]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /how_to/custom_objects.py
            :language: build123d
            :start-after: [use_algebra]
            :end-before: [use_algebra]

Because it passes ``rotation``, ``align`` and ``mode`` on to its base class,
it takes them like any other object. Here the same peg, lying down and
centred, is a tool that makes a hole:

.. literalinclude:: /how_to/custom_objects.py
    :language: build123d
    :start-after: [options]
    :end-before: [options]

***********************************
What the base class does for you
***********************************

The ``Base*Object`` class handles the Builder integration. Intermediate objects
created inside the custom object are isolated from the caller's Builder context,
so a helper ``Box``, ``Circle``, or ``Line`` used during construction doesn't
leak into the user's model. When the custom object is complete, it is published
once to the active Builder using the provided ``mode``. Any active
:class:`~build_common.Locations` context and any Builder ``placements`` are
applied at publication time, just as they are for the built-in objects.

Each built-in base class also declares which Builder it applies to. For example,
``BasePartObject`` applies to ``BuildPart`` and ``BaseSketchObject`` applies to
``BuildSketch``. If a custom object inherits from one of these base classes and
is used in the wrong Builder, build123d raises an error before the custom object
is constructed. This validation is provided by the inherited ``_applies_to``
attribute; most custom objects don't need to set it themselves unless they are
creating a new base class or intentionally changing the Builder compatibility.

A class whose shape is built in algebra mode is isolated in the same way, so
either style of class is safe to use in either mode.

***********************
A larger example
***********************

.. image:: /reference/assets/objects/card_box.svg
    :align: center

The suits cut into the lid of this playing card box are custom sketch
objects, from the :ref:`Playing Cards <playing_cards>` example. This is one
of them:

.. image:: /how_to/assets/build_line/buildline_example_6.svg
    :align: center
    :width: 30%

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /../examples/playing_cards.py
            :language: build123d
            :start-after: [Club]
            :end-before: [Club]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /../examples/playing_cards_algebra.py
            :language: build123d
            :start-after: [Club]
            :end-before: [Club]

Here the new custom object class is called ``Club`` and it's a subclass of
:class:`~objects_sketch.BaseSketchObject` because it creates a 2D sketch object.
The ``__init__`` method contains the parameters used to instantiate the custom
object: ``height``, ``rotation``, ``align``, and ``mode``. Your objects may have
different parameters, but should usually include ``mode`` so they can be added
to, subtracted from, intersected with, or kept private in a Builder.

The middle of the method creates the object itself, in this case a sketch of the
club suit. The final line calls ``super().__init__`` with the completed sketch
and passes through the ``rotation``, ``align``, and ``mode`` parameters handled
by :class:`~objects_sketch.BaseSketchObject`.

That's it. The ``Club`` object can now be used anywhere a
:class:`~objects_sketch.Circle` would be used, with either the Algebra or
Builder API.


***********************
Why not a function?
***********************

A plain Python function that builds a shape and returns it can look like a
simpler way to reuse a design. It is not recommended, because a function is
not isolated from the Builder it is called from and takes no part in
publishing its result:

* A function that uses a Builder internally creates a build of its own. Called
  inside another Builder it adds nothing to that Builder, and the active
  :class:`~build_common.Locations` are not applied to it. The returned shape
  is discarded unless the caller passes it to
  :func:`~operations_generic.insert`.
* A function written in Algebra mode is not isolated at all. Called inside a
  Builder, the intermediate objects it creates are offered to that Builder,
  which either adds them to the caller's model or raises an error - a
  ``Rectangle`` created by a function called inside a ``BuildPart`` fails
  with *BuildPart doesn't have a Rectangle object or operation*.
* A function has no ``rotation``, ``align`` or ``mode`` unless each is
  implemented by hand, so it can't be used interchangeably with the built-in
  objects.
* The result is a plain shape. It has no type of its own to test for and no
  attributes recording how it was made.

A function may work in the script it was written for and then fail when it is
reused inside a larger model. A custom object behaves the same wherever it is
used.


************
See also
************

* :ref:`tutorial_parametric_part` builds a custom part object, ``Beam``,
  step by step.
* The :ref:`Playing Cards <playing_cards>`, :ref:`Platonic Solids
  <platonic_solids>` and :ref:`Stud Wall <stud_wall>` examples each define
  custom objects.
* :ref:`how_builder_mode_works` explains how objects find their builder.
