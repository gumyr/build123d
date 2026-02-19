import math

from build123d import CenterOf, Compound, ShapeList, Vector, VectorLike, Vertex
from build123d.topology import Shape

VIEW_PRESETS = {
    "isometric": {
        "elevation": math.degrees(math.atan2(1.0, math.sqrt(2))),
        "azimuth": 45.0,
    },
    "dimetric": {"elevation": math.degrees(math.atan2(1.0, 2.0)), "azimuth": 45.0},
    "trimetric": {"elevation": 20.0, "azimuth": 30.0},
    # Orthographic presets
    "front": {"elevation": 0.0, "azimuth": 0.0},
    "back": {"elevation": 0.0, "azimuth": 180.0},
    "left": {"elevation": 0.0, "azimuth": 90.0},
    "right": {"elevation": 0.0, "azimuth": 270.0},
    "top": {"elevation": 90.0, "azimuth": 0.0},
    "bottom": {"elevation": -90.0, "azimuth": 0.0},
}


def get_view_coords(view: str | dict[str, float] | tuple[float, float]):
    """Get elevation/azimuth coordinates from view string or convert from tuple to dict"""
    if view in VIEW_PRESETS:
        coords = VIEW_PRESETS[view]
    elif isinstance(view, dict):
        coords = view
    elif isinstance(view, tuple):
        coords = dict(zip(("elevation", "azimuth"), view))
    else:
        raise ValueError(f"Invalid view '{view}' of type {type(view)}")

    return coords


def camera_projection(
    target: Shape | ShapeList | list | VectorLike,
    elevation: float,
    azimuth: float,
    scalar: float = 2.5,
):
    """Get camera position and target from Shape center and Horizontal Coordinate System.
    Always resets camera. Front facing camera has elevation 0 and azimuth 0

    Args:
        shape (Shape | ShapeList): Shape to center camera on
        elevation (float): vertical angle from horizontal plane (-90., 90.)
        azimuth (float): horizontal angle from front facing camera using right-hand rule (-180., 180.)
        scalar (float, optional): distance multiplier for point targets to avoid clipping. 
            Not necessary for shapes. Defaults to 2.5
    Returns:
        dict with "position", "target"
    """

    def flatten(items):
        for item in items:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield item

    if isinstance(target, (Vertex, Vector, tuple)):
        center = Vector(tuple(target) if isinstance(target, Vertex) else target)
        distance = scalar

    elif isinstance(target, (Shape, ShapeList, list)):
        shape = (
            Compound(children=list(flatten(target)))
            if isinstance(target, (ShapeList, list))
            else target
        )
        center = shape.center(CenterOf.BOUNDING_BOX)
        distance = shape.bounding_box().diagonal * scalar

    else:
        raise TypeError(f"Target type '{type(target)}' not supported")

    el, az = math.radians(elevation), math.radians(-azimuth + 90)
    position = (
        center.X + distance * math.cos(el) * math.cos(az),
        center.Y - distance * math.cos(el) * math.sin(az),
        center.Z + distance * math.sin(el),
    )

    return {
        "position": position,
        "target": tuple(center),
    }
