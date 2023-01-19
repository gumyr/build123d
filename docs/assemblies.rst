##########
Assemblies
##########

Most CAD designs consist of more than one part which are naturally arranged in
some type of assembly. Once parts have been assembled in a ``Compound`` object
they can be treated as a unit - i.e. ``moved`` or exported.

To create an assembly in build123d, one needs to
create a tree of parts by simply assigning either a ``Compound`` object's ``parent`` or
``children`` attributes. To illustrate the process, we'll extend the
:ref:`Joint Tutorial <joint_tutorial>`.

****************
Assigning Labels
****************

In order keep track of objects one can assign a ``label`` to all ``Shape`` objects.
Here we'll assign labels to all of the components that will be part of the box
assembly:

.. literalinclude:: tutorial_joints.py
    :lines: 283-287

The labels are just strings with no further limitations (they don't have to be unique
within the assembly).

****************************
Create the Assembly Compound
****************************

Creation of the assembly is done by simply creating a ``Compound`` object and assigning
appropriate ``parent`` and ``children`` attributes as shown here:

.. literalinclude:: tutorial_joints.py
    :lines: 289-290

To display the structure of an assembly ``Compound``, the :meth:`~direct_api.Shape.show_structure`
method can be used as follows:

.. literalinclude:: tutorial_joints.py
    :lines: 289-291
    :emphasize-lines: 3

which results in:

.. code::

        assembly        Compound at 0x7fc8ee235760, Location(p=(0, 0, 0), o=(-0, 0, -0))
        ├── box         Compound at 0x7fc8ee2188b0, Location(p=(0, 0, 50), o=(-0, 0, -0))
        ├── lid         Compound at 0x7fc8ee228460, Location(p=(-26, 0, 181), o=(-180, 30, -0))
        ├── inner hinge Hinge    at 0x7fc9292c3f70, Location(p=(-119, 60, 122), o=(90, 0, -150))
        └── outer hinge Hinge    at 0x7fc9292c3f40, Location(p=(-150, 60, 50), o=(90, 0, 90))

To add to an assembly ``Compound`` one can change either ``children`` or ``parent`` attributes.

.. literalinclude:: tutorial_joints.py
    :lines: 293-295

and now the screw is part of the assembly.

.. code::

        assembly        Compound at 0x7fc8ee235760, Location(p=(0, 0, 0), o=(-0, 0, -0))
        ├── box         Compound at 0x7fc8ee2188b0, Location(p=(0, 0, 50), o=(-0, 0, -0))
        ├── lid         Compound at 0x7fc8ee228460, Location(p=(-26, 0, 181), o=(-180, 30, -0))
        ├── inner hinge Hinge    at 0x7fc9292c3f70, Location(p=(-119, 60, 122), o=(90, 0, -150))
        ├── outer hinge Hinge    at 0x7fc9292c3f40, Location(p=(-150, 60, 50), o=(90, 0, 90))
        └── M6 screw    Compound at 0x7fc8ee235310, Location(p=(-157, -40, 70), o=(-0, -90, -60))


************************
Shapes are Anytree Nodes
************************

The build123d assembly constructs are built using the python
`anytree <https://anytree.readthedocs.io/en/latest/>`_ package by making the build123d
:class:`~direct_api.Shape` class a sub-class of anytree's ``NodeMixin`` class. Doing so
adds the following attributes to ``Shape``:

* ``parent`` - Parent Node. On set, the node is detached from any previous parent node and attached to the new node.
* ``children`` - Tuple of all child nodes.
* ``path`` - Path of this ``Node``.
* ``iter_path_reverse`` - Iterate up the tree from the current node.
* ``ancestors`` - All parent nodes and their parent nodes.
* ``descendants`` - All child nodes and all their child nodes.
* ``root`` - Tree Root Node.
* ``siblings`` - Tuple of nodes with the same parent.
* ``leaves`` - Tuple of all leaf nodes.
* ``is_leaf`` - ``Node`` has no children (External Node).
* ``is_root`` - ``Node`` is tree root.
* ``height`` - Number of edges on the longest path to a leaf ``Node``.
* ``depth`` - Number of edges to the root ``Node``.

.. note::

    Changing the ``children`` attribute

    Any iterator can be assigned to the ``children`` attribute but subsequently the children
    are stored as immutable ``tuple`` objects.  To add a child to an existing ``Compound``
    object, the ``children`` attribute will have to be reassigned.
