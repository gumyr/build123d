from build123d import (
    Compound,
    ShapeList,
    Circle,
    Pos,
    LineType,
    Export2D,
    ExportSVG,
    Unit,
)
from build123d.topology import Shape
from .camera import camera_projection, get_view_coords


def write_svg(
    label: str,
    layers: dict | None = None,
    height: float = 300,
    margin: float = 0,
    unit: Unit = Unit.MM,
):
    """Write svg from a combination of projected shapes and predefined layers.

    Each layer is defined by a label key and value dict of layer shapes and settings. Only "shapes"
    is required to define a layer and default settings are filled. Layers are ordered back to front.

    Example layers:
    layers = {
        "box": {"shapes": Box(1, 1, 1)},
        "group": {"shapes": [Sphere(1), Cylinder(1, 1)], "line_weight": 1},
    }

    Layer values format and defaults:
    layer = {
        "shapes": Shape | ShapeList # required
        "fill_color": Color (None) # ColorIndex | RGB | Color | None
        "line_color": Color (Export2D.DEFAULT_COLOR_INDEX), # ColorIndex | RGB | Color | None
        "line_weight": float (Export2D.DEFAULT_LINE_WEIGHT),  # float,  in millimeters
        "line_type": LineType (Export2D.DEFAULT_LINE_TYPE), # LineType
    }

    Special layer defaults for "visible" and "hidden":
    layers = {
        "visible": {"line_weight": default_layer["line_weight"] * 3},
        "hidden": {
            "line_weight": default_layer["line_weight"] / 2,
            "line_color": (99, 99, 99),
            "line_type": LineType.PHANTOM}
    }

    Args:
        label (str): filename
        to_project (Shape | ShapeList): shapes to project to view
        view (str | dict[str, float] | tuple[float, float]): view to project to as either string or
            elevation/azimuth pair. Defaults to "top"
        layers (dict): dict of dicts defining layer shapes and svg shape properties
        height (float, optional): target height of svg in unit. Defaults to 300
        margin (float, optional): margin of foreground to svg size in unit. Defaults to 0
        show_hidden (float, optional): show hidden layer from projection. Defaults to True
        unit (Unit): canvas units in MM, IN, or CM. Defaults to MM
    """
    default_layer = {
        "fill_color": None,  # ColorIndex | RGB | Color | None
        "line_color": Export2D.DEFAULT_COLOR_INDEX,  # ColorIndex | RGB | Color | None
        "line_weight": 1,  # float,  in millimeters
        "line_type": Export2D.DEFAULT_LINE_TYPE,  # LineType
    }

    special_layers = {
        "visible": {
            **default_layer,
            **{"line_weight": default_layer["line_weight"] * 2},
        },
        "hidden": {
            **default_layer,
            **{
                "line_weight": default_layer["line_weight"] / 2,
                "line_color": (99, 99, 99),
                "line_type": LineType.PHANTOM,
            },
        },
    }

    # Set layer defaults
    if layers is None:
        print(label, "Nothing to write")
        return

    new_layers = {}
    for key, value in layers.items():
        if key in special_layers:
            new_layers.update({key: {**special_layers[key], **value}})
        else:
            new_layers.update({key: {**default_layer, **value}})

    for key, value in special_layers.items():
        if key not in new_layers:
            new_layers.update({key: special_layers[key]})

    layers = new_layers

    # Remove layers without shapes
    all_shapes = []
    layers = {k: v for k, v in layers.items() if v.get("shapes") is not None}

    # Normalize canvas scale to size of all shapes
    for v in layers.values():
        shapes = v["shapes"]
        if not isinstance(shapes, list):
            shapes = [shapes]
        all_shapes.extend(shapes)

    scale_factor = (height - 2 * margin) / Compound(
        children=all_shapes
    ).bounding_box().size.Y

    # Push hidden to back
    if "hidden" in layers:
        layers = {"hidden": layers.pop("hidden"), **layers}

    # Author svg
    exporter = ExportSVG(unit, scale_factor, margin)
    for layer, values in layers.items():
        shapes = values["shapes"]
        values.pop("shapes")
        exporter.add_layer(layer, **values)
        exporter.add_shape(shapes, layer=layer)

    exporter.write(f"{label}.svg")


def project_shapes(shapes: Shape | ShapeList, view="isometric", show_hidden=True):
    """Project shapes to svg layers

    Args:
        shapes (Shape | ShapeList): shapes to project to view
        view (str | dict[str, float] | tuple[float, float]): view to project to as either string or
            elevation/azimuth pair. Defaults to "isometric"
        show_hidden (float, optional): show hidden layer from projection. Defaults to True
    """
    shape = shapes if isinstance(shapes, Shape) else Compound(shapes)
    camera = camera_projection(shape, **get_view_coords(view))
    visible, hidden = shape.project_to_viewport(
        camera["position"], look_at=camera["target"]
    )
    layers = {"visible": {"shapes": visible}}
    if show_hidden:
        layers["hidden"] = {"shapes": hidden}

    return layers


def make_points(
    points: list, other: Shape | ShapeList, symbol: str = "o", fraction: float = 25.0
):
    """Depict points as a symbol sized relative to other

    Symbols: "o",
    """
    other = other if isinstance(other, Shape) else Compound(other)
    scale_factor = other.bounding_box().size.Y / fraction

    if symbol == "o":
        shape = Circle(scale_factor / 2)
    else:
        raise NotImplementedError(f"Symbol '{symbol}' not implemented")

    return [Pos(p) * shape for p in points]
