Create Text Object
^^^^^^^^^^^^^^^^^^

Create text object or add to ``BuildSketch`` using :class:`~objects_sketch.Text`:

.. image:: /assets/objects/text.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

    text = "The quick brown fox jumped over the lazy dog."
    Text(text, 10)


Specify font and style. Fonts have up to 4 font styles: ``REGULAR``, ``BOLD``,
``ITALIC``, ``BOLDITALIC``. All fonts can use ``ITALIC`` even if only
``REGULAR`` is defined.

.. code-block:: build123d

   Text(text, 10, "Arial", font_style=FontStyle.BOLD)


Find available fonts on system and available styles:

.. code-block:: build123d

   from pprint import pprint
   pprint(available_fonts())

.. code-block:: text

   [
    ...
    Font(name='Arial', styles=('REGULAR', 'BOLD', 'BOLDITALIC', 'ITALIC')),
    Font(name='Arial Black', styles=('REGULAR',)),
    Font(name='Arial Narrow', styles=('REGULAR', 'BOLD', 'BOLDITALIC', 'ITALIC')),
    Font(name='Arial Rounded MT Bold', styles=('REGULAR',)),
    ...
   ]


Font faces like ``"Arial Black"`` or ``"Arial Narrow"`` must be specified
by name rather than ``FontStyle``:

.. code-block:: build123d

   Text(text, 10, "Arial Black")


Specify a font file directly by filename:

.. code-block:: build123d

   Text(text, 10, font_path="DejaVuSans.ttf")


Fonts added via ``font_path`` persist in the font list:

.. code-block:: build123d

   Text(text, 10, font_path="SourceSans3-VariableFont_wght.ttf")
   pprint([f.name for f in available_fonts() if "Source Sans" in f.name])
   Text(text, 10, "Source Sans 3 Medium")

.. code-block:: text

   ['Source Sans 3',
    'Source Sans 3 Black',
    'Source Sans 3 ExtraBold',
    'Source Sans 3 ExtraLight',
    ...]


Add a font file to ``FontManager`` if a font is reused in the script or
contains multiple font faces:

.. code-block:: build123d

   new_font_faces = FontManager().register_font("Roboto-VariableFont_wdth,wght.ttf")
   pprint(new_font_faces)
   Text(text, 10, "Roboto")
   Text(text, 10, "Roboto Black")

.. code-block:: text

   ['Roboto Thin',
    'Roboto ExtraLight',
    'Roboto Light',
    'Roboto',
     ...]


Placement
^^^^^^^^^

Multiline text has two methods of alignment.
``text_align`` aligns the text relative to its ``Location``:

.. image:: /assets/objects/text_align.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

   Text(text, 10, text_align=(TextAlign.LEFT, TextAlign.TOPFIRSTLINE))


``align`` aligns the object bounding box relative to its ``Location`` *after*
text alignment:

.. image:: /assets/objects/align.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

   text = "The quick brown\nfox jumped over\nthe lazy dog."
   Text(text, 10, align=(Align.MIN, Align.MIN))


Place text along an ``Edge`` or ``Wire`` with ``path`` and ``position_on_path``:

.. image:: /assets/objects/path.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

   text = "The quick brown fox"
   path = RadiusArc((-50, 0), (50, 0), 100)
   Text(
       text,
       10,
       path=path,
       position_on_path=.5,
       text_align=(TextAlign.CENTER, TextAlign.BOTTOM)
   )


Single Line Fonts
^^^^^^^^^^^^^^^^^

``"singleline"`` is a special font referencing ``Relief SingleLine CAD``.
Glyphs are represented as single lines rather than filled faces.

``Text`` creates an outlined face by default. The outline width is controlled
by ``single_line_width``. This operation is slow with many glyphs.

.. image:: /assets/objects/outline.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

   Text(text, 10, "singleline")
   Text(text, 10, "singleline", single_line_width=1)


Use ``Compound.make_text()`` to create *unoutlined* single-line text.
Useful for routing, engraving, or drawing label paths.

.. image:: /assets/objects/singleline.png
    :width: 80%
    :align: center

|

.. code-block:: build123d

   Compound.make_text(text, 10, "singleline")


Common Issues
^^^^^^^^^^^^^

Missing Glyphs or Invalid Geometry
==================================

Modern variable-width fonts often contain glyphs with overlapping stroke
outlines, which produce invalid geometry. ``ocp_vscode`` ignores invalid
faces.

.. image:: /assets/objects/missing_glyph.png
    :align: center

|

.. code-block:: build123d

   Text("The", 10, "Source Sans 3 Black")


FileNotFoundError
=================

Ensure relative ``font_path`` specifications are relative to the *current
working directory*.


.. Working With Text
.. #################

.. Create text object or add to ``BuildSketch``:

.. .. code-block:: build123d
..     text = "The quick brown fox jumped over the lazy dog."
..     Text(text, 10)

.. Specify font and style. Fonts have up to 4 font styles: ``REGULAR``, ``BOLD``, ``ITALIC``, ``BOLDITALIC``.
.. All fonts can use ``ITALIC`` even if only ``REGULAR`` is defined.

.. .. code-block:: build123d

..    Text(text, 10, "Arial", font_style=FontStyle.BOLD)

.. Find available fonts on system and available styles:

.. .. code-block:: build123d

..    from pprint import pprint
..    pprint(available_fonts())

.. .. code-block:: text

..    [
..     ...
..     Font(name='Arial', styles=('REGULAR', 'BOLD', 'BOLDITALIC', 'ITALIC')),
..     Font(name='Arial Black', styles=('REGULAR',)),
..     Font(name='Arial Narrow', styles=('REGULAR', 'BOLD', 'BOLDITALIC', 'ITALIC')),
..     Font(name='Arial Rounded MT Bold', styles=('REGULAR',)),
..     ...
..    ]

.. Font faces like ``"Arial Black"`` or ``"Arial Narrow"`` need to be specified by name rather than ``FontStyle``:

.. .. code-block:: build123d

..    Text(text, 10, "Arial Black")


.. .. code-block:: build123d

..    Text(text, 10, font_path="DejaVuSans.ttf")


.. .. code-block:: build123d

..    Text(text, 10, font_path="SourceSans3-VariableFont_wght.ttf")
..    pprint([f.name for f in available_fonts() if "Source Sans" in f.name])
..    Text(text, 10, "Source Sans 3 Medium")

.. .. code-block:: text

..    ['Source Sans 3',
..     'Source Sans 3 Black',
..     'Source Sans 3 ExtraBold',
..     'Source Sans 3 ExtraLight',
..     ...]


.. .. code-block:: build123d

..    new_font_faces = FontManager().register_font("Roboto-VariableFont_wdth,wght.ttf")
..    pprint(new_font_faces)
..    Text(text, 10, "Roboto")
..    Text(text, 10, "Roboto Black")

.. .. code-block:: text

..    ['Roboto Thin',
..     'Roboto ExtraLight',
..     'Roboto Light',
..     'Roboto',
..      ...]

.. Placement
.. #########

.. Multiline text has two methods of alignment:
.. ``text_align`` aligns the text relative to its ``Location``:

.. .. code-block:: build123d

..    Text(text, 10, text_align=(TextAlign.LEFT, TextAlign.TOPFIRSTLINE))


.. ``align`` aligns the object bounding box relative to its ``Location`` *after* text alignment:

.. .. code-block:: build123d

..    text = "The quick brown\nfox jumped over\nthe lazy dog."
..    Text(text, 10, align=(Align.MIN, Align.MIN))

.. Place text along an ``Edge`` or ``Wire`` with ``path`` and ``position_on_path``:

.. .. code-block:: build123d

..    text = "The quick brown fox"
..    path = RadiusArc((-50, 0), (50, 0), 100)
..    Text(
..        text,
..        10,
..        path=path,
..        position_on_path=.5,
..        text_align=(TextAlign.CENTER, TextAlign.BOTTOM)
..    )

.. Single Line Fonts
.. #################

.. ``"singleline"`` is a special font referencing ``Relief SingleLine CAD``.
.. Glyphs are represented as single lines rather than filled faces.

.. ``Text`` creates an outlined face by default.
.. The outline width is controlled by ``single_line_width``.
.. This operation is slow with many glyphs.

.. .. code-block:: build123d

..    Text(text, 10, "singleline")
..    Text(text, 10, "singleline", single_line_width=1)

.. Use ``Compound.make_text`` to create *unoutlined* single-line text.
.. Useful for routing, engraving, or drawing label path.

.. .. code-block:: build123d

..    Compound.make_text(text, 10, "singleline")

.. Common Issues
.. #############

.. Missing Glyphs or Invalid Geometry
.. ##################################

.. Modern variable-width fonts often contain glyphs with overlapping stroke outlines, which produce
.. invalid geometry. ``ocp_vscode`` ignores invalid faces.

.. .. code-block:: build123d

..    Text("The", 10, "Source Sans 3 Black")

.. FileNotFoundError
.. #################

.. Ensure relative ``font_path`` specifications are relative to the *current working directory*