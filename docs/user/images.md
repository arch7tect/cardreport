# Images and logos

[Documentation home](../../README.md) · [API](api.md#image) · [Templates](templates.md)

Embed static PNG (including transparency) and JPEG images in any Row, Column,
Card or top-level block. `Report.logo` adds an image to the first-page title area,
left or right of the title/subtitle. It also works without a title. Headers do not
repeat on subsequent pages. Both PDF renderers support images; flow still requires
Chromium.

## Python

This runnable example uses the bundled, synthetic company logo. In an application,
replace `LOGO` with your file path. Database and HTTP clients can pass their bytes
to `Image.from_bytes` without saving a temporary file.

```python
from examples.images_report import LOGO
from cardreport import Card, Image, Report, Text

logo = Image.from_file(LOGO, width_mm=30, alt="ACME")
report = Report("Account statement", logo=logo, logo_position="right")
report.row(
    Image.from_bytes(LOGO.read_bytes(), width_mm=45, alt="ACME"),
    Card(Text("Prepared for the account holder")),
    widths=[1, 3],
    height_mm=30,
)
html = report.to_html()
pdf = report.to_pdf()
```

Input bytes are copied into the immutable component. Changing the original file
or bytearray later cannot change the report. Images are embedded in HTML/PDF;
renderers never fetch a URL or read a source path.

## Dimensions and alignment

| Dimensions | Behavior |
| --- | --- |
| Only `width_mm` | Derive height from the image proportions |
| Only `height_mm` | Derive width from the image proportions |
| Both | Fit within this rectangle, preserving proportions without cropping |
| Neither, ordinary block with free height | Fill the available width; derive height from proportions |
| Neither, ordinary block with definite height | Fit within available width and height |
| Neither, header logo | Fit within a 30 × 15 mm rectangle |

`align="left|center|right"` and `valign="top|center|bottom"` position the image;
defaults are left/top. `logo_position="left|right"` places the logo relative to
the title, independently of alignment inside its rectangle. For a narrow image
flush against the right edge of a wider logo rectangle, also set `align="right"`. Explicit dimensions
override the default logo rectangle. Source DPI metadata does not set print size.

Fixed-size images that exceed the allocated space raise `LayoutOverflowError`.
An automatic image in a free-height block can be taller than the page; specify
height or use a fixed-height Row to contain it. An unweighted Column has natural
height, even inside a fixed-height Row. Images and nested cards remain indivisible.

JPEG/MPO displays its first image only. JPEG EXIF orientation is honored and used to calculate proportions. PNG uses its
stored pixel orientation (EXIF rotation is ignored). `alt` is literal HTML alternate
text, not a Jinja expression; empty means decorative. This does not claim tagged
PDF accessibility. SVG and animated images are explicitly unsupported.

## JSON and YAML templates

Store image resources once in top-level `assets`. Reference the same name from
`report.logo` and image blocks. `Image.to_asset()` creates the portable resource
object, so application code never needs to encode Base64 itself.

```python
from cardreport import Image, ReportTemplate
from examples.images_report import LOGO

spec = {
    "format": "cardreport.template/1",
    "datasets": {},
    "assets": {"company": Image.from_file(LOGO).to_asset()},
    "report": {
        "title": "Account statement",
        "logo": {"asset": "company", "alt": "ACME"},
        "logo_position": "left",
        "blocks": [{
            "type": "image", "asset": "company", "width_mm": 45,
            "alt": "ACME", "align": "right",
        }],
    },
}
template = ReportTemplate.from_dict(spec)
yaml_source = template.to_yaml()
report = ReportTemplate.from_yaml(yaml_source).bind({})
```

The resource shape is `{media_type: image/png|image/jpeg, data_base64: "..."}`.
The declared media type must match the file content. No paths, URLs or data
bindings are accepted as image sources. Extra unused resources are allowed;
remove them to keep the template small. Assets belong to the immutable template
revision, not to changing report datasets. The default 1 MiB template budget
includes assets. Raise `ReportTemplate(..., max_bytes=...)` for larger images.
See [resource budgets and long reports](limits.md).

The existing `python -m cardreport render` command accepts these templates with
no additional flags. Save `template.to_json()` or `to_yaml()` and provide datasets
as usual. The server must run a library version supporting images before such a
template can be registered. A prepared template can be imported through its
ordinary JSON/YAML editor; this change does not add a browser asset editor.

## Validation and resource policy

Construction and template validation read metadata with Pillow without decoding
pixels. Pillow's standard decompression-bomb warning/error thresholds are left
unchanged; CardReport adds no pixel-count ceiling and never disables Pillow's
guard globally. Actual pixel decoding is checked during export. Corrupt pixel
streams fail with `RenderError`, rather than silently disappearing. Chromium
HTML additionally checks browser image readiness before laying out pages.

For PDF, decoding checks run in the owned renderer worker. Direct Chromium HTML
export checks pixels in the caller process; on CardReport Server that caller is
the render child, not the API's template-registration handler. Standalone Python
callers own their resource policy. Server memory remains limited per worker
container, shared by concurrent jobs; images do not introduce per-job isolation.

The complete [image example](../../examples/images_report.py) supports both
engines and a template variant:

```sh
uv run --all-extras python examples/images_report.py --output output/images-chromium
uv run --all-extras python examples/images_report.py --renderer weasyprint --template --output output/images-weasyprint
```
