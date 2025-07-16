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
import os
import uuid
from string import Template
from typing import Any
from IPython.display import HTML
from build123d.vtk_tools import to_vtkpoly_string

DEFAULT_COLOR = [1, 0.8, 0, 1]

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "template_render.js"), encoding="utf-8") as f:
    TEMPLATE_JS = f.read()


def shape_to_html(shape: Any) -> HTML:
    """shape_to_html

    Args:
        shape (Shape): object to display

    Raises:
        ValueError: not a valid Shape

    Returns:
        HTML: html code
    """
    payload: list[dict[str, Any]] = []

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

    # A new div with a unique id, plus the JS code templated with the id
    div_id = "shape-" + uuid.uuid4().hex[:8]
    code = Template(TEMPLATE_JS).substitute(
        data=dumps(payload), div_id=div_id, ratio=0.5
    )
    html = HTML(f"<div id={div_id}></div><script>{code}</script>")

    return html
