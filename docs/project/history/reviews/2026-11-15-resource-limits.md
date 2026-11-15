# Configurable limits review

The owner authorized configurable library/server budgets and release together with
static images, followed by a local Compose update. Restricted Claude design and
implementation consultations read both real repositories and exited successfully.

Accepted findings: preserve accepted server budgets; decouple schema structure
from runtime size policy; retain recursion guards; bound YAML alias expansion by
actual source bytes; defer sample table-size policy to real binding; carry input
budgets into file diagnostics; retain independent preview memory budgets and raw
download access. Server exact-boundary storage tests verified canonical PostgreSQL
JSON; a follow-up concern based on superseded migration 0002 JSONB did not apply
after migration 0003. No per-job memory isolation is claimed.

The image feature has its [separate verification record](2026-11-15-images.md).
Full release checks and the public artifact identities are recorded after validation.

Final local checks: 746 tests passed with zero skips, Ruff and strict mypy passed,
57 executable Python documentation blocks and 408 local links passed. Both renderers
passed image and page-budget regressions; Chromium flow preserved the final row of
a 2101-row table. JSON/YAML transport handled more than the former 500000 tree-node
ceiling. Fresh installed-wheel core/full-extra smoke and strict Twine checks passed.
The release workflow repeats the complete checks before publishing 0.10.0.
