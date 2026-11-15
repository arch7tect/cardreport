"""Static image metadata and shared layout markup; pixels belong to renderers."""

from base64 import b64decode, b64encode
from html import escape
from html.parser import HTMLParser
from io import BytesIO

from PIL import Image as PillowImage
from PIL import UnidentifiedImageError

from .model import Image, RenderError, ValidationError


def image_info(data: bytes) -> tuple[str, tuple[int, int]]:
    try:
        with PillowImage.open(BytesIO(data), formats=("PNG", "JPEG")) as image:
            if image.format == "PNG" and getattr(image, "is_animated", False):
                raise ValidationError("image: animated images are not supported")
            width, height = image.size
            # PNG getexif() can decode pixels to find trailing metadata.
            # PNG uses its stored orientation; JPEG uses its EXIF orientation.
            if image.format in ("JPEG", "MPO") and image.getexif().get(274, 1) in (
                5,
                6,
                7,
                8,
            ):
                width, height = height, width
            return ("image/png" if image.format == "PNG" else "image/jpeg"), (
                width,
                height,
            )
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        PillowImage.DecompressionBombError,
    ) as exc:
        raise ValidationError(
            "image: invalid PNG/JPEG or Pillow safety limit exceeded"
        ) from exc


def data_uri(image: Image) -> str:
    return f"data:{image._media_type};base64," + b64encode(image.data).decode("ascii")


def markup(
    image: Image, path: str, definite: bool = False, *, logo: bool = False
) -> str:
    width, height = image.width_mm, image.height_mm
    if logo and width is None and height is None:
        width, height = 30, 15
    if width is not None and height is None:
        height = width * image._size[1] / image._size[0]
    elif height is not None and width is None:
        width = height * image._size[0] / image._size[1]
    w = "100%" if width is None else f"{float(width)}mm"
    h = ("100%" if definite else "auto") if height is None else f"{float(height)}mm"
    outer_h = "100%" if definite else h
    horizontal = {"left": "flex-start", "center": "center", "right": "flex-end"}[
        image.align
    ]
    vertical = {"top": "flex-start", "center": "center", "bottom": "flex-end"}[
        image.valign
    ]
    outer_w = w if logo else "100%"
    orientation = "from-image" if image._media_type == "image/jpeg" else "none"
    return (
        f'<div class="report-image" data-kind="Image" data-path="{path}" '
        f'style="width:{outer_w};height:{outer_h};justify-content:{horizontal};align-items:{vertical}">'
        f'<img src="{data_uri(image)}" alt="{escape(image.alt, quote=True)}" '
        f'data-image-path="{path}" style="width:{w};height:{h};object-position:{image.align} {image.valign};image-orientation:{orientation}" '
        f'width="{image._size[0]}" height="{image._size[1]}"></div>'
    )


def check_pixels(data: bytes, path: str) -> None:
    """Run at export time, never during component/template validation."""
    try:
        with PillowImage.open(BytesIO(data), formats=("PNG", "JPEG")) as image:
            image.load()
    except (
        OSError,
        ValueError,
        SyntaxError,
        PillowImage.DecompressionBombError,
    ) as exc:
        raise RenderError(f"{path}: image could not be decoded") from exc


def check_html_images(html: str) -> dict[str, tuple[bytes, str]]:
    """Check each embedded resource once inside the owned PDF worker."""

    class Images(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.resources: dict[str, tuple[bytes, str]] = {}

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            if tag != "img":
                return
            values = dict(attrs)
            path, uri = values.get("data-image-path"), values.get("src")
            if path and uri and uri not in self.resources:
                if not uri.startswith(
                    ("data:image/png;base64,", "data:image/jpeg;base64,")
                ):
                    raise RenderError(f"{path}: expected embedded image")
                try:
                    data = b64decode(uri.split(",", 1)[1], validate=True)
                except ValueError as exc:
                    raise RenderError(f"{path}: invalid embedded image") from exc
                check_pixels(data, path)
                self.resources[uri] = (data, uri.split(";", 1)[0].removeprefix("data:"))

    images = Images()
    images.feed(html)
    return images.resources
