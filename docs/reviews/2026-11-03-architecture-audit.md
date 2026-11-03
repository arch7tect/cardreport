# Architecture and typing audit

Status: advisory findings and proposed changes, not implemented or accepted design.
Date: 2026-11-03. Requested by the owner after inspecting public child types.

Claude reviewed the actual checkout read-only through the restricted consultation
runner (exit 0). Full response is preserved in ignored
`local/reviews/claude-architecture-typing.txt`. The primary agent independently
inspected findings and ran the checks below. No implementation files were edited.

## Verification

| Check | Observed result |
| --- | --- |
| `uv run --extra pdf pytest -q` | 43 passed in 16.35 seconds |
| `uv run ruff format --check src tests examples` | 11 files formatted |
| `uv run ruff check src tests examples` | 28 findings with installed defaults |
| `uv run mypy src/cardreport` | Pass, 7 files, existing permissive configuration |
| `uv run mypy --strict src/cardreport` | 6 errors in 5 files |
| Strict mypy caller probe with `Report().add(123)`, `Card("not a component")`, `Row("not a component")` and misspelled `row(width_mm="typo")` | Incorrectly passes because the public annotations explicitly allow Any |

The earlier completion recorded Ruff formatting, not Ruff lint. Strict mypy alone
also permits explicit Any. Runtime tests and build verification do not establish
public API typing quality. Most lint findings concern imports/style; the worker's
exception boundary should be evaluated intentionally, not mechanically removed.

## Confirmed architectural findings

- `model.py`: child/value Any annotations, string enums, and `Report.row(**layout)`
  prevent useful static rejection and hide supported keywords from the IDE.
- `html.py`: semantic validation, font checks, traversal and HTML emission are mixed.
  `charts.py` mixes chart validation and Plotly-specific serialization. The modules
  import each other through deferred imports.
- `assets/layout.js`: browser measurement, pagination and Plotly DOM inspection are
  inseparable from this renderer. Shared public components do not imply a shared
  layout engine. The Python/JavaScript payload contract needs explicit documentation.
- HTML export currently serializes an unchecked layout; opening it runs layout
  checks. PDF export waits for those checks. Preserve and document that distinction.
- One page-overflow test uses 40,000 characters and accepts ValidationError, so it
  exercises the 10,000-character cap rather than page overflow. Split validation
  and geometric overflow tests with precise expected failures.
- Invalid line `x_kind` is checked after interpretation of labels, allowing misleading
  diagnostics. JavaScript page-limit failures are generic RenderError rather than
  the intended content/layout classification.

Claude's funnel-test criticism is only partially accepted: the existing test checks
the no-silent-loss contract (readable currency label OR explicit overflow), so it is
not vacuous. Add a deterministic must-fit case to prevent excessive rejection.
Claims about WeasyPrint private box-tree feasibility remain unverified.

## Proposed direction

1. Closed recursive unions for supported components, scalar/number aliases, Literal
   options, explicit builder keywords and return types. Keep runtime validation for
   value-dependent invariants. Add positive and negative consumer typing fixtures,
   strict mypy and explicit Ruff lint/format configuration.
2. Extract semantic validation and formatting/limits from emitters, without a new
   whole-document geometry IR. Retain engine escaping and engine measurement in the
   corresponding backend. Introduce normalized chart data only where both real
   renderers need it; preserve date/time and decimal semantics deliberately.
3. A small Renderer protocol may expose render_html/report-to-string and
   render_pdf/report-to-bytes with a deadline, with Chromium as the default. Share
   publication and validation; each renderer owns chart drawing, layout, pagination
   and verification. Shared HTML fragments are appropriate only where compatible.
   Do not introduce registries, entry points, backend inheritance trees or public
   user-defined component plugins.
4. A WeasyPrint prototype must first prove strict overflow detection using the same
   model, then reproduce the reference report. Reject unsupported features explicitly;
   do not silently weaken the output contract or call an incomplete backend equivalent.
   Share behavioral tests across renderers, retaining engine-specific lifecycle tests.

Claude recommends keeping the renderer seam private until B works. The primary
recommendation differs: the owner's explicit extension requirement justifies a
small injectable renderer seam now; stabilize its public compatibility contract
after exercising B. A single chart hook cannot replace browser pagination and
measurement. No promise of a trivial WeasyPrint implementation or pixel parity.

Existing Chromium behavior, process isolation and atomic publication should stay
unchanged during typing and validation refactoring. This audit authorizes no code
changes, commit, publication or replacement of the original evidence.
