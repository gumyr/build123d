.. _material_tutorial:
.. _tutorial_box_materials:

#############################
Materials for the hinged box
#############################

The box of :ref:`joint_tutorial` has a shape and nothing else. It is not
made of anything, so it has no weight, and in a viewer every part is the
same plain colour. In this tutorial you will say what each part is made
of - a walnut box with a brass hinge - and get this:

.. image:: /tutorials/assets/box_materials/materials_box.png
    :align: center
    :width: 70%

Along the way you will:

* give a part a material from a library of real ones,
* give a whole assembly a material, for its parts to share,
* add a surface finish,
* read back what a material is like,
* weigh each part, and the whole box, and
* see the materials in a viewer and export them for other programs.

It takes about ten minutes, and it carries on in the file you ended
:ref:`joint_tutorial` with: every step below is added to the end of that
file, and is the same in builder and algebra mode.

*******************************
Step 1: Choose the materials
*******************************

Materials come from ``bd_materials``, a library of real materials that is
installed with build123d. You met it in :ref:`tutorial_parametric_part`,
where a beam was made of aluminium. It is organised by kind: ``metals``,
``wood``, ``plastics`` and more.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [materials]
    :end-before: [materials]

Every shape has a ``material``, and giving it one is an assignment. The box
and the lid are each given walnut.

The last line gives a material to ``hinged_box``, the assembly, and that
is worth a second look. A part with no material of its own takes the
material of the assembly it is in. The two leaves, the pin and the six screws
have none, so all nine are now brass, and nothing had to be written nine
times. The box and the lid keep their walnut, because a part's own
material comes first.

*************************
Step 2: Add a finish
*************************

A real part is made and then finished: sanded, brushed, polished, plated
or painted. A finish does not change what the part is made of, but it
changes how it looks. Give the two leaves a brushed surface.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [finish]
    :end-before: [finish]

``finish=`` goes to the function that makes the material, and the result
is a material like any other, here kept in a variable and used twice. The
leaves now have a material of their own, brushed brass. The pin and the
screws still take plain brass from the assembly.

****************************************
Step 3: Ask a material what it is
****************************************

A material is more than a name. It knows the physical properties of the
real thing. Print the material of the box.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [properties]
    :end-before: [properties]

.. code-block:: text

    Hardwood_WALNUT
      # mechanical properties
      compressive_strength_parallel  46 to 58 MPa
      density                        640 kg/m³
      janka_hardness                 4800 to 5800 N
      modulus_of_elasticity          10 to 13 GPa
      modulus_of_rupture             90 to 110 MPa
      # thermal properties
      specific_heat_capacity         1200 to 1700 J/(kg·K)
      thermal_conductivity           0.12 to 0.18 W/(m·K)

What you assigned in step 1 has two layers, which is why ``material``
appears twice. ``box.material`` is the *finished* material: the substance
together with its finish. ``box.material.material`` is the substance
itself, and printing it lists what is known about it.

Most properties are given as a range, because real wood and real brass
vary from one piece to the next. Density is a single typical value, so
that a part can be weighed.

Each property can also be read on its own, and so can the finish.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [one_property]
    :end-before: [one_property]

.. code-block:: text

    640
    Brushed

The first line is the density of the walnut, in kg/m³. The second is the
finish of the brass leaf from step 2: ``finish`` is the other layer of a
finished material, beside ``material``.

*******************************
Step 4: Weigh the box
*******************************

A shape has a volume, and a material has a density, so a part with a
material has a mass.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [mass]
    :end-before: [mass]

.. code-block:: text

    box               Hardwood_WALNUT        1243.6 g
    outer leaf        Brass_C360_HALF_HARD    113.1 g
    inner leaf        Brass_C360_HALF_HARD    113.1 g
    lid               Hardwood_WALNUT         575.5 g
    pin               Brass_C360_HALF_HARD     21.4 g
    outer leaf screw  Brass_C360_HALF_HARD      2.8 g
    outer leaf screw  Brass_C360_HALF_HARD      2.8 g
    outer leaf screw  Brass_C360_HALF_HARD      2.8 g
    inner leaf screw  Brass_C360_HALF_HARD      2.8 g
    inner leaf screw  Brass_C360_HALF_HARD      2.8 g
    inner leaf screw  Brass_C360_HALF_HARD      2.8 g
    whole box                                2083.5 g
                                              2.084 kg

``mass()`` gives grams, taking the model to be in millimetres. The pin and the
screws report brass although they were never given it: that is the material of
the assembly, reaching them. The mass of an assembly is the sum of its
parts, each weighed with its own material, and ``mass(Unit.KG)`` gives the
answer in another unit.

This is a parts list with weights, and it came from the model. Change
``wood.walnut()`` to ``wood.pine()`` in step 1, or ``wall_thickness`` at
the top of the file, and it is right again.

*********************
Step 5: Look at it
*********************

Show the assembly in your viewer.

.. code-block:: build123d

    show(hinged_box)

Each part is already drawn in the colour of its material: brown for the
walnut and yellow for the brass. OCP CAD Viewer can do a good deal more.
Open its **Studio** tab and it renders the materials as they would look,
with the grain of the wood and the brushed surface of the leaves.

.. image:: /tutorials/assets/box_materials/materials_hinge.png
    :align: center
    :width: 70%

The grain and the brushing are part of the materials. Nothing was added to
the model to draw them.

***************************
Step 6: Take it elsewhere
***************************

The same appearance can be written to a file. glTF is a format made for
exchanging models with their materials, and most 3D viewers, game engines
and renderers read it.

.. literalinclude:: /tutorials/box_materials.py
    :language: build123d
    :start-after: [export]
    :end-before: [export]

``binary=True`` writes a ``.glb`` file, which holds the shapes and the
textures of the materials in one file. Open it in any glTF viewer, such as
the `Khronos glTF viewer <https://github.khronos.org/glTF-Sample-Viewer-Release>`_.

********************
What you learned
********************

* ``bd_materials`` is a library of real materials, and
  ``part.material = wood.walnut()`` gives a part one.
* A material given to an assembly is used by every part in it that has
  none of its own.
* A finish is added where the material is made:
  ``metals.brass(finish=finishes.brushed())``.
* ``part.material.material`` holds the physical properties of the
  substance.
* ``mass()`` weighs a part, or a whole assembly, in grams.
* The viewer colours each part by its material, its Studio tab renders
  them realistically, and ``export_gltf`` takes that appearance to other
  programs.

:ref:`materials` covers the rest: choosing a material by name, units,
ranges, and making a material of your own.
