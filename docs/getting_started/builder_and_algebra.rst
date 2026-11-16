.. _builder_and_algebra:

##############################
Builder mode and algebra mode
##############################

build123d can be written in two ways, called *builder mode* and *algebra
mode*. Every tutorial and guide in this documentation shows both, so it is
worth a few minutes now to see what they are.

Here is one part, a plate with a hole in the middle and one near each
corner, written each way:

.. image:: /getting_started/assets/modes_plate.svg
    :align: center

.. grid:: 1 1 2 2
    :gutter: 3

    .. grid-item::

        **Builder mode**

        .. literalinclude:: /getting_started/modes.py
            :language: build123d
            :start-after: [builder]
            :end-before: [builder]

    .. grid-item::

        **Algebra mode**

        .. literalinclude:: /getting_started/modes.py
            :language: build123d
            :start-after: [algebra]
            :end-before: [algebra]

Both make exactly the same part.

********************
What is the same
********************

Nearly everything. Both use the same objects, ``RectangleRounded`` and
``Circle``, the same patterns, ``GridLocations``, and the same operations,
``extrude``. The geometry that comes out is identical.

The two are also equal in what they can do. Anything that can be made in
one mode can be made in the other, and there is no feature of build123d
that belongs to only one of them.

*********************
What is different
*********************

How the pieces are put together.

In **builder mode** a model is built inside ``with`` blocks. A
``BuildSketch`` collects the shapes drawn inside it, and a ``BuildPart``
collects the solids. Each object adds itself to the builder whose block it
is in, and says how with ``mode``: the circles above are taken away because
they are made with ``Mode.SUBTRACT``. The layout of the code follows the
structure of the design: the sketch is indented inside the part it belongs
to, and the holes inside the sketch they are cut from. The finished part
is ``plate.part``.

In **algebra mode** every object is a value, like a number, and values are
combined with operators: ``+`` to join, ``-`` to cut and ``&`` to keep what
two have in common, with ``*`` to put something in a place. Each line takes
shapes and gives back a new shape, which is kept in an ordinary variable.
Nothing happens that is not written down. The finished part is ``plate``.

****************
Which to use
****************

It is a matter of taste, and both are fully supported.

* Builder mode gives a design a visible structure. Many people find that
  the nesting helps while they are designing, because it keeps each
  feature with the thing it belongs to, much as the feature tree does in a
  conventional CAD program. Its syntax is the less familiar of the two: a
  line such as ``Circle(12, mode=Mode.SUBTRACT)``, which changes a model
  that is never named, does not look like ordinary Python.
* Algebra mode looks like ordinary Python, which some people much prefer.
  There is no hidden state: what a line does can be read from the line. It
  is often the shorter of the two for a small part. In a larger design the
  structure that the builder supplies has to come from how the code is
  arranged instead, and keeping it tidy is up to you. The usual habits of
  good programming apply. One that matters here is not to change what kind
  of thing a name holds: when a sketch is extruded, give the part a new
  name, as the example above does with ``outline`` and ``plate``, and do
  not reuse the sketch's. Linters and type checkers, the ordinary tools of
  Python, will catch slips like that.

Try both on a part or two and use the one that suits you. The choice is
not permanent, and the two can be mixed in one program. A part made by a
builder is an ordinary value once the block has ended, and can be carried
on with operators:

.. literalinclude:: /getting_started/modes.py
    :language: build123d
    :start-after: [mixed]
    :end-before: [mixed]

************************************
How the documentation shows them
************************************

Wherever the two modes differ, the code is given in a pair of tabs,
**Builder** and **Algebra**. Choose one and every other pair on the page
follows, and the site remembers the choice. The other tab can be ignored:
each is complete without the other.

Where the modes do not differ, for instance when selecting the edges of a
finished part, the code is shown once.

To understand what each mode is doing underneath, see
:ref:`how_builder_mode_works` and :doc:`/explanation/key_concepts_algebra`.
