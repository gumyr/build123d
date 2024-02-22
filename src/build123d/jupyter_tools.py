"""

name: jupyter_tools.py

desc:
    Based on CadQuery version.

license:

    Copyright 2022 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

# pylint: disable=no-name-in-module
from json import dumps
from typing import Any, Dict, List
from IPython.display import Javascript
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter

DEFAULT_COLOR = [1, 0.8, 0, 1]

TEMPLATE_RENDER = """

function render(data, parent_element, ratio){{

    // Initial setup
    const renderWindow = vtk.Rendering.Core.vtkRenderWindow.newInstance();
    const renderer = vtk.Rendering.Core.vtkRenderer.newInstance({{ background: [1, 1, 1 ] }});
    renderWindow.addRenderer(renderer);

    // iterate over all children children
    for (var el of data){{
        var trans = el.position;
        var rot = el.orientation;
        var rgba = el.color;
        var shape = el.shape;

        // load the inline data
        var reader = vtk.IO.XML.vtkXMLPolyDataReader.newInstance();
        const textEncoder = new TextEncoder();
        reader.parseAsArrayBuffer(textEncoder.encode(shape));

        // setup actor,mapper and add
        const mapper = vtk.Rendering.Core.vtkMapper.newInstance();
        mapper.setInputConnection(reader.getOutputPort());
        mapper.setResolveCoincidentTopologyToPolygonOffset();
        mapper.setResolveCoincidentTopologyPolygonOffsetParameters(0.5,100);

        const actor = vtk.Rendering.Core.vtkActor.newInstance();
        actor.setMapper(mapper);

        // set color and position
        actor.getProperty().setColor(rgba.slice(0,3));
        actor.getProperty().setOpacity(rgba[3]);

        actor.rotateZ(rot[2]*180/Math.PI);
        actor.rotateY(rot[1]*180/Math.PI);
        actor.rotateX(rot[0]*180/Math.PI);

        actor.setPosition(trans);

        renderer.addActor(actor);

    }};

    renderer.resetCamera();

    const openglRenderWindow = vtk.Rendering.OpenGL.vtkRenderWindow.newInstance();
    renderWindow.addView(openglRenderWindow);

    // Add output to the "parent element"
    var container;
    var dims;

    if(typeof(parent_element.appendChild) !== "undefined"){{
        container = document.createElement("div");
        parent_element.appendChild(container);
        dims = parent_element.getBoundingClientRect();
    }}else{{
        container = parent_element.append("<div/>").children("div:last-child").get(0);
        dims = parent_element.get(0).getBoundingClientRect();
    }};

    openglRenderWindow.setContainer(container);

    // handle size
    if (ratio){{
        openglRenderWindow.setSize(dims.width, dims.width*ratio);
    }}else{{
        openglRenderWindow.setSize(dims.width, dims.height);
    }};

    // Interaction setup
    const interact_style = vtk.Interaction.Style.vtkInteractorStyleManipulator.newInstance();

    const manips = {{
        rot: vtk.Interaction.Manipulators.vtkMouseCameraTrackballRotateManipulator.newInstance(),
        pan: vtk.Interaction.Manipulators.vtkMouseCameraTrackballPanManipulator.newInstance(),
        zoom1: vtk.Interaction.Manipulators.vtkMouseCameraTrackballZoomManipulator.newInstance(),
        zoom2: vtk.Interaction.Manipulators.vtkMouseCameraTrackballZoomManipulator.newInstance(),
        roll: vtk.Interaction.Manipulators.vtkMouseCameraTrackballRollManipulator.newInstance(),
    }};

    manips.zoom1.setControl(true);
    manips.zoom2.setScrollEnabled(true);
    manips.roll.setShift(true);
    manips.pan.setButton(2);

    for (var k in manips){{
        interact_style.addMouseManipulator(manips[k]);
    }};

    const interactor = vtk.Rendering.Core.vtkRenderWindowInteractor.newInstance();
    interactor.setView(openglRenderWindow);
    interactor.initialize();
    interactor.bindEvents(container);
    interactor.setInteractorStyle(interact_style);

    // Orientation marker

    const axes = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
    axes.setXPlusFaceProperty({{text: '+X'}});
    axes.setXMinusFaceProperty({{text: '-X'}});
    axes.setYPlusFaceProperty({{text: '+Y'}});
    axes.setYMinusFaceProperty({{text: '-Y'}});
    axes.setZPlusFaceProperty({{text: '+Z'}});
    axes.setZMinusFaceProperty({{text: '-Z'}});

    const orientationWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({{
        actor: axes,
        interactor: interactor }});
    orientationWidget.setEnabled(true);
    orientationWidget.setViewportCorner(vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.BOTTOM_LEFT);
    orientationWidget.setViewportSize(0.2);

}};
"""

TEMPLATE = (
    TEMPLATE_RENDER
    + """

new Promise(
  function(resolve, reject)
  {{
    if (typeof(require) !== "undefined" ){{
        require.config({{
         "paths": {{"vtk": "https://unpkg.com/vtk"}},
        }});
        require(["vtk"], resolve, reject);
    }} else if ( typeof(vtk) === "undefined" ){{
        var script = document.createElement("script");
    	script.onload = resolve;
    	script.onerror = reject;
    	script.src = "https://unpkg.com/vtk.js";
    	document.head.appendChild(script);
    }} else {{ resolve() }};
 }}
).then(() => {{
    var parent_element = {element};
    var data = {data};
    render(data, parent_element, {ratio});
}});
"""
)


def to_vtkpoly_string(
    shape: Any, tolerance: float = 1e-3, angular_tolerance: float = 0.1
) -> str:
    """to_vtkpoly_string

    Args:
        shape (Shape): object to convert
        tolerance (float, optional): Defaults to 1e-3.
        angular_tolerance (float, optional): Defaults to 0.1.

    Raises:
        ValueError: not a valid Shape

    Returns:
        str: vtkpoly str
    """
    if not hasattr(shape, "wrapped"):
        raise ValueError(f"Type {type(shape)} is not supported")

    writer = vtkXMLPolyDataWriter()
    writer.SetWriteToOutputString(True)
    writer.SetInputData(shape.to_vtk_poly_data(tolerance, angular_tolerance, True))
    writer.Write()

    return writer.GetOutputString()


def display(shape: Any) -> Javascript:
    """display

    Args:
        shape (Shape): object to display

    Raises:
        ValueError: not a valid Shape

    Returns:
        Javascript: code
    """
    payload: List[Dict[str, Any]] = []

    if not hasattr(shape, "wrapped"):  # Is a "Shape"
        raise ValueError(f"Type {type(shape)} is not supported")

    payload.append(
        {
            "shape": to_vtkpoly_string(shape),
            "color": DEFAULT_COLOR,
            "position": [0, 0, 0],
            "orientation": [0, 0, 0],
        }
    )
    code = TEMPLATE.format(data=dumps(payload), element="element", ratio=0.5)

    return Javascript(code)
