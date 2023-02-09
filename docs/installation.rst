############
Installation
############
Install build123d from github:
----------------------------------------------

The recommended method for most users is to install build123d with one of the following two commands.

In Linux/MacOS, use the following command:

.. doctest::

	>>> python3 -m pip install git+https://github.com/gumyr/build123d.git@pyproject.toml

In Windows, use the following command:

.. doctest::

	>>> python -m pip install git+https://github.com/gumyr/build123d.git@pyproject.toml

Development install of build123d:
----------------------------------------------
.. doctest::

	>>> git clone https://github.com/gumyr/build123d.git
	>>> cd build123d
	>>> python3 -m pip install -e .

Test your build123d installation:
----------------------------------------------
If all has gone well, you can open a command line/prompt, and type:

.. doctest::

	>>> python
	>>> from build123d import *
	>>> print(Solid.make_box(1,2,3).show_topology(limit_class="Face"))

Which should return something similar to:

.. code::

		Solid        at 0x165e75379f0, Center(0.5, 1.0, 1.5)
		└── Shell    at 0x165eab056f0, Center(0.5, 1.0, 1.5)
			├── Face at 0x165b35a3570, Center(0.0, 1.0, 1.5)
			├── Face at 0x165e77957f0, Center(1.0, 1.0, 1.5)
			├── Face at 0x165b3e730f0, Center(0.5, 0.0, 1.5)
			├── Face at 0x165e8821570, Center(0.5, 2.0, 1.5)
			├── Face at 0x165e88218f0, Center(0.5, 1.0, 0.0)
			└── Face at 0x165eb21ee70, Center(0.5, 1.0, 3.0)

Adding a nicer GUI
----------------------------------------------

If you prefer to have a GUI available, your best option is to choose one from here: :ref:`external`
