# Static report images

Status: implemented locally, not released. Owner approval: 2026-11-15.

Images are ordinary immutable components, with from_file and from_bytes helpers.
PNG/JPEG metadata is inspected using Pillow; its standard decompression-bomb
protection remains unchanged. No custom pixel cap, URL fetcher or image registry
is introduced. Full decoding checks happen at export, not during template loading.
PDF checks run in the owned renderer process; direct Chromium HTML checks run in
the caller. The native WeasyPrint fetcher admits only exact embedded image/font
URIs. Both renderers reject missing/undecodable images instead of silently omitting
them. PNG uses stored orientation to avoid decoding just to find trailing EXIF;
JPEG EXIF is read from metadata and applied by both engines.

Ordinary components auto-size within their available box when dimensions are
omitted. Explicit dimensions are fixed; two dimensions define a contain box.
The standard first-page header has an optional Image logo and left/right position.
Its dimension-free default is 30 by 15 mm, independent of title measurements.
No repeated-header or general header/footer framework is added.

Template assets are named embedded media_type/data_base64 resources. The media
type must match the content; names are not paths. Image.to_asset() supports
programmatic authoring. Unused assets are permitted within the existing template
byte budget. Library API and existing JSON/YAML CLI support are part of this slice;
a browser asset editor and server dependency release are separate delivery work.
No template envelope version or database migration is required.

The owner explicitly retained Pillow protection. Existing table/page/data limits
are not removed here. Raising those requires a separate end-to-end change covering
normalized snapshots and API data views. Existing container memory limits do not
provide per-job memory isolation; no such guarantee is added by image support.

See [user documentation](../../user/images.md) for the public contract. The review
from 2026-11-14 motivated these boundaries; implementation verification is recorded
in the current task and the dated review record after completion.
