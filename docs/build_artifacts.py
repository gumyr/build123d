import argparse
import contextlib
import importlib
import hashlib
import json
import math
import sys
import shutil

from pathlib import Path
from collections.abc import Iterable

from tcv_screenshots import get_saved_models
from process_image import batch_screenshots, batch_thumbnails

from build123d import Vector, Vertex, Compound, ShapeList, CenterOf, VectorLike
from build123d.topology import Shape

DOCS_ROOT = Path(__file__).parent
ARTIFACT_FOLDER = "_build/assets"
ASSET_CONFIG_NAME = "asset_config"
DEFAULT_MODEL_CONFIG = {
    "cadWidth": 1000,
    "height": 1000,
}


@contextlib.contextmanager
def add_to_syspath(paths: Iterable[Path]):
    """Temporarily append paths to sys.path"""
    paths = [str(p) for p in paths]
    old_sys_path = sys.path.copy()
    sys.path.extend(paths)
    try:
        yield
    finally:
        sys.path[:] = old_sys_path


def hash_folders(folders: Iterable[Path]) -> str:
    """Compute hash of list of folder's contents"""
    h = hashlib.sha256()
    for folder in sorted(Path(f).resolve() for f in folders):
        for p in sorted(folder.rglob("*")):
            if p.is_dir() or p.name == ".asset-stamp":
                continue
            h.update(p.read_bytes())

    return h.hexdigest()


def build_artifacts(config_path: Path, *,  force=False):
    """Generate and copy build artifacts as defined by a folder's asset config
    
    The config is imported if it exists and sources are added. Sources are checked for changes by 
    hash and skipped if no changes.
    The artifact destination is set to the cwd as a destination for in process artifact generation 
    and sources are temporarily added to path. 

    If the config has `save_models`, that method is run to add screenshot models to global list. 
    Likewise, all `to_generate` items are imported to add any screenshot models to global list and 
    generate any assets to artifact destination. These imports are expected to run all required asset 
    creation outside of methods and class definitions. 
    """
    folder = config_path.parent
    sources = {folder}
    destination = DOCS_ROOT / ARTIFACT_FOLDER / folder.name
    empty_config = {
        "sources": [],
        "build": [],
        "thumbnails": [],
        "exceptions": []
    }

    if not destination.exists():
        destination.mkdir()

    with contextlib.chdir(destination):
        # Import asset config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config = {**empty_config, **config}

        for source in config["sources"]:
            sources.add((DOCS_ROOT / source).resolve())

        # Check for changes to sources
        new_hash = hash_folders(sources)
        stamp = destination / ".asset-stamp"
        if stamp.exists() and not force:
            old = json.loads(stamp.read_text())
            if old["input_hash"] == new_hash:
                return

        # Copy assets not found in static
        copy_assets(sources - {folder}, destination)

        with add_to_syspath(sources):
            # Save models and generate artifacts
            for module in config["build"]:
                importlib.import_module(module)

        if saved_models := get_saved_models():
            saved_models = [
                (obj, label, {**DEFAULT_MODEL_CONFIG, **model_config})
                for obj, label, model_config in saved_models
            ]
            generate_screenshots(saved_models, destination, config["exceptions"], config["thumbnails"])

    # Check contents of _static and write stamp
    if any(destination.iterdir()):
        stamp.write_text(json.dumps({"input_hash": new_hash,}))


def iter_assets(sources: Iterable[Path], exts: set[str]):
    """Find all assets in extensions list in sources"""
    exts = {e.lower().lstrip(".") for e in exts}

    for source in sources:
        source = Path(source)
        for p in source.rglob("*"):
            if p.is_file() and p.suffix.lower().lstrip(".") in exts:
                yield p


def copy_assets(sources: Iterable[Path], destination: Path):
    """Copy all assets to artifact destination"""
    extensions = {"3mf", "brep", "dxf", "glb", "jpg", "png", "step", "stl", "svg"}

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for artifact in iter_assets(sources, extensions):
        target = destination / artifact.name
        shutil.copy2(artifact, target)


def generate_screenshots(models: list[tuple], destination: Path, exceptions: dict | None, thumbnails: list | None):
    """Generate screenshots and batch resize/thumbnail creation"""
    import asyncio
    from tcv_screenshots.render import render_models_to_screenshots

    # Render models to screenshots
    print("\n=== Rendering models to screenshots ===")
    debug_models_dir = None
    fail_count = asyncio.run(
        render_models_to_screenshots(
            screenshots_process_examples(models),
            destination,
            headless=True,
            pause=False,
            debug=debug_models_dir is not None,
        )
    )
    if fail_count > 0:
        sys.exit(1)

    batch_screenshots(destination, exceptions)
    if thumbnails:
        batch_thumbnails(destination, thumbnails)


def screenshots_process_examples(
    models_to_process: list[tuple],
) -> list[tuple[str, dict]]:
    """Slimmed version of process_examples

    Args:
        models_to_process: Saved model tuples

    Returns:
        List of (name, data) tuples where data is {model, config}
    """
    # Import ocp_tessellate once (heavy import)
    from ocp_tessellate.convert import export_three_cad_viewer_js
    from tcv_screenshots.render import DEFAULT_CONFIG as TCV_DEFAULT_CONFIG

    processed_models = []

    for cad_object, output_name, example_config in models_to_process:
        # Merge defaults with example overrides
        if "reset_camera" in example_config:
            view = None
            if view in VIEW_PRESETS:
                view = VIEW_PRESETS[example_config["reset_camera"]]
            elif isinstance(example_config["reset_camera"], dict):
                view = example_config["reset_camera"]
            elif isinstance(example_config["reset_camera"], tuple):
                view = dict(zip(("elevation", "azimuth"), example_config["reset_camera"]))

            if view:
                example_config.update(view)
                example_config.pop("reset_camera")
        config = {**TCV_DEFAULT_CONFIG, **(example_config or {})}

        # Export model to JSON string
        model_json = export_three_cad_viewer_js(None, cad_object)
        model_data = json.loads(model_json)

        # Create combined data with model and config
        combined_data = {"model": model_data, "config": config}

        processed_models.append((output_name, combined_data))

    return processed_models


# View presets: {elevation(deg), azimuth (deg)}
# Isometric:  all axes equally foreshortened (~35.264°, 45°)
# Dimetric:   two axes equal, one different (common 2:1 engineering variant) (~26.565°, 45°)
# Trimetric:  all three axes foreshortened differently (20°, 30°)
VIEW_PRESETS = {
    "isometric":  {"elevation": math.degrees(math.atan2(1.0, math.sqrt(2))), "azimuth": 45.0},
    "dimetric":   {"elevation": math.degrees(math.atan2(1.0, 2.0)),         "azimuth": 45.0},
    "trimetric":  {"elevation": 20.0,                                       "azimuth": 30.0},
}

def camera_projection(target: Shape | ShapeList | list | VectorLike, elevation: float, azimuth: float, scalar: float = 2.5):
    """
    Get camera position and target from Shape center and Horizontal Coordinate System.
    Always resets camera. Front facing camera has elevation 0 and azimuth 0

    Args:
        shape (Shape | ShapeList): Shape to center camera on
        elevation (float): vertical angle from horizontal plane (-90., 90.)
        azimuth (float): horizontal angle from front facing camera using right-hand rule (-180., 180.)
        scalar (float, optional): distance multiplier for point targets to avoid clipping. Not necessary for shapes. Defaults to 2.5 
    Returns:
        dict with "position", "target"
    """

    if isinstance(target, (Vertex, Vector, tuple)):
        center = Vector(tuple(target) if isinstance(target, Vertex) else target)
        distance = scalar

    elif isinstance(target, (Shape, ShapeList, list)):
        shape = Compound(children=target) if isinstance(target, (ShapeList, list)) else target
        center = shape.center(CenterOf.BOUNDING_BOX)
        distance = shape.bounding_box().diagonal * scalar

    else:
        raise TypeError(f"Target type '{type(target)}' not supported")

    el, az   = math.radians(elevation), math.radians(-azimuth + 90)
    position = (
        center.X + distance * math.cos(el) * math.cos(az),
        center.Y - distance * math.cos(el) * math.sin(az),
        center.Z + distance * math.sin(el),
    )

    return {
        "position":   position,
        "target":     tuple(center),
    }


def batch_build_artifacts(root: str | Path, *, force: bool = False):
    root = Path(root).resolve()
    destination = DOCS_ROOT / ARTIFACT_FOLDER

    if not destination.exists():
        destination.mkdir()

    ignore = ["__pycache__"]
    folders = [p for p in root.rglob("*") if p.is_dir() and p.name not in ignore]
    if (root / (ASSET_CONFIG_NAME + ".py")).exists():
        folders.append(root)

    for folder in folders:
        config_path = folder / (ASSET_CONFIG_NAME + ".json")
        if config_path.exists():
            print("===== Processing " + folder.name + " =====")
            build_artifacts(config_path, force=force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="build_artifacts",
        description="Build screenshots, svgs, and other documentation assets from a directory and "
        "its subdirectories."
    )

    parser.add_argument(
        "-d", "--directory",
        type=Path,
        help="Directory to traverse for generating artifacts.",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean (erase) artifact folder",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force (re)generation of artifacts despite source status",
    )

    args = parser.parse_args()
    if args.clean:
        print(f"Removing everything under '{ARTIFACT_FOLDER}'...")
        artifact_folder = DOCS_ROOT / ARTIFACT_FOLDER
        if Path(artifact_folder).exists():
            shutil.rmtree(artifact_folder)

    else:
        batch_build_artifacts(args.directory, force=args.force)
