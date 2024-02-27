#######################
The build123d Examples
#######################
.. |siren| replace:: 🚨 
.. |Builder| replace:: 🔨
.. |Algebra| replace:: ✏️ 

Overview
--------------------------------

In the GitHub repository you will find an `examples folder <https://github.com/42sol-eu/build123d/tree/examples>`_.

Most of the examples show the builder and algebra modes.

.. ----------------------------------------------------------------------------------------------
.. Index Section
.. ----------------------------------------------------------------------------------------------


.. grid:: 3

    .. grid-item-card:: Low Poly Benchy |Builder|
        :img-top:  assets/examples/thumbnail_benchy_01.png
        :link: examples-benchy
        :link-type: ref

    .. grid-item-card:: Boxes on Faces |Builder| |Algebra|
        :img-top: assets/examples/thumbnail_boxes_on_faces_01.png
        :link: examples-boxes_on_faces
        :link-type: ref

    .. grid-item-card:: build123d customizable logo |Builder| |Algebra|
        :img-top: assets/examples/thumbnail_build123d_customizable_logo_01.png
        :link: examples-build123d_customizable_logo
        :link-type: ref

    .. grid-item-card:: Former build123d Logo |Builder| |Algebra|
            :img-top: assets/examples/thumbnail_build123d_logo_01.png
            :link: examples-build123d_logo
            :link-type: ref
    
    .. grid-item-card:: Circuit Board With Holes |Builder| |Algebra| 
            :img-top: assets/examples/thumbnail_circuit_board_01.png
            :link: examples-canadian_flag
            :link-type: ref
        
    .. grid-item-card:: Canadian Flag Blowing in The Wind |Builder| |Algebra| 
            :img-top: assets/examples/thumbnail_canadian_flag_01.png
            :link: examples-circuit_board
            :link-type: ref

    .. grid-item-card:: Maker Coin |Builder| 
            :img-top: assets/examples/maker_coin.png
            :link: maker_coin
            :link-type: ref

    .. grid-item-card:: Platonic Solids |Algebra| 
            :img-top: assets/examples/platonic_solids.png
            :link: platonic_solids
            :link-type: ref

    .. grid-item-card:: Stud Wall |Algebra| 
            :img-top: assets/examples/stud_wall.png
            :link: stud_wall
            :link-type: ref


.. NOTE 01: insert new example thumbnails above this line

.. TODO: Copy this block to add the example thumbnails here
    .. grid-item-card:: name-of-your-example-with-spaces |Builder| |Algebra|
            :img-top: assets/examples/thumbnail_{name-of-your-example}_01.{extension}
            :link: examples-{name-of-your-example}
            :link-type: ref
   
.. ----------------------------------------------------------------------------------------------
.. Details Section
.. ----------------------------------------------------------------------------------------------

.. _examples-benchy:

Low Poly Benchy
--------------------------------
.. image:: assets/examples/example_benchy_01.png
    :align: center


The Benchy examples shows how to import a STL model as a `Solid` object with the class `Mesher` and 
modify it by replacing chimney with a BREP version.

.. note 

     *Attribution:*
     The low-poly-benchy used in this example is by `reddaugherty`, see
     https://www.printables.com/model/151134-low-poly-benchy.


.. dropdown:: Gallery

    .. image:: assets/examples/example_benchy_02.png
        :align: center


    .. image:: assets/examples/example_benchy_03.png
        :align: center

.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/benchy.py
        :start-after: [Code]
        :end-before: [End]

.. ----------------------------------------------------------------------------------------------

.. _examples-boxes_on_faces:

Boxes on Faces
--------------------------------
.. image:: assets/examples/example_boxes_on_faces_01.png
    :align: center

Create elements on every face of a box.


.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/boxes_on_faces.py
        :start-after: [Code]
        :end-before: [End]

.. dropdown:: |Algebra| Reference Implementation (Algebra Mode)  

    .. literalinclude:: ../examples/boxes_on_faces_algebra.py
        :start-after: [Code]
        :end-before: [End]

.. _examples-build123d_customizable_logo:

The build123d customizable logo
--------------------------------
.. image:: assets/examples/example_build123d_customizable_logo_01.png
    :align: center

This example creates the build123d customizable logo.
It shows how text is created, placed and sizes of text is calulated to define sizes of other elements.

.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/build123d_customizable_logo.py
        :start-after: [Code]
        :end-before: [End]

.. dropdown:: |Algebra| Reference Implementation (Algebra Mode)  

    .. literalinclude:: ../examples/build123d_customizable_logo_algebra.py
        :start-after: [Code]
        :end-before: [End]


.. _examples-build123d_logo:

Former build123d Logo
--------------------------------
.. image:: assets/examples/example_build123d_logo_01.png
    :align: center


This example creates the former build123d logo (new logo was created in the end of 2023).

Using text and lines to create the first build123d logo. 
The builder mode example also generates the SVG file `logo.svg`.


.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/build123d_logo.py
        :start-after: [Code]
        :end-before: [End]
    
.. dropdown:: |Algebra| Reference Implementation (Algebra Mode) 

    .. literalinclude:: ../examples/build123d_logo_algebra.py
        :start-after: [Code]
        :end-before: [End]


.. _examples-canadian_flag:

Canadian Flag Blowing in The Wind
----------------------------------
.. image:: assets/examples/example_canadian_flag_01.png
    :align: center



A Canadian Flag blowing in the wind created by projecting planar faces onto a non-planar face (the_wind).

This example also demonstrates building complex lines that snap to existing features.


.. dropdown:: More Images

    .. image:: assets/examples/example_canadian_flag_02.png
        :align: center

    .. image:: assets/examples/example_canadian_flag_03.png
        :align: center


.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/canadian_flag.py
        :start-after: [Code]
        :end-before: [End]
    
.. dropdown:: |Algebra| Reference Implementation (Algebra Mode) 

    .. literalinclude:: ../examples/canadian_flag_algebra.py
        :start-after: [Code]
        :end-before: [End]
    

.. _examples-circuit_board:


Circuit Board With Holes
------------------------
.. image:: assets/examples/example_circuit_board_01.png
    :align: center



This example demonstrates placing holes around a part.

- Builder mode uses `Locations` context to place the positions.
- Algebra mode uses `product` and `range` to calculate the positions.



.. dropdown:: More Images

    .. image:: assets/examples/example_circuit_board_02.png
        :align: center


.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/circuit_board.py
        :start-after: [Code]
        :end-before: [End]
    
.. dropdown:: |Algebra| Reference Implementation (Algebra Mode) 

    .. literalinclude:: ../examples/circuit_board_algebra.py
        :start-after: [Code]
        :end-before: [End]


.. _maker_coin:

Maker Coin
----------
.. image:: assets/examples/maker_coin.png
    :align: center

This example creates the maker coin as defined by Angus on the Maker's Muse
YouTube channel. There are two key features:

#. the use of :class:`~objects_curve.DoubleTangentArc` to create a smooth 
   transition from the central dish to the outside arc, and

#. embossing the text into the top of the coin not just as a simple
   extrude but from a projection which results in text with even depth.


.. dropdown:: |Builder| Reference Implementation (Builder Mode) 

    .. literalinclude:: ../examples/maker_coin.py
        :start-after: [Code]
        :end-before: [End]

.. _platonic_solids:

Platonic Solids
---------------
.. image:: assets/examples/platonic_solids.png
    :align: center

This example creates a custom Part object PlatonicSolid.

Platonic solids are five three-dimensional shapes that are highly symmetrical, 
known since antiquity and named after the ancient Greek philosopher Plato. 
These solids are unique because their faces are congruent regular polygons, 
with the same number of faces meeting at each vertex. The five Platonic solids 
are the tetrahedron (4 triangular faces), cube (6 square faces), octahedron 
(8 triangular faces), dodecahedron (12 pentagonal faces), and icosahedron 
(20 triangular faces). Each solid represents a unique way in which identical 
polygons can be arranged in three dimensions to form a convex polyhedron, 
embodying ideals of symmetry and balance.

.. dropdown:: |Algebra| Reference Implementation (Algebra Mode) 

    .. literalinclude:: ../examples/platonic_solids.py
        :start-after: [Code]
        :end-before: [End]

.. _stud_wall:

Stud Wall
---------
.. image:: assets/examples/stud_wall.png
    :align: center

This example demonstrates creatings custom `Part` objects and putting them into
assemblies. The custom object is a `Stud` used in the building industry while
the assembly is a `StudWall` created from copies of `Stud` objects for efficiency.
Both the `Stud` and `StudWall` objects use `RigidJoints` to define snap points which
are used to position all of objects.   

.. dropdown:: |Algebra| Reference Implementation (Algebra Mode) 

    .. literalinclude:: ../examples/stud_wall.py
        :start-after: [Code]
        :end-before: [End]
    


.. NOTE 02: insert new example thumbnails above this line
    

.. TODO: Copy this block to add your example details here
    .. _examples-{name-of-your-example}:

    {name-of-your-example-with-spaces}
    --------------------------------
    .. image:: assets/examples/example_{name-of-your-example}_01.{extension}
    :align: center

    .. image:: assets/examples/example_{name-of-your-example}_02.{extension}
    :align: center

    .. dropdown:: info

        TODO: add more information about your example 

    .. dropdown:: |Builder| Reference Implementation (Builder Mode) 

        .. literalinclude:: ../examples/boxes_on_faces.py
            :start-after: [Code]
            :end-before: [End]

    .. dropdown:: |Algebra| Reference Implementation (Algebra Mode)  

        .. literalinclude:: ../examples/boxes_on_faces_algebra.py
            :start-after: [Code]
            :end-before: [End]