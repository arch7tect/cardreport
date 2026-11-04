# Documentation restructure: review and verification

Date: 2026-11-04. Scope: documentation, example typing and verification tooling;
no library runtime behavior changes. The owner authorized restructuring, Claude
review, example/link verification and a push to the existing public repository.

## Result

[README](../../../../README.md) is the user entry. The user docs separate a Python
embedding quickstart, API reference, layout guide, renderer setup/capabilities,
complete examples and secondary command-line runners. The original dashboard is
the first complete usage example. Current architecture/development documentation
is separate from preserved historical design, plans and advisory reviews.

The new import-safe `examples/quickstart.py` accepts application data and returns
a Report. Strict typing now covers all examples and the documentation checker.
Historical documents were moved with their contents retained and links rebased.

## Advisory review and disposition

Two restricted read-only Claude consultations completed successfully (exit 0).
The first found no blockers but requested three small corrections:

- Count all nested components, including containers and PageBreaks, toward the
  500-component limit; clarify the report-wide table-cell limit.
- State that executing all documentation examples requires both renderers and
  native WeasyPrint dependencies; provide a links-only check.
- Remove the local CodexHome maintenance requirement for outside contributors.

All were applied. Additional corrections document constructor errors and writable
Report attributes, explicit rejection of landscape orientation for custom sizes,
and how to test custom renderers through Report exports. Guide and renderer
snippets have their own imports. uv remains the documented installation tool.

Execution found a natural-height KPI card rejected by the experimental WeasyPrint
geometry check. The renderer examples now give the card an explicit 50 mm row
height and document the limitation; the runtime implementation is unchanged.

The focused final review confirmed all essential findings resolved and found no
remaining blockers or factual errors within README/user-doc scope. This is advisory
source review, not an independent execution claim. Raw review outputs stay local.

## Executed verification

On macOS/Python 3.12, with native libraries configured:

- All 29 Python blocks in README and six user pages executed successfully.
  PDF-producing blocks returned PDF bytes; file writes used temporary directories.
- Local Markdown targets and heading anchors passed, including moved history.
  Eight external documentation URLs and the GitHub repository returned HTTP 200;
  referenced remote HTML anchors were checked too.
- Quickstart, reference (Chromium and WeasyPrint) and flow runners completed;
  documented argument parsers were checked with `--help`.
- Git-revision, editable-checkout and wheel installation commands worked in fresh
  environments outside the repository, followed by HTML and PDF exports.
- Runtime suite: 80 passed, no skips. Strict mypy: 20 files. Ruff lint and format:
  23 files. Wheel and source archive built successfully; bundled assets, new docs
  and source/evidence exclusions were inspected.

The [development guide](../../development.md) documents repeatable checks.
The offline checker inventories external links but does not claim to verify their
availability; the network verification above was separate. No hosted CI, PyPI
publication or new cross-platform support claim was added.
