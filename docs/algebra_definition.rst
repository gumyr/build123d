.. _algebra_definition:

Algebraic definition
========================

Objects and arithmetic
------------------------

**Set definitions:**

:math:`C^3` is the set of all ``Part`` objects ``p`` with ``p._dim = 3``

:math:`C^2` is the set of all ``Sketch`` objects ``s`` with ``s._dim = 2``

:math:`C^1` is the set of all ``Curve`` objects ``c`` with ``c._dim = 1``

**Neutral elements:**

:math:`c^3_0` is the empty ``Part`` object ``p0 = Part()`` with ``p0._dim = 3`` and ``p0.wrapped = None``

:math:`c^2_0` is the empty ``Sketch`` object ``s0 = Sketch()`` with ``s0._dim = 2`` and ``s0.wrapped = None``

:math:`c^1_0` is the empty ``Curve`` object ``c0 = Curve()`` with ``c0._dim = 1`` and ``c0.wrapped = None``


**Sets of predefined basic shapes:**

:math:`B^3 := \lbrace` ``Part``, ``Box``, ``Cylinder``, ``Cone``, ``Sphere``, ``Torus``, ``Wedge``, ``Hole``, ``CounterBoreHole``, ``CounterSinkHole`` :math:`\rbrace`

:math:`B^2 := \lbrace` ``Sketch``, ``Rectangle``, ``Circle``, ``Ellipse``, ``Rectangle``, ``Polygon``, ``RegularPolygon``, ``Text``, ``Trapezoid``, ``SlotArc``, ``SlotCenterPoint``, ``SlotCenterToCenter``, ``SlotOverall`` :math:`\rbrace`

:math:`B^1 := \lbrace` ``Curve``, ``Bezier``, ``FilletPolyline``, ``PolarLine``, ``Polyline``, ``Spline``, ``Helix``, ``CenterArc``, ``EllipticalCenterArc``, ``RadiusArc``, ``SagittaArc``, ``TangentArc``, ``ThreePointArc``, ``JernArc`` :math:`\rbrace`

with :math:`B^3 \subset C^3, B^2 \subset C^2` and :math:`B^1 \subset C^1`


**Operations:**

:math:`+: C^n \times C^n \rightarrow C^n` with :math:`(a,b) \mapsto a + b`,  :math:`\;` for :math:`n=1,2,3`

    :math:`\; a + b :=` ``a.fuse(b)`` for each operation

:math:`-: C^n \rightarrow C^n` with :math:`a \mapsto -a`,  :math:`\;` for :math:`n=1,2,3`

    :math:`\; b + (-a) :=` ``b.cut(a)`` for each operation (implicit definition)


:math:`\&: C^n \times C^n \rightarrow C^n` with :math:`(a,b) \mapsto a \; \& \; b`,  :math:`\;` for :math:`n=2,3`

    :math:`\; a \; \& \; b :=` ``a.intersect(b)`` for each operation

    * :math:`\&` is not defined for :math:`n=1` in build123d
    * The following relationship holds: :math:`a \; \& \; b = (a + b) + -(a + (-b)) + -(b + (-a))`


**Abelian groups**

:math:`( C^n, \; c^n_0, \; +, \; -)` :math:`\;`  are abelian groups for :math:`n=1,2,3`.

* The implementation ``a - b = a.cut(b)`` needs to be read as :math:`a + (-b)` since the group does not have a binary ``-`` operation. As such, :math:`a - (b - c) = a + -(b + -c)) \ne a - b + c`
* This definition also includes that neither ``-`` nor ``&`` are commutative.


Locations, planes and location arithmentic
---------------------------------------------

**Set definitions:**

:math:`L  := \lbrace` ``Location((x, y, z), (a, b, c))`` :math:`: x,y,z \in R \land a,b,c \in R \rbrace\;`

    with :math:`a,b,c` being angles in degrees.

:math:`P  := \lbrace` ``Plane(o, x, z)`` :math:`: o,x,z ∈ R^3 \land \|x\| = \|z\| = 1\rbrace`

    with ``o`` being the origin and ``x``, ``z`` the x- and z-direction of the plane.

Neutral element: :math:`\; l_0 \in L`: ``Location()``

**Operations:**

:math:`*: L \times L \rightarrow L` with :math:`(l_1,l_2) \mapsto l_1 * l_2`

    :math:`\; l_1 * l_2 :=`  ``l1 * l2`` (multiply two locations)

:math:`*: P \times L \rightarrow P` with :math:`(p,l) \mapsto p * l`

    :math:`\; p * l :=` ``Plane(p.location * l)`` (move plane :math:`p \in P` to location :math:`l \in L`)

Inverse element: :math:`\; l^{-1} \in L`: ``l.inverse()``


**Placing objects onto planes**

:math:`*: P \times C^n  \rightarrow C^n \;`  with :math:`(p,c) \mapsto p * c`,  :math:`\;` for :math:`n=1,2,3`

    Locate an object :math:`c \in C^n` onto plane :math:`p \in P`, i.e. ``c.moved(p.location)``

**Placing objects at locations**

:math:`*: L \times C^n  \rightarrow C^n \;`  with :math:`(l,c) \mapsto l * c`,  :math:`\;` for :math:`n=1,2,3`

    Locate an object :math:`c \in C^n` at location :math:`l \in L`, i.e. ``c.moved(l)``
