##################
CAD Object Centers
##################

Finding the center of a CAD object is a surprisingly complex operation.  To illustrate
let's consider two examples: a simple isosceles triangle and a curved line (their bounding
boxes are shown with dashed lines):

.. image:: assets/center.svg
    :width: 49%

.. image:: assets/one_d_center.svg
    :width: 49%


One can see that there is are significant differences between the different types of 
centers. To allow the designer to choose the center that makes the most sense for the given
shape there are three possible values for the :class:`~build_enums.CenterOf` Enum:

==============================  ======  == == == ========
:class:`~build_enums.CenterOf`  Symbol  1D 2D 3D Compound
==============================  ======  == == == ========
CenterOf.BOUNDING_BOX           □       ✓  ✓  ✓  ✓
CenterOf.GEOMETRY               △       ✓  ✓       
CenterOf.MASS                   ○       ✓  ✓  ✓  ✓
==============================  ======  == == == ========
