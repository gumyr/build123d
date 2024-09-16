############
Installation
############

The recommended method for most users is to install **build123d** is:

.. doctest::

	>>> pip install build123d

.. note::

	The `ocp-vscode <https://github.com/bernhard-42/vscode-ocp-cad-viewer>`_ viewer has
	the ability to install **build123d**.

Install build123d from GitHub:
------------------------------

To get the latest non-released version of **build123d** one can install from GitHub using one of the following two commands:

In Linux/MacOS, use the following command:

.. doctest::

	>>> python3 -m pip install git+https://github.com/gumyr/build123d

In Windows, use the following command:

.. doctest::

	>>> python -m pip install git+https://github.com/gumyr/build123d

If you receive errors about conflicting dependencies, you can retry the installation after having
upgraded pip to the latest version with the following command:

.. doctest::

	>>> python3 -m pip install --upgrade pip

If you use `poetry <https://python-poetry.org/>`_ to install build123d, you can simply use:

.. doctest::

	>>> poetry add build123d

However, if you want the latest commit from GitHub you might need to specify
the branch that is used for git-based installs; until quite recently, poetry used to checkout the
`master` branch when none was specified, and this fails on build123d that uses a `dev` branch.

Pip does not suffer from this issue because it correctly fetches the repository default branch.

If you are a poetry user, you can work around this issue by installing build123d in the following
way:

.. doctest::

	>>> poetry add git+https://github.com/gumyr/build123d.git@dev

Please note that always suffixing the URL with ``@dev`` is safe and will work with both older and
recent versions of poetry.

Development install of build123d:
----------------------------------------------
**Warning**: it is highly recommended to upgrade pip to the latest version before installing
build123d, especially in development mode. This can be done with the following command:

.. doctest::

	>>> python3 -m pip install --upgrade pip

Once pip is up-to-date, you can install build123d
`in development mode <https://setuptools.pypa.io/en/latest/userguide/development_mode.html>`_
with the following commands:

.. doctest::

	>>> git clone https://github.com/gumyr/build123d.git
	>>> cd build123d
	>>> python3 -m pip install -e .

Please substitute ``python3`` with ``python`` in the lines above if you are using Windows.

If you're working directly with the OpenCascade ``OCP`` layer you will likely want to install
the OCP stubs as follows:

.. doctest::

	>>> python3 -m pip install git+https://github.com/CadQuery/OCP-stubs@7.7.0

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

Special notes on Apple Silicon installs
----------------------------------------------

Due to some dependencies not being available via pip, there is a bit of a hacky work around for Apple Silicon installs (M1 or M2 ARM64 architecture machines - if you aren't sure, try `uname -p` in a terminal and see if it returns arm).  Specifically the cadquery-ocp dependency fails to resolve at install time.  The error looks something like this:

.. doctest::

	└[~]> python3 -m pip install build123d
	Collecting build123d
	...
	INFO: pip is looking at multiple versions of build123d to determine which version is compatible with other requirements. This could take a while.
	ERROR: Could not find a version that satisfies the requirement cadquery-ocp~=7.7.1 (from build123d) (from versions: none)
	ERROR: No matching distribution found for cadquery-ocp~=7.7.1

A procedure for avoiding this issue is to install in a conda environment, which does have the missing dependency (substituting <YOUR ENVIRONMENT NAME> for the environment name you want to use for this install):

.. doctest::

	conda create -n <YOUR ENVIRONMENT NAME> python=3.10
	conda activate <YOUR ENVIRONMENT NAME>
	conda install -c cadquery -c conda-forge cadquery=master
	pip install svgwrite svgpathtools anytree scipy ipython trianglesolver \
	    ocp_tessellate webcolors==1.12 numpy numpy-quaternion cachetools==5.2.0 \
	    ocp_vscode requests orjson urllib3 certifi py-lib3mf \
	    "svgpathtools>=1.5.1,<2" "svgelements>=1.9.1,<2" "ezdxf>=1.1.0,<2"
	pip install --no-deps build123d ocpsvg

`You can track the issue here <https://github.com/CadQuery/ocp-build-system/issues/11#issuecomment-1407769681>`_

Alternatively, you can install under `Rosetta <https://support.apple.com/en-us/HT211861>`_ and run scripts non-natively:


.. doctest::

	arch -x86_64 zsh # starts zsh under emulated intel architecture
	pip install build123d
	python ./my_bd_script.py # you will need to run python under `arch -x86_64`

Adding a nicer GUI
----------------------------------------------

If you prefer to have a GUI available, your best option is to choose one from here: :ref:`external`
