import argparse
import contextlib
import importlib
import hashlib
import json
import sys
import shutil

from collections.abc import Iterable
from pathlib import Path
from warnings import warn

from tcv_screenshots import get_saved_models
from tools.camera import get_view_coords, camera_projection
from tools.process_image import batch_screenshots, batch_thumbnails


DOCS_ROOT = Path(__file__).parent
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


def localize_path(path: Path) -> Path:
    if path.is_absolute():
        result = path
    else:
        result = DOCS_ROOT / path

    return result.resolve()


def build_artifacts(config: dict, destination: Path, *, force=False):
    """Generate and copy build artifacts as defined by an asset config into destination

    Sources are checked for changes by hash and skipped if no changes.
    The artifact destination is set to the cwd as a destination for in process artifact generation
    and sources are temporarily added to path.

    If the config has `save_models`, that method is run to add screenshot models to global list.
    Likewise, all `to_generate` items are imported to add any screenshot models to global list and
    generate any assets to artifact destination. These imports are expected to run all required asset
    creation outside of methods and class definitions.
    """
    empty_config = {
        "sources": [],
        "destination": None,
        "resources": [],
        "build": [],
        "thumbnails": [],
        "exceptions": [],
    }
    config = {**empty_config, **config}
    folder = config["label"]

    if config["destination"]:
        destination = localize_path(Path(config["destination"])) / folder
    else:
        destination = destination / folder

    destination.mkdir(parents=True, exist_ok=True)


    with contextlib.chdir(destination):
        # Import asset config
        sources = {localize_path(Path(source)) for source in config["sources"]}

        # Check for changes to sources
        new_hash = hash_folders(sources)
        stamp = destination / ".asset-stamp"
        if stamp.exists() and not force:
            old = json.loads(stamp.read_text())
            if old["input_hash"] == new_hash:
                print(f"===== {folder}: No Change =====")
                return

        print(f"===== {folder}: Building Assets =====")

        # Copy assets used in build process
        if config["resources"]:
            copy_assets(config["resources"], sources, destination)

        with add_to_syspath(sources):
            # Save models and generate artifacts
            for module in config["build"]:
                importlib.import_module(module)

        if saved_models := get_saved_models():
            saved_models = [
                (obj, label, {**DEFAULT_MODEL_CONFIG, **model_config})
                for obj, label, model_config in saved_models
            ]
            generate_screenshots(
                saved_models, destination, config["exceptions"], config["thumbnails"]
            )

    # Check contents of _static and write stamp
    if any(destination.iterdir()):
        stamp.write_text(
            json.dumps(
                {
                    "input_hash": new_hash,
                }
            )
        )


def iter_assets(sources: Iterable[Path], exts: set[str]):
    """Find all assets in extensions list in sources"""
    exts = {e.lower().lstrip(".") for e in exts}

    for source in sources:
        source = Path(source)
        for p in source.rglob("*"):
            if p.is_file() and p.suffix.lower().lstrip(".") in exts:
                yield p


def copy_assets(asset_paths: Iterable, sources: Iterable, destination: Path):
    """Copy assets to artifact destination

    Naively looks for assets in sources
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    for asset_path in asset_paths:
        for source in sources:
            asset_source = source / Path(asset_path)
            asset_dest = destination / asset_source.name
            try:
                shutil.copy2(asset_source, asset_dest)
                break
            except FileNotFoundError:
                warn(f"{asset_path} not found in {source}")


def generate_screenshots(
    models: list[tuple],
    destination: Path,
    exceptions: dict | None,
    thumbnails: list | None,
):
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

    print(f"===== Processing {len(models_to_process)} Screenshots =====")

    processed_models = []
    for cad_object, output_name, example_config in models_to_process:
        # Merge defaults with example overrides
        if "reset_camera" in example_config:
            view = get_view_coords(example_config["reset_camera"])

            if view:
                camera = camera_projection(cad_object, **view)
                example_config.update(camera)
                example_config.pop("reset_camera")

        config = {**TCV_DEFAULT_CONFIG, **(example_config or {})}

        # Export model to JSON string
        model_json = export_three_cad_viewer_js(None, cad_object)
        model_data = json.loads(model_json)

        # Create combined data with model and config
        combined_data = {"model": model_data, "config": config}

        processed_models.append((output_name, combined_data))

    return processed_models


def batch_build_artifacts(
    config_path: str | Path,
    destination: str | Path,
    *,
    labels: list = None,
    force: bool = False,
):
    """Build artifact from config list (json) into destination path.

    Optionally
        - Specify specific configs to build by labels
        - Force rebuild of unchanged asset sources
    """
    config_path = localize_path(Path(config_path))
    destination = localize_path(Path(destination))
    if config_path.exists():
        destination.mkdir(parents=True, exist_ok=True)

        with open(config_path, "r", encoding="utf-8") as f:
            configs = json.load(f)

        if labels:
            configs = [c for c in configs if c["label"] in labels]

            if not configs:
                raise ValueError(f"No labels {labels} found")

        for config in configs:
            build_artifacts(config, destination, force=force)

    else:
        raise FileNotFoundError(f"Could not find {config}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="build_artifacts",
        description="Build screenshots, svgs, and other documentation assets from a config",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default="asset_conf.json",
        help="Artifact build config (json)",
    )

    parser.add_argument(
        "-d",
        "--destination",
        type=Path,
        default="_build/assets",
        help="Build destination directory",
    )

    parser.add_argument(
        "-l",
        "--label",
        help="Label to build from config",
    )

    parser.add_argument(
        "-s",
        "--script",
        help="Script to run",
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
        clean_destination = localize_path(args.destination)
        print(f"Removing everything under '{clean_destination}'...")
        if Path(clean_destination).exists():
            shutil.rmtree(clean_destination)
    elif args.script:
        print(f"Building artifacts from '{args.script}' to '{args.destination}'...")
        script = Path(args.script)
        script_config = {
            "label": script.stem,
            "sources": [script.parent],
            "build": [script.stem],
        }
        build_artifacts(script_config, args.destination, force=args.force)
    else:
        label = [args.label] if args.label else None
        print(f"Building artifacts from '{args.config}' to '{args.destination}'...")
        batch_build_artifacts(args.config, args.destination, labels=label, force=args.force)
