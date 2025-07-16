.. _tech_drawing_tutorial:

##########################
Technical Drawing Tutorial
##########################

This example demonstrates how to generate a standard technical drawing of a 3D part 
using `build123d`. It creates orthographic and isometric views of a Nema 23 stepper 
motor and exports the result as an SVG file suitable for printing or inspection.

Overview
--------

A technical drawing represents a 3D object in 2D using a series of standardized views. 
These include:

- **Plan (Top View)** – as seen from directly above (Z-axis down)
- **Front Elevation** – looking at the object head-on (Y-axis forward)
- **Side Elevation (Right Side)** – viewed from the right (X-axis)
- **Isometric Projection** – a 3D perspective view to help visualize depth

Each view is aligned to a position on the page and optionally scaled or annotated.

How It Works
------------

The script uses the `project_to_viewport` method to project the 3D part geometry into 2D. 
A helper function, `project_to_2d`, sets up the viewport (camera origin and up direction) 
and places the result onto a virtual drawing sheet.

The steps involved are:

1. Load or construct a 3D part (in this case, a stepper motor).
2. Define a `TechnicalDrawing` border and title block using A4 page size.
3. Generate each of the standard views and apply transformations to place them.
4. Add dimensions using `ExtensionLine` and labels using `Text`.
5. Export the drawing using `ExportSVG`, separating visible and hidden edges by layer 
   and style.

Result
------

.. image:: /assets/stepper_drawing.svg
   :alt: Stepper motor technical drawing
   :class: align-center
   :width: 80%

Try It Yourself
---------------

You can modify the script to:

- Replace the part with your own `Part` model
- Adjust camera angles and scale
- Add other views (bottom, rear)
- Enhance with more labels and dimensions

Code
----

.. literalinclude:: technical_drawing.py
    :language: python
    :start-after: [code]
    :end-before: [end]

Dependencies
------------

This example depends on the following packages:

- `build123d`
- `bd_warehouse` (for the `StepperMotor` part)
- `ocp_vscode` (for local preview)
