from pathlib import Path
from PIL import Image


def crop_to_content(image: Image):
    """Crop image to non-background content, assuming transparent background"""
    bbox = image.getbbox()
    if bbox:
        cropped = image.crop(bbox)
    else:
        raise RuntimeError("Image is entirely transparent.")

    return cropped


def resize_to_height(image: Image, new_height: int):
    "Resize image to new height."
    width, height = image.size
    if height <= new_height:
        new_height = height
        new_width = width
    else:
        height_ratio = new_height / height
        new_width = int(width * height_ratio)

    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def process_screenshot(
        filepath: str | Path,
        height: int = 300,
        margin: int = 0,
        background: float | tuple[float, ...] | str | None = (0, 0, 0, 0)
    ):
    """Crop screenshot to non-transparent objects, resize non-transparent objects,
    apply margin, update background. Saves to png.

    Args:
        filepath (str): path to image to process
        new_height (int): final image height
        margin (int): image margin around objects
        background (float, tuple, str, None): RGBA color representation
    """

    filepath = Path(filepath)
    content_height = height - 2 * margin

    with Image.open(filepath) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        cropped = crop_to_content(image)
        resized = resize_to_height(cropped, content_height)

        # Apply margin and background change
        resize_width, resizeheight = resized.size
        width = resize_width + margin * 2
        height = resizeheight + margin * 2

        x_offset = (width - resize_width) // 2
        y_offset = (height - resizeheight) // 2

        expanded_image = Image.new("RGBA", (width, height), background)
        expanded_image.paste(resized, (x_offset, y_offset))

        expanded_image.save(filepath)


def make_thumbnail(
        filepath: str | Path,
        label: str | None = None,
        size: int = 250,
        crop: bool = False,
        push: str | None = None,
        shift: tuple[float] = (0, 0)
    ):
    """Make square thumbnail with given name and height. File saved as "thumb_{name}.png

    Args:
        source (str): source image for thumbnail
        label (str): name to give thumbnail, no need to include "thumb" or file extension
        size (int): final image height
        crop (bool): crop width to fill height. False shrinks foreground height to fit width
        push (str): push foreground to edge ("top", "bottom, "left", "right")
        shift (tuple[float]): amount to shift image along x and y in pixels
    """

    filepath = Path(filepath)
    if not filepath.exists():
        print(f"{filepath} doesn't exist, skipping.")
        return

    folder = filepath.parent

    if not label:
        label = filepath.name

    thumb_name = (
        "thumb_"
        + Path(label).stem.replace("thumb_", "")
        + ".png"
    )
    thumb_path = folder / thumb_name

    with Image.open(filepath) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        cropped = crop_to_content(image)
        width, height = cropped.size
        resize_height = int(height / (height / width)) if not crop and width > height else height

        # Shift Image
        shift_x, shift_y = shift
        x_offset = (resize_height - width) // 2 + shift_x
        y_offset = (resize_height - height) // 2 + shift_y

        if push:
            if "left" in push:
                x_offset = 0
            elif "right" in push:
                x_offset = resize_height - width
            if "top" in push:
                y_offset = 0
            elif "bottom" in push:
                y_offset = resize_height - height

        x_offset += shift_x
        y_offset += shift_y

        shifted = Image.new("RGBA", (resize_height, resize_height))
        shifted.paste(cropped, (x_offset, y_offset))

        # Crop image to thumbnail
        resized = resize_to_height(shifted, size)
        resized.save(thumb_path)


def batch_screenshots(folder: str | Path, exceptions: dict | None = None, height: int = 300, margin = 0, background: float | tuple[float, ...] | str | None = None):
    """Batch process screenshots in folder. 
    
    exceptions is a dict with image paths as keys and dicts of "new_height" and "margin" parameters 
        to override
    """

    folder = Path(folder)
    exceptions = exceptions or {}

    for path in folder.glob("*.png"):
        if path in exceptions:
            process_screenshot(path, **exceptions[path])
        else:
            process_screenshot(path, height=height, margin=margin)


def batch_thumbnails(folder: str | Path, to_thumbnail: list[dict], size: int = 250):
    """Batch create thumbnails from list.
    
    to_thumbnail is a list of dicts with required keys "source", "label" and optional 
        "size" and "shift".
    """
    folder = Path(folder)

    for thumbnail in to_thumbnail:
        thumbnail.setdefault("size", size)
        thumbnail["filepath"] = folder / thumbnail["source"]
        thumbnail.pop("source")
        make_thumbnail(**thumbnail)
