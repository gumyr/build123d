.. _algebra_definition:

Algebraic definition
========================

Objects and object arithmetic
----------------------------------

Set definitions:

:math:`P` is the set of all ``Part`` objects ``p`` with ``p._dim = 3``

:math:`S` is the set of all ``Sketch`` objects ``s`` with ``s._dim = 2``

:math:`C` is the set of all ``Curve`` objects ``c`` with ``c._dim = 3``

Neutral elements:

:math:`p_0` := ``p0``  is the empty ``Part`` object ``p0`` with ``p0._dim = 3`` and ``p0.wrapped = None``

:math:`s_0` := ``s0``  is the empty ``SKetch`` object ``s0`` with ``s0._dim = 2`` and ``s0.wrapped = None``

:math:`c_0` := ``c0``  is the empty ``Curve`` object ``c0`` with ``c0._dim = 1`` and ``c0.wrapped = None``

**Sets of predefined basic shapes:**

:math:`P_D := \lbrace` ``Part``, ``Box``, ``Cylinder``, ``Cone``, ``Sphere``, ``Torus``, ``Wedge``, ``Hole``, ``CounterBoreHole``, ``CounterSinkHole`` :math:`\rbrace`

:math:`S_D := \lbrace` ``Sketch``, ``Rectangle``, ``Circle``, ``Ellipse``, ``Rectangle``, ``Polygon``, ``RegularPolygon``, ``Text``, ``Trapezoid``, ``SlotArc``, ``SlotCenterPoint``, ``SlotCenterToCenter``, ``SlotOverall`` :math:`\rbrace`

:math:`C_D := \lbrace` ``Curve``, ``Bezier``, ``PolarLine``, ``Polyline``, ``Spline``, ``Helix``, ``CenterArc``, ``EllipticalCenterArc``, ``RadiusArc``, ``SagittaArc``, ``TangentArc``, ``ThreePointArc``, ``JernArc`` :math:`\rbrace`

with :math:`P_D \subset P, S_D \subset S` and :math:`C_D \subset C`

**Operations:**


:math:`+: P \times P \rightarrow P` with :math:`(a,b) \mapsto a + b`

:math:`+: S \times S \rightarrow S` with :math:`(a,b) \mapsto a + b`

:math:`+: C \times C \rightarrow C` with :math:`(a,b) \mapsto a + b`

    and :math:`a + b :=` ``a.fuse(b)`` for each operation


:math:`-: P \rightarrow P` with :math:`a \mapsto -a`

:math:`-: S \rightarrow S` with :math:`a \mapsto -a`

:math:`-: C \rightarrow C` with :math:`a \mapsto -a`

    and :math:`b + (-a) :=` ``b.cut(a)`` for each operation (implicit definition)


:math:`\&: P \times P \rightarrow P` with :math:`(a,b) \mapsto a \& b`

:math:`\&: S \times S \rightarrow S` with :math:`(a,b) \mapsto a \& b`

:math:`\&: C \times C \rightarrow C` with :math:`(a,b) \mapsto a \& b`

    and :math:`a \; \& \; b :=` ``a.intersect(b)`` for each operation

    Note: :math:`a \; \& \; b = (a + b) + -(a + (-b)) + -(b + (-a))`

**Abelian groups**

:math:`( P, p_0, +, -)`, :math:`( S, s_0, +, -)`, :math:`( C, c_0, +, -)` are abelian groups

Notes: 

* The implementation ``a - b = a.cut(b)`` needs to be read as :math:`a + (-b)` since the group does not have a binary ``-`` operation. As such, :math:`a - (b - c) = a + -(b + -c)) \ne a - b + c`

* This definition also includes that neither ``-`` nor ``&`` are commutative.




Locations, planes and location arithmentic
---------------------------------------------

:math:`L  := \lbrace` ``Location((x, y, z), (a, b, c))`` :math:`: x,y,z \in R \land a,b,c \in R\rbrace` with :math:`a,b,c` being angles in degrees

:math:`Q  := \lbrace` ``Plane(o, x, z)`` :math:`: o,x,z ∈ R^3 \land \|x\| = \|z\| = 1\rbrace` with ``o`` being the origin and ``x``, ``z`` the x- and z-direction of the plane.

:math:`*: L \times L \rightarrow L` (multiply two locations :math:`l_1, l_2 \in L`, i.e. ``l1 * l2``)

:math:`*: Q \times L \rightarrow Q` (move plane :math:`p \in Q` to location :math:`l \in L`, i.e. ``Plane(p.to_location() * l)``)

Neutral element: :math:`l_0 \in L`: ``Location()``

Inverse element: :math:`l^{-1} \in L`: ``l.inverse()``


**Placing objects onto planes**

:math:`*: Q \times P  \rightarrow P` (locate an object :math:`p \in P` onto plane :math:`q \in Q`, i.e. ``p.moved(q.to_location())``)

:math:`*: Q \times S  \rightarrow S` (locate an object :math:`s \in S` onto plane :math:`q \in Q`, i.e. ``s.moved(q.to_location())``)

:math:`*: Q \times C  \rightarrow C` (locate an object :math:`c \in C` onto plane :math:`q \in Q`, i.e. ``c.moved(q.to_location())``)


**Placing objects at locations**

:math:`*: L \times P  \rightarrow P` (locate an object :math:`p \in P` at location :math:`l \in L`, i.e. ``p.moved(l)``)

:math:`*: L \times S  \rightarrow S` (locate an object :math:`s \in S` at location :math:`l \in L`, i.e. ``s.moved(l)``)

:math:`*: L \times C  \rightarrow C` (locate an object :math:`c \in C` at location :math:`l \in L`, i.e. ``c.moved(l)``)
