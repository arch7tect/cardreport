# Rendering comparison (not shipped)

Run from the repository root with the experiment-local uv environment:

```sh
uv sync --project experiments/rendering
uv run --project experiments/rendering playwright install chromium
uv run --project experiments/rendering python experiments/rendering/compare.py --output local/rendering-comparison/new-run
```

On the tested macOS host, WeasyPrint needed the existing native library directory
in DYLD_FALLBACK_LIBRARY_PATH (for example the output of `brew --prefix` plus `/lib`).
No system packages are installed by the script. Outputs are ignored under
local/rendering-comparison/p0. Do not rerun into a preserved evidence directory
without selecting a new output path. See [P0 results](../../docs/project/history/p0-results.md) for conclusions and
limits: this is a narrow comparison, not an alternate production renderer.

The later experimental library renderer is in [weasyprint.py](../../src/cardreport/weasyprint.py);
see the [current renderer contract](../../docs/project/decisions/renderer-extension.md) for its supported subset.
This comparison script remains the original P0 experiment.
