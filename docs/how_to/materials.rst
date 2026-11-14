.. _materials:

#########
Materials
#########

A shape can be told what it is made of. With a material it has a mass, a
colour, and an appearance that viewers and exported files can use.
Materials come from `bd_materials <https://github.com/bernhard-42/bd_materials>`_,
which is installed with build123d. For a guided introduction see
:ref:`material_tutorial`.

******************
Assign a material
******************

``bd_materials`` is organised by kind - ``metals``, ``wood``, ``plastics``
and others - with a function for each material. Assign the result to a
shape's ``material``.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [assign]
    :end-before: [assign]

Each function takes a ``grade`` for the particular alloy or species, and
defaults to a common one: ``metals.aluminum()`` is 6061-T6. The
`bd_materials catalogue <https://github.com/bernhard-42/bd_materials#2-materials--finishes--organised-by-manufacturing-process>`_
lists what is available.

A material can also be assigned by name:

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [by_name]
    :end-before: [by_name]

.. code-block:: text

    Titanium_GR5_ANNEALED

*************
Add a finish
*************

A finish is what is done to the surface after the part is made. Pass it
as ``finish`` when making the material.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [finish]
    :end-before: [finish]

.. code-block:: text

    Brushed

The ``finishes`` module has mechanical finishes such as ``brushed``,
``bead_blast`` and ``fine_sanding``, coatings such as ``powder_coat``, and
platings such as ``chrome`` and ``nickel_plate``. Some take arguments:
``anodize`` needs a colour.

``shape.material`` is therefore a *finished* material with three parts:

* ``material.material`` - the substance and its physical properties,
* ``material.finish`` - the finish applied, or ``None``,
* ``material.pbr`` - how it should be rendered.

********************************
Read a material's properties
********************************

Printing the substance lists everything known about it, with units.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [properties]
    :end-before: [properties]

.. code-block:: text

    Alu_G6061_T6
      # mechanical properties
      density                 2700 kg/m³
      hardness                85 to 100 HB
      modulus_of_elasticity   66 to 70 GPa
      poisson_ratio           0.32 to 0.35
      shear_modulus           25 to 28 GPa
      shear_strength          200 to 210 MPa
      tensile_strength        290 to 320 MPa
      yield_strength          240 to 280 MPa
      # thermal properties
      max_service_temp        80 to 120 °C
      melting_temperature     570 to 660 °C
      specific_heat_capacity  875 to 950 J/(kg·K)
      thermal_conductivity    130 to 180 W/(m·K)
      thermal_expansion       2.2e-05 to 2.4e-05 1/K

Which properties there are depends on the kind of material: a wood has a
``janka_hardness`` and a metal a ``yield_strength``.

Ranges
======

``density`` is a single typical value. Every other property is a
``Range``, because real material varies.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [ranges]
    :end-before: [ranges]

.. code-block:: text

    Range(min=66, max=70)
    66 70
    68.0

``value_at(r)`` gives the value a fraction ``r`` of the way from ``min`` to
``max``: ``value_at(0)`` is ``min`` and ``value_at(1)`` is ``max``. ``r`` is
not limited to that interval, and outside it the value is extrapolated.
For a calculation that has to be safe, take the end of the range that
works against you, as :ref:`tutorial_parametric_part` does with ``.min``.

Units
=====

The properties are plain numbers. Their units are fixed, and are listed in
``PROPERTY_UNITS``.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [units]
    :end-before: [units]

.. code-block:: text

    kg/m³
    GPa

.. list-table::
    :header-rows: 1
    :widths: 50 30

    * - Property
      - Unit
    * - ``density``
      - kg/m³
    * - ``areal_density``
      - g/m²
    * - ``modulus_of_elasticity``, ``shear_modulus``
      - GPa
    * - ``tensile_strength``, ``yield_strength``, ``shear_strength``,
        ``compressive_strength_parallel``, ``modulus_of_rupture``
      - MPa
    * - ``hardness``
      - per ``hardness_scale``
    * - ``janka_hardness``
      - N
    * - ``elongation_at_break``
      - %
    * - ``poisson_ratio``
      - none
    * - ``max_service_temp``, ``melting_temperature``,
        ``glass_transition_temperature``, ``heat_deflection_temperature``
      - °C
    * - ``specific_heat_capacity``
      - J/(kg·K)
    * - ``thermal_conductivity``
      - W/(m·K)
    * - ``thermal_expansion``
      - 1/K
    * - ``thickness``
      - mm

**************
Weigh a part
**************

``mass()`` multiplies the volume of a shape by the density of its
material.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [mass]
    :end-before: [mass]

.. code-block:: text

    30000.0
    81.0
    0.081

``volume`` is a bare number: the volume in whatever unit of length the
model was drawn in, cubed. A density, on the other hand, is always in
kg/m³. So ``mass(mass_unit, length_unit)`` has to be told two things: the
unit to give the answer in, and the unit of length the model is in. They
default to grams and millimetres.

If the model is in inches, say so:

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [mass_inches]
    :end-before: [mass_inches]

.. code-block:: text

    2926.3

The shape has not changed. The same numbers are now read as a plate 100
inches long, which is 25.4³ - about 16,000 - times the volume of one 100
mm long, and the answer is in pounds.

A shape with no material cannot be weighed:

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [no_material]
    :end-before: [no_material]

.. code-block:: text

    Shape's density is missing

**************************
Materials in an assembly
**************************

A part that has no material of its own uses the material of the assembly
it belongs to, or of the assembly above that. The mass of an assembly is
the sum of the masses of its children, each with its own material.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [assembly]
    :end-before: [assembly]

.. code-block:: text

    Stainless_G304_ANNEALED
    89.0

The plate is aluminium and the knob is oak, as assigned. The bolt was
given nothing, so it is stainless steel, the material of the panel.

***********************
Colour and rendering
***********************

Each material carries *physically based rendering* (PBR) properties: its
colour, how metallic and how rough it is, and for many materials texture
maps for grain or brushing. They are chosen from the material and its
finish together.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [pbr]
    :end-before: [pbr]

.. code-block:: text

    PbrProperties(name='aluminum', source='physicallybased', license='CC0 1.0')
      values:  PbrValues(color=[0.962127915014933, 0.9653593968226258, 0.965819868630574], metalness=1.0, roughness=0.0, specular_intensity=1.0, specular_color=[0.91, 0.936, 0.959])
      maps:    PbrMaps()
    Color: (0.9621, 0.9654, 0.9658, 1.0) near 'WHITESMOKE'

A shape with a material and no colour of its own takes the colour of the
material, as the last line shows. The Studio tab of OCP CAD Viewer uses
all of the PBR properties:

.. image:: /tutorials/assets/box_materials/materials_box.png
    :align: center
    :width: 60%

:func:`~exporters3d.export_gltf` writes them into the file, so a glTF
viewer shows the same thing. Use ``binary=True`` and a ``.glb`` name, which
keeps the texture maps in the one file:

.. code-block:: build123d

    export_gltf(panel, "panel.glb", binary=True)

*******************
Custom materials
*******************

When the library does not have what you need, each module has a
``custom_`` function. Only a name and a density are required; give any of
the other properties you know.

.. literalinclude:: /how_to/materials.py
    :language: build123d
    :start-after: [custom]
    :end-before: [custom]

.. code-block:: text

    1.1

A custom material can be given an appearance from one of the public
material libraries. This box is carbon fibre with black oxide steel
hinges:

.. code-block:: build123d

    from threejs_materials import PbrProperties

    carbon_fibre = plastics.custom_plastic(
        "carbon fiber",
        density=1500,  # kg/m³
        pbr=PbrProperties.from_gpuopen("Carbon biColor Coat"),
    )
    box.material = carbon_fibre
    lid.material = carbon_fibre
    hinge.material = metals.mild_steel(finish=finishes.black_oxide())

.. image:: /tutorials/assets/materials/pbr_hinges_carbon.png
    :align: center
    :width: 60%

.. note::

    ``PbrProperties.from_gpuopen`` downloads the material and converts it,
    which needs `MaterialX <https://pypi.org/project/MaterialX/>`_. That is
    a binary package which is not available for every system and Python
    version, so it is optional: install it with
    ``pip install threejs-materials[materialx]``.
