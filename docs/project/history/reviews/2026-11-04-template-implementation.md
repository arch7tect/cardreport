# Template and dataset implementation review

Date: 2026-11-04. Target: CardReport 0.2.0, additive extension above the existing
Python components/renderers. The owner authorized implementation, Claude checkpoints
and publication to the existing public GitHub repository. No PyPI release.

## Delivered scope

The [six-slice plan](../../template-implementation-plan.md) delivers immutable
Dataset/schema/limits, lossless typed data JSON, closed ReportTemplate presentation
and binding to ordinary Report, a single-file CSV adapter and optional pandas.
Native SQL results are caller-owned. SQL query execution, CSV-directory loading,
YAML, JSON Schema, expressions and provider registries remain deferred.

The original report now has separate presentation and data fixtures, a second data
fixture and an import-safe Python runner. Its normalized model equals the existing
independent Python reference. README, quickstart, API, template/data guides, examples,
renderer/CLI guides and project architecture/development documents were updated.

## Advisory reviews and disposition

Two restricted read-only Claude Code reviews completed with exit 0. They were
advisory source inspections, not independent executions of tests or packaging.

The first checkpoint covered native datasets, transport, template parsing/binding,
types and associated documentation/tests. Confirmed findings were resolved:

- Require ordered row sequences; reject mappings, sets, bytearrays and iterators
  passed as records. Separate mapping rows use from_dicts; its empty-input sentinel
  no longer masks an invalid first None row.
- Map semantic errors through known component paths instead of the last visited node;
  include report settings and preserve dataset/row/field locations through decoding
  and lowered-limit binding checks. Unknown suffixes remain unset.
- Reject datetimes outside the representable UTC range and invalid timezone offsets.
- Normalize native Mapping objects before compact JSON serialization; avoid whitespace
  expansion when applying template size limits.
- Verify exact transported scalar types, Decimal scale and datetime offsets in tests.

The final review rechecked those fixes and reviewed adapters, examples, error/type
contracts and user documentation. It found no high-severity blocker and one required
small fix: reject lone Unicode surrogates in dataset/column names before encoding.
That shared-name validation is implemented and covered at native/schema/JSON ingress
and JSON egress. The reviewer concluded no remaining blocking issue conditional on
that fix. The implementation agent verified the fix; no additional advisory call
is represented as having occurred.

Optional improvements accepted: report the missing CSV column, document pandas
nullable Int64, and add a missing-pandas dependency regression. Optional finer paths
for numeric/format settings remain deferred: the current contract permits an unknown
location and never fabricates one. No renderer/component contract changed.

## Verification

Final acceptance: **155 tests passed** (both engines and pandas, no skips), strict
mypy passed for **27 files**, Ruff lint/format passed for **34 files**, and **36 Python
documentation blocks** passed across README and eight user guides. The published
JSON fixtures bind successfully, local Markdown links/anchors pass, and
`uv sync --all-extras --locked` succeeds. Wheel and source distribution build successfully.
The initial baseline was 80 passing tests. Verification covers both PDF engines,
original/second-data reuse, explicit pages, Chromium flow, empty charts and oversized
content rejection, plus the unchanged legacy contracts.

Both original PDFs were rendered from a freshly installed wheel and visually
inspected. Card positions, text, table and chart bounds fit; the two engines retain
their documented axis/typography differences. The output is one page with selectable
text and no raster images. The original source discrepancy is intentionally retained.

Fresh isolated wheel checks outside the source tree verified core-only JSON/CSV/
binding/HTML without pandas, NumPy or PDF packages; missing pandas produces the
explicit DependencyError. A separate full-extra environment verified pandas 3.1.0
and both renderer exports. The wheel/source archive include new modules, py.typed,
fonts/licenses/assets and distributable JSON/CSV examples; private source PDFs,
local evidence, generated output, IDE state and experiments are excluded.

Review limits: Claude did not run commands, verify packaging or review the unchanged
renderers in full. Runtime evidence is from local macOS/Python 3.12; no Linux/Windows,
pandas 2.2 execution or hosted CI claim is made. External links are inventoried by
the offline checker; the published GitHub ref is verified separately after pushing.
