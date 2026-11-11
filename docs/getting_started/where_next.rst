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
  :doc:`/explanation/key_concepts_builder`.

* **Algebra mode** has no hidden state. Shapes are values that are combined
  with ``+``, ``-`` and ``&`` and positioned with ``*``. It suits those who
  prefer explicit code and is the shorter of the two for small parts. See
  :doc:`/explanation/key_concepts_algebra`.

Neither choice is permanent: the objects and operations are the same in both,
the two can be mixed in one design, and most examples in this documentation are
shown both ways.

*****************
What to read next
*****************

* To learn by doing, work through the :doc:`tutorials </tutorials/index>`. The
  first seven, starting with :ref:`tutorial_sketch_then_extrude`, are a series
  that builds one part each in both modes;
  :doc:`Designing a Part </tutorials/tutorial_design>` then shows how to plan a
  part of your own. The remaining tutorials each take up one subject.

* To understand how build123d models shapes before going further, read
  :doc:`/explanation/key_concepts`.

* If you are coming from OpenSCAD, start with :doc:`/how_to/OpenSCAD`.

* To look something up, use the :ref:`cheat_sheet`.
