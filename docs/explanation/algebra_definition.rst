.. _algebra_definition:

Algebraic definition
========================

This page states formally what :ref:`how_algebra_mode_works` describes by
example. Equality between shapes means equality of the sets of points they
occupy, to the tolerance of the geometric kernel.

Objects and arithmetic
------------------------

**Set definitions:**

:math:`C^n` is the set of all shapes ``s`` with ``s._dim = n``, for :math:`n = 1, 2, 3`.

:math:`C^3` contains every ``Part`` object, and also every ``Solid`` and every ``Compound`` of solids

:math:`C^2` contains every ``Sketch`` object, and also every ``Face`` and every ``Compound`` of faces

:math:`C^1` contains every ``Curve`` object, and also every ``Edge``, every ``Wire`` and every ``Compound`` of them

``Part``, ``Sketch`` and ``Curve`` are the classes a design is normally written
in, and the results of the operations below are of those classes wherever the
result is a single connected piece.

**Neutral elements:**

:math:`c^3_0` is the empty ``Part`` object ``p0 = Part()`` with ``p0._dim = 3`` and ``p0.is_empty``

:math:`c^2_0` is the empty ``Sketch`` object ``s0 = Sketch()`` with ``s0._dim = 2`` and ``s0.is_empty``

:math:`c^1_0` is the empty ``Curve`` object ``c0 = Curve()`` with ``c0._dim = 1`` and ``c0.is_empty``

The empty objects are the zeros of the algebra: :math:`a + c_0 = a`,
:math:`c_0 + a = a`, :math:`c_0 - a = c_0` and :math:`a \; \& \; c_0 = c_0`.
An operation that leaves nothing, such as ``a - a``, returns the empty object
of its set rather than failing. See :ref:`empty_shapes`.


**Sets of predefined basic shapes:**

:math:`B^3 := \lbrace` ``Part``, ``Box``, ``Cylinder``, ``Cone``, ``Sphere``, ``Torus``, ``Wedge``, ``Hole``, ``CounterBoreHole``, ``CounterSinkHole`` :math:`\rbrace`

:math:`B^2 := \lbrace` ``Sketch``, ``Rectangle``, ``Circle``, ``Ellipse``, ``Polygon``, ``RegularPolygon``, ``Text``, ``Trapezoid``, ``SlotCenterPoint``, ``SlotCenterToCenter``, ``SlotCurve``, ``SlotOverall`` :math:`\rbrace`

:math:`B^1 := \lbrace` ``Curve``, ``Bezier``, ``FilletPolyline``, ``PolarLine``, ``Polyline``, ``Spline``, ``Helix``, ``CenterArc``, ``EllipticalCenterArc``, ``ParabolicCenterArc``, ``HyperbolicCenterArc``, ``RadiusArc``, ``SagittaArc``, ``TangentArc``, ``ThreePointArc``, ``JernArc`` :math:`\rbrace`

with :math:`B^3 \subset C^3, B^2 \subset C^2` and :math:`B^1 \subset C^1`


**Operations:**

:math:`+: C^n \times C^n \rightarrow C^n` with :math:`(a,b) \mapsto a + b`,  :math:`\;` for :math:`n=1,2,3`

    :math:`\; a + b :=` ``a.fuse(b)``

:math:`-: C^n \times C^n \rightarrow C^n` with :math:`(a,b) \mapsto a - b`,  :math:`\;` for :math:`n=1,2,3`

    :math:`\; a - b :=` ``a.cut(b)``

:math:`\&: C^n \times C^n \rightarrow C^n` with :math:`(a,b) \mapsto a \; \& \; b`,  :math:`\;` for :math:`n=1,2,3`

    :math:`\; a \; \& \; b :=` ``a.intersect(b)``

    * The following relationship holds: :math:`a \; \& \; b = (a + b) - (a - b) - (b - a)`
    * For :math:`n=3` the result is regularised: two solids that only touch,
      on a face, an edge or a corner, have :math:`c^3_0` in common.
    * For :math:`n=1,2` two shapes that touch without overlapping return what
      they share one dimension down: two faces that share an edge return that
      edge as a ``Curve``, and two curves that meet or cross at a point return
      a ``Vertex``. Such a result is not a member of :math:`C^n`. The laws
      below are stated for the part of dimension :math:`n`, that is, up to
      contact of lower dimension.

For :math:`n=1`, :math:`+` joins curves that meet end to end into a single
``Wire``. Where two curves overlap and share an end, both are kept, so the
result holds the same points but its edges overlap and its total length is
greater. The laws below hold for curves as sets of points.

``-`` is a binary operation. There is no unary minus: a shape has no negative,
and ``-a`` is not defined for the members of :math:`C^n`.

**Note:** ``Shell`` has ``_dim = 2`` but is not treated as a member of :math:`C^2`.
Adding to a ``Shell`` sews faces into a single connected surface instead of
fusing them, and raises ``ValueError`` when they cannot be sewn - see
:ref:`algebra_sewing`.


**Laws**

For :math:`n=1,2,3` and all :math:`a, b, c \in C^n`:

* :math:`+` and :math:`\&` are commutative: :math:`a + b = b + a` and :math:`a \; \& \; b = b \; \& \; a`
* :math:`+` and :math:`\&` are associative: :math:`(a + b) + c = a + (b + c)` and :math:`(a \; \& \; b) \; \& \; c = a \; \& \; (b \; \& \; c)`
* :math:`+` and :math:`\&` are idempotent: :math:`a + a = a` and :math:`a \; \& \; a = a`
* each absorbs the other: :math:`a + (a \; \& \; b) = a` and :math:`a \; \& \; (a + b) = a`
* each distributes over the other: :math:`a \; \& \; (b + c) = (a \; \& \; b) + (a \; \& \; c)` and :math:`a + (b \; \& \; c) = (a + b) \; \& \; (a + c)`
* :math:`c^n_0` is the identity of :math:`+` and annihilates :math:`\&`: :math:`a + c^n_0 = a` and :math:`a \; \& \; c^n_0 = c^n_0`
* :math:`a - b` is the complement of :math:`b` relative to :math:`a`: :math:`(a - b) \; \& \; b` has no part of dimension :math:`n`, and :math:`(a - b) + (a \; \& \; b) = a`

:math:`( C^n, \; +, \; \&, \; -, \; c^n_0)` is therefore a generalised Boolean
algebra: a distributive lattice with a least element in which every element
has a complement relative to any other. It has no greatest element, since
there is no shape that is "everything", and so no absolute complement.

* It is not a group under :math:`+`. Because :math:`a + a = a`, no element other
  than :math:`c^n_0` can have an inverse, and :math:`-` does not undo :math:`+`:
  in general :math:`(b - a) + a = a + b \ne b`.
* :math:`-` is neither commutative nor associative. The useful identities are
  :math:`a - (b + c) = (a - b) - c` and :math:`a - (b - c) = (a - b) + (a \; \& \; c)`,
  so in particular :math:`a - (b - c) \ne (a - b) + c`.


**Operands of different dimension**

:math:`+` is defined only between shapes of the same dimension. The other two
operations extend to mixed dimensions:

:math:`-: C^n \times C^m \rightarrow C^n \;` for :math:`m \ge n`

    What is removed must have the same or a higher dimension. The result has
    the dimension of what it is removed from.

:math:`\&: C^n \times C^m \rightarrow C^{\min(n,m)}`

    The common part of two shapes has the lower of their dimensions.


Locations, planes and location arithmetic
---------------------------------------------

**Set definitions:**

:math:`L  := \lbrace` ``Location((x, y, z), (a, b, c))`` :math:`: x,y,z \in R \land a,b,c \in R \rbrace\;`

    with :math:`a,b,c` being angles in degrees.

:math:`P  := \lbrace` ``Plane(o, x, z)`` :math:`: o,x,z ∈ R^3 \land \|x\| = \|z\| = 1 \land x \cdot z = 0\rbrace`

    with ``o`` being the origin and ``x``, ``z`` the x- and z-direction of the plane.

Neutral element: :math:`\; l_0 \in L`: ``Location()``

**Operations:**

:math:`*: L \times L \rightarrow L` with :math:`(l_1,l_2) \mapsto l_1 * l_2`

    :math:`\; l_1 * l_2 :=`  ``l1 * l2`` (multiply two locations)

:math:`*: P \times L \rightarrow L` with :math:`(p,l) \mapsto p * l`

    :math:`\; p * l :=` ``p.location * l`` (the location :math:`l \in L`, taken relative to plane :math:`p \in P`)

Inverse element: :math:`\; l^{-1} \in L`: ``l.inverse()``

:math:`( L, \; *, \; l_0)` is a group: :math:`*` is associative, :math:`l_0` is
its identity and every :math:`l` has the inverse :math:`l^{-1}`. It is not
abelian: in general :math:`l_1 * l_2 \ne l_2 * l_1`.


**Placing objects onto planes**

:math:`*: P \times C^n  \rightarrow C^n \;`  with :math:`(p,c) \mapsto p * c`,  :math:`\;` for :math:`n=1,2,3`

    Locate an object :math:`c \in C^n` onto plane :math:`p \in P`, i.e. ``c.moved(p.location)``

**Placing objects at locations**

:math:`*: L \times C^n  \rightarrow C^n \;`  with :math:`(l,c) \mapsto l * c`,  :math:`\;` for :math:`n=1,2,3`

    Locate an object :math:`c \in C^n` at location :math:`l \in L`, i.e. ``c.moved(l)``

Placement is compatible with the multiplication of locations:
:math:`(l_1 * l_2) * c = l_1 * (l_2 * c)` and :math:`l_0 * c = c`, so a chain of
placements may be read from the right, or multiplied out first.
