.. _where_next:

##########
Where Next
##########

*************************
Builder or algebra mode?
*************************

Every build123d feature is available in two modes, and the choice between them
is one of style.

* **Builder mode** uses Python ``with`` blocks. A builder collects the objects
  created inside it, tracks what is pending and what was last changed, and
  places objects at the active locations. It suits designs described as a
  sequence of steps, much as they would be made in a GUI CAD program. See
  :doc:`key_concepts_builder`.

* **Algebra mode** has no hidden state. Shapes are values that are combined
  with ``+``, ``-`` and ``&`` and positioned with ``*``. It suits those who
  prefer explicit code and is the shorter of the two for small parts. See
  :doc:`key_concepts_algebra`.

Neither choice is permanent: the objects and operations are the same in both,
the two can be mixed in one design, and most examples in this documentation are
shown both ways.

*****************
What to read next
*****************

* To learn by doing, work through the :doc:`introductory_examples`, which go
  from simple to complex in both modes, then
  :doc:`Designing a Part <tutorial_design>` and the
  :doc:`Selector Tutorial <tutorial_selectors>`. The other
  :doc:`tutorials <tutorials>` each take up one subject.

* To understand how build123d models shapes before going further, read
  :doc:`key_concepts`.

* If you are coming from OpenSCAD, start with :doc:`OpenSCAD`.

* To look something up, use the :ref:`cheat_sheet`.
