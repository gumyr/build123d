############
Introduction
############

***********
Key Aspects
***********

The following sections describe some of the key aspects of build123d and illustrate
why one might choose this open source system over proprietary options like SolidWorks,
OnShape, Fusion 360, or even other open source systems like Blender, or OpenSCAD.

Boundary Representation (BREP) Modelling
========================================

Boundary representation (BREP) and mesh-based CAD systems are both used to
create and manipulate 3D models, but they differ in the way they represent and
store the models.

Advantages of BREP-based CAD systems (e.g. build123d & SolidWorks):

* Precision: BREP-based CAD systems use mathematical representations to define
  the shape of an object, which allows for more precise and accurate modeling of
  complex shapes.
* Topology: BREP-based CAD systems maintain topological information of the 3D
  model, such as edges, faces and vertices. This allows for more robust and stable
  modeling, such as Boolean operations.
* Analytical modeling: BREP-based CAD systems can take advantage of the
  topological information to perform analytical operations such as collision
  detection, mass properties calculations, and finite element analysis.
* Features-based modeling: BREP-based CAD systems are often feature-based, which
  means that the model is built by creating and modifying individual features,
  such as holes, fillets, and chamfers. This allows for parametric design and easy
  modification of the model.
* Efficient storage: BREP-based CAD systems use a compact representation to
  store the 3D model, which is more efficient than storing a large number of
  triangles used in mesh-based systems.


Advantages of Mesh-based CAD systems (e.g. Blender, OpenSCAD):

* Simplicity: Mesh-based CAD systems use a large number of triangles to
  represent the surface of an object, which makes them easy to use and understand.
* Real-time rendering: Mesh-based CAD systems can be rendered in real-time,
  which is useful for applications such as video games and virtual reality.
* Flexibility: Mesh-based CAD systems can be easily exported to other 3D
  modeling and animation software, which makes them a good choice for use in the
  entertainment industry.
* Handling of freeform surfaces: Mesh-based systems are better equipped to
  handle freeform surfaces, such as those found in organic shapes, as they do not
  rely on mathematical representation.
* Handling of large datasets: Mesh-based systems are more suitable for handling
  large datasets such as point clouds, as they can be easily converted into a mesh
  representation.

Parameterized Models
====================

Parametrized CAD systems are more effective than non-parametric CAD systems in
several ways:

* Reusability: Parametrized CAD models can be easily modified by changing a set
  of parameters, such as the length or width of an object, rather than having to
  manually edit the geometry. This makes it easy to create variations of a design
  without having to start from scratch.
* Design exploration: Parametrized CAD systems allow for easy exploration of
  different design options by changing the parameters and quickly visualizing the
  results.  This can save a lot of time and effort during the design process.
* Constraints and relationships: Parametrized CAD systems allow for the
  definition of constraints and relationships between different parameters. This
  ensures that the model remains valid and functional even when parameters are
  changed.
* Automation: Parametrized CAD systems can be automated to perform repetitive
  tasks, such as generating detailed drawings or creating parts lists. This can
  save a lot of time and effort and reduce the risk of errors.
* Collaboration: Parametrized CAD systems allow different team members to work
  on different aspects of a design simultaneously and ensure that the model
  remains consistent across different stages of the development process.
* Document management: Parametrized CAD systems can generate engineering
  drawings, BOMs, and other documents automatically, which makes it easier to
  manage and track the design history.

In summary, parametrized CAD systems are more effective than non-parametric CAD
systems because they provide a more efficient and flexible way to create and
modify designs, and can be easily integrated into the design, manufacturing, and
documentation process.

Python Programming Language
===========================

Python is a popular, high-level programming language that has several advantages
over other programming languages:

* Readability: Python code is easy to read and understand, with a clear and
  consistent syntax. This makes it a great language for beginners and for teams of
  developers who need to collaborate on a project.
* Versatility: Python is a general-purpose language that can be used for a wide
  range of tasks, including web development, scientific computing, data analysis,
  artificial intelligence, and more. This makes it a great choice for developers
  who need to work on multiple types of projects.
* Large community: Python has a large and active community of developers who
  contribute to the language and its ecosystem. This means that there are many
  libraries and frameworks available for developers to use, which can save a lot
  of time and effort.
* Good for data science, machine learning, and CAD: Python has a number of libraries
  such as numpy, pandas, scikit-learn, tensorflow, and cadquery which are popularly
  used in data science and machine learning and CAD.
* High-level language: Python is a high-level language, which means it abstracts
  away many of the low-level details of the computer.  This makes it easy to write
  code quickly and focus on solving the problem at hand.
* Cross-platform: Python code runs on many different platforms, including
  Windows, Mac, and Linux, making it a great choice for developers who need to
  write code that runs on multiple operating systems.
* Open-source: Python is an open-source programming language, which means it is
  free to use and distribute.  This makes it accessible to developers of all
  levels and budgets.
* Large number of libraries and modules: Python has a vast collection of
  libraries and modules that make it easy to accomplish complex tasks such as
  connecting to web servers, reading and modifying files, and connecting to
  databases.

Open Source Software
====================

Open source and proprietary software systems are different in several ways: B
Licensing: Open source software is licensed in a way that allows users to view,
modify, and distribute the source code, while proprietary software is closed
source and the source code is not available to the public.

* Ownership: Open source software is usually developed and maintained by a
  community of developers, while proprietary software is owned by a company or
  individual.
* Cost: Open source software is typically free to use, while proprietary
  software may require payment for a license or subscription.  Customization: Open
  source software can be modified and customized by users and developers, while
  proprietary software is typically not modifiable by users.
* Support: Open source software may have a larger community of users who can
  provide support, while proprietary software may have a smaller community and
  relies on the company for support.  Security: Open source software can be
  audited by a large community of developers, which can make it more secure, while
  proprietary software may have fewer eyes on the code and may be more vulnerable
  to security issues.
* Interoperability: Open source software may have better interoperability with
  other software and platforms, while proprietary software may have more limited
  compatibility.
* Reliability: Open source software can be considered as reliable as proprietary
  software. It is usually used by large companies, governments, and organizations
  and has been tested by a large number of users.

In summary, open source and proprietary software systems are different in terms
of licensing, ownership, cost, customization, support, security,
interoperability, and reliability. Open source software is typically free to use
and can be modified by users and developers, while proprietary software is
closed-source and may require payment for a license or subscription. Open source
software may have a larger community of users who can provide support, while
proprietary software may have a smaller community and relies on the company for
support.

Source Code Control Systems
===========================

Most GUI based CAD systems provide version control systems which represent the
CAD design and its history. They allows developers to see changes made to the design
over time, in a format that is easy to understand.

On the other hand, a source code control system like Git, is a command-line tool
and it provides more granular control over the code. This makes it suitable for
more advanced users and developers who are comfortable working with command-line
interfaces. A source code control system like Git is more flexible and allows
developers to perform tasks like branching and merging, which are not easily
done with a GUI version control system. Systems like Git have several advantages,
including:

* Version control: Git allows developers to keep track of changes made to the
  code over time, making it easy to revert to a previous version if necessary.
* Collaboration: Git makes it easy for multiple developers to work on the same
  codebase simultaneously, with the ability to merge changes from different
  branches of development.
* Backup: Git provides a way to backup and store the codebase in a remote
  repository, like GitHub. This can serve as a disaster recovery mechanism, in
  case of data loss.
* Branching: Git allows developers to create multiple branches of a project for
  different features or bug fixes, which can be easily merged into the main
  codebase once they are complete.
* Auditing: Git allows you to see who made changes to the code, when and what
  changes were made, which is useful for auditing and debugging.
* Open-source development: Git makes it easy for open-source developers to
  contribute to a project and share their work with the community.
* Flexibility: Git is a distributed version control system, which means that
  developers can work independently and offline.  They can then push their changes
  to a remote repository when they are ready to share them with others.

In summary, GUI version control systems are generally more user-friendly and
easier to use, while source code control systems like Git offer more flexibility
and control over the code. Both can be used to achieve the same goal, but they
cater to different types of users and use cases.

Automated Testing
=================

Users of source based CAD systems can benefit from automated testing which improves
their source code by:

* Finding bugs: Automated tests can detect bugs in the code, which can then be
  fixed before the code is released.  This helps to ensure that the code is of
  higher quality and less likely to cause issues when used.
* Regression testing: Automated tests can be used to detect regressions, which
  are bugs that are introduced by changes to the codebase. This helps to ensure
  that changes to the code do not break existing functionality.
* Documenting code behavior: Automated tests can serve as documentation for how
  the code is supposed to behave. This makes it easier for developers to
  understand the code and make changes without breaking it.
* Improving code design: Writing automated tests often requires a good
  understanding of the code and how it is supposed to behave. This can lead to a
  better design of the code, as developers will have a better understanding of the
  requirements and constraints.
* Saving time and cost: Automated testing can save time and cost by reducing the
  need for manual testing. Automated tests can be run quickly and often, which
  means that bugs can be found and fixed early in the development process, which
  is less expensive than finding them later.
* Continuous integration and delivery: Automated testing can be integrated into
  a continuous integration and delivery (CI/CD) pipeline. This means that tests
  are run automatically every time code is committed and can be integrated with
  other tools such as code coverage, static analysis and more.
* Improving maintainability: Automated tests can improve the maintainability of
  the code by making it easier to refactor and change the codebase. This is
  because automated tests provide a safety net that ensures that changes to the
  code do not introduce new bugs.

Overall, automated testing is an essential part of the software development
process, it helps to improve the quality of the code by detecting bugs early,
documenting code behavior, and reducing the cost of maintaining and updating the
code.

Automated Documentation
=======================

The Sphinx automated documentation system was used to create the page you are
reading now and can be used for user design documentation as well.  Such systems
are used for several reasons:

* Consistency: Sphinx and other automated documentation systems can generate
  documentation in a consistent format and style, which makes it easier to
  understand and use.
* Automation: Sphinx can automatically generate documentation from source code
  and comments, which saves time and effort compared to manually writing
  documentation.
* Up-to-date documentation: Automated documentation systems like Sphinx can
  update the documentation automatically when the code changes, ensuring that the
  documentation stays up-to-date with the code.
* Searchability: Sphinx and other automated documentation systems can include
  search functionality, which makes it easy to find the information you need.
* Cross-referencing: Sphinx can automatically create links between different
  parts of the documentation, making it easy to navigate and understand the
  relationships between different parts of the code.
* Customizable: Sphinx and other automated documentation systems can be
  customized to match the look and feel of your company's documentation.
* Multiple output formats: Sphinx can generate documentation in multiple formats
  such as HTML, PDF, ePub, and more.
* Support for multiple languages: Sphinx can generate documentation in multiple
  languages, which can make it easier to support international users.
* Integration with code management: Sphinx can be integrated with code
  management tools like Git, which allows documentation to be versioned along with
  the code.

In summary, automated documentation systems like Sphinx are used to generate
consistent, up-to-date, and searchable documentation from source code and
comments. They save time and effort compared to manual documentation, and can be
customized to match the look and feel of your company's documentation. They also
provide multiple output formats, support for multiple languages and can be
integrated with code management tools.


************************
Advantages Over CadQuery
************************

.. include:: advantages.rst
