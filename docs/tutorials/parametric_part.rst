.. _tutorial_parametric_part:

#################
A parametric part
#################

Every tutorial so far has ended by inviting you to change a number at the
top of the file and watch the part follow. That is what *parametric*
means: the part is described in terms of values that can change.

Those values have all been dimensions. They do not have to be. A part
exists to do a job, and the job can be the parameter: *this beam must carry
200 newtons at its end and bend by no more than a millimetre*. How deep the
beam has to be is then something for the code to work out.

In this tutorial you will make a ``Beam`` that is described that way, and
you will make it an object of your own - one that is created, placed and
combined exactly like ``Box`` or ``Cylinder``:

.. image:: /tutorials/assets/parametric_part/beam_bracket.svg
    :align: center
    :width: 60%

Along the way you will:

* describe a part by what it must do, not by its size,
* look up the properties of a real material,
* calculate a dimension from those requirements,
* turn the design into a custom object, a class of your own,
* use that object like any built-in one, and
* see why a custom object is a better home for a design than a function.

It takes about twenty-five minutes and is the last of the series. It adds
no new ways of making shapes, and it asks a little more Python of you than
the others: you need to have met a ``class`` before. How the builder and
algebra tabs on this page work is described in
:ref:`tutorial_sketch_then_extrude`.

***************************
Step 1: The requirement
***************************

Start a new Python file with the imports and the requirement.

.. literalinclude:: /tutorials/parametric_part.py
    :language: build123d
    :start-after: [setup]
    :end-before: [setup]

The beam is fixed at one end and loaded at the other, like a shelf bracket
or a diving board. It is ``length`` long and ``width`` wide, it carries
``load``, and its free end may move down by at most ``max_deflection``.
Notice what is missing: nothing says how deep the beam is.

The material comes from ``bd_materials``, a library of real materials that
is installed with build123d. ``metals.aluminum()`` is a common aluminium
alloy, and it knows its own physical properties. ``FinishedMaterial``,
imported beside it, is the type of every material in the library, and is
needed in step 4.

Lengths are in millimetres and the load is in newtons. With those two,
stiffness comes out in megapascals, and no other conversions are needed.

***************************************************
Step 2: From the requirement to a dimension
***************************************************

How much a beam bends depends on how stiff its material is and on the
shape of its cross-section. For a rectangular beam, the depth that bends by
exactly ``max_deflection`` under the load can be written in one line.

.. literalinclude:: /tutorials/parametric_part.py
    :language: build123d
    :start-after: [sizing]
    :end-before: [sizing]

Run it and it prints ``25.38...``: an aluminium beam of this length and
width has to be a little over 25 mm deep.

``material.material.modulus_of_elasticity`` is the stiffness of the
aluminium. ``bd_materials`` gives it as a range in gigapascals, because
real material varies; ``.min`` takes the less stiff end of the range, to be
on the safe side, and multiplying by 1000 turns gigapascals into
megapascals.

.. dropdown:: Where the formula comes from

    A beam fixed at one end, with a load :math:`F` on the other, bends at
    its free end by

    .. math::

        \delta = \frac{F L^3}{3 E I}

    where :math:`L` is its length, :math:`E` is the modulus of elasticity
    of the material and :math:`I` is the second moment of area of the
    cross-section. For a rectangle :math:`b` wide and :math:`h` deep,

    .. math::

        I = \frac{b h^3}{12}

    Put the second into the first and solve for the depth:

    .. math::

        h = \sqrt[3]{\frac{4 F L^3}{E\, b\, \delta}}

    which is the line in the code, with ``load`` for :math:`F`,
    ``max_deflection`` for :math:`\delta` and ``section_depth`` for
    :math:`h`.

.. warning::

    This sizes the beam for stiffness only. It does not check that the
    material is strong enough to carry the load, and it is here to show
    how a requirement can drive a part, not as a way to design a real
    structure.

*********************
Step 3: Draw it
*********************

With the depth known, the beam is the first tutorial again: its
cross-section is a rectangle, drawn on ``Plane.YZ`` so that it faces along
X, and extruded by the length.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [draw_builder]
            :end-before: [draw_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [draw_algebra]
            :end-before: [draw_algebra]

.. image:: /tutorials/assets/parametric_part/beam_drawn.svg
    :align: center
    :width: 55%

The cross-section is in red. The fixed end of the beam is at the origin and
the beam runs out along X.

The shape is as simple as a shape can be, and that is deliberate. What is
new is where its depth came from: change ``load`` to 800 and the beam is
about 40 mm deep; change ``max_deflection`` to 2 and it is about 20 mm.

**********************************
Step 4: Make it an object
**********************************

The file now makes one beam. A design worth having is worth using more than
once, so the next step is to give it a name and make it something that can
be asked for: a ``Beam``, to sit beside ``Box`` and ``Cylinder``.

Every ready-made object in build123d is a Python class built on a small
set of base classes, and you can build on them too. For a solid the base
class is :class:`~objects_part.BasePartObject`. Replace steps 2 and 3 with
this:

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [object_builder]
            :end-before: [object_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [object_algebra]
            :end-before: [object_algebra]

The class has four parts, and every custom object has the same four:

#. **It inherits from a base class.** ``class Beam(BasePartObject)`` says
   that a ``Beam`` is a part, and brings with it everything a part can do.
#. **Its parameters are the arguments of** ``__init__``. Here they are the
   requirement - ``length``, ``load``, ``max_deflection``, ``material`` and
   ``width`` - followed by three that every built-in object has:
   ``rotation``, ``align`` and ``mode``.
   Each is followed by a colon and its type, such as ``length: float``.
   These *type hints* change nothing when the code runs, but they tell
   whoever uses a ``Beam``, and their editor, what each argument should
   be. build123d itself is written this way, and its own types are there
   to be used: ``RotationLike`` is anything that describes a rotation, and
   ``FinishedMaterial`` is what ``bd_materials`` supplies.
#. **It builds the shape with the ordinary tools.** These are the lines of
   steps 2 and 3, unchanged, in whichever mode you prefer.
#. **It hands the finished shape to** ``super().__init__``, together with
   ``rotation``, ``align`` and ``mode``. The base class takes it from
   there.

The last three lines keep the answer. ``self.section_depth`` records the
depth that was calculated, so that it can be read back from the beam.
``self.material`` tells the beam what it is made of, and ``self.label``
gives it a name - the material followed by "Beam" - which is what a viewer
shows beside the part.

.. Remove this note when anytree is removed (the Assembly work planned for
   after v1.0.0): anytree is what reserves these names.

.. note::

    At present some attribute names are already taken on a part.
    ``self.height = ...`` and ``self.depth = ...`` both fail with
    *property ... has no setter*, which is why the depth is stored under
    the name ``section_depth``.

The last line of the file makes a beam, and it is the same solid as the one
in step 3. Which mode the class is *written* in makes no difference at all
to how it is *used*: either version works in both modes.

From here on the class stays where it is, and each step shows only what is
added below it.

***********************************************
Step 5: Use it like a built-in object
***********************************************

Here is what the base class has bought. A wall plate carries two beams,
side by side.

.. tab-set::

    .. tab-item:: Builder
        :sync: builder

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [use_builder]
            :end-before: [use_builder]

    .. tab-item:: Algebra
        :sync: algebra

        .. literalinclude:: /tutorials/parametric_part.py
            :language: build123d
            :start-after: [use_algebra]
            :end-before: [use_algebra]

.. image:: /tutorials/assets/parametric_part/beam_bracket.svg
    :align: center
    :width: 60%

Read the builder version beside step 4 of :ref:`tutorial_combining_solids`,
where cylinders were placed in a pattern. It is the same code with a
different object. Inside a ``Locations`` block a ``Beam`` is made at every
location and joined to the part, without being told to; in algebra mode it
goes on the right of a ``*`` like any other shape.

The three arguments passed on to the base class work as well:

* ``rotation=(0, -90, 0)`` stands the beam on end;
* ``align=(Align.MIN, Align.CENTER, Align.MIN)`` puts its lower edge, not
  its centre line, at the origin; and
* ``mode=Mode.SUBTRACT`` cuts a beam-shaped socket out of whatever is being
  built.

None of that was written in the class. It came with ``BasePartObject``.

****************************************
Step 6: Change the requirement
****************************************

A ``Beam`` is asked for by what it must do, so different answers are one
argument away. Here is the same requirement in three materials. This step
is the same in both modes.

.. literalinclude:: /tutorials/parametric_part.py
    :language: build123d
    :start-after: [materials]
    :end-before: [materials]

.. code-block:: text

    Alu_G6061_T6 Beam: 25.4 mm deep, 411 g
    MildSteel_PLAIN_CARBON_GENERIC Beam: 17.7 mm deep, 828 g
    Titanium_GR5_ANNEALED Beam: 21.4 mm deep, 569 g

.. image:: /tutorials/assets/parametric_part/beam_materials.svg
    :align: center
    :width: 60%

From the back: aluminium, steel and titanium. Each beam is a different
depth, because each material is a different stiffness, and all three bend
by the same millimetre under the same load.

``beam.label`` and ``beam.section_depth`` are the values the class stored.
``beam.mass()`` is
something every part can do once it has a material, and it gives the
answer in grams. Steel makes the slimmest beam and the heaviest; aluminium
makes the deepest and the lightest. That is a real design decision, and it
took a three-line loop to lay out.

Try a ``load`` of 800 or a ``max_deflection`` of 0.25 at the top of the
file, or add ``metals.stainless()`` to the loop.

*******************************************
Why an object, and not a function?
*******************************************

A Python function that takes the same arguments and returns a part looks
like less work than a class, and it is often the first thing people try. It
is not recommended, because a function knows nothing about the builder it
is called from:

* A function written in **builder mode**, called inside your
  ``BuildPart``, adds nothing to it. Its part is returned and then quietly
  dropped unless you pass it to
  :func:`~operations_generic.insert` yourself.
* A function written in **algebra mode**, called inside your ``BuildPart``,
  is worse: the shapes it makes on the way try to join the part you are
  building. Some are added to it where they do not belong, and others
  stop the program with an error.
* A function has no ``rotation``, ``align`` or ``mode`` unless you write
  each of them yourself.
* What it returns is a plain part. It is not a ``Beam``, and it has no
  ``section_depth`` to read back.

A custom object has none of these problems. Whatever is made inside it is
kept apart from the model it is used in, and the finished object arrives
once, in the place and in the mode it was asked for. A function that works
in a small script can misbehave in a large model; a custom object behaves
the same everywhere. :ref:`custom_objects` describes the base classes for
sketches and lines as well as parts.

********************
What you learned
********************

* The parameters of a part do not have to be dimensions. They can be what
  the part must do, with the dimensions calculated from them.
* ``bd_materials`` supplies the properties of real materials, and a part
  with a ``material`` can report its ``mass()``.
* A **custom object** is a class built on a base class -
  :class:`~objects_part.BasePartObject` for a solid - that takes its
  parameters in ``__init__``, builds a shape, and hands it to
  ``super().__init__``.
* A custom object is placed, rotated, aligned and combined exactly like a
  built-in one, in both modes, whichever mode it was written in.
* Package a design as a custom object, not as a function.

***********************
The end of the series
***********************

These seven tutorials have followed one method throughout: draw a sketch,
make it a solid, select what was made, and build on it - with every value
given a name, so that the part can change. That is enough to model a great
many real parts, and now to make them objects of your own.

:ref:`where_next` suggests what to read from here, and :ref:`cheat_sheet`
lists every object and operation on one page.
