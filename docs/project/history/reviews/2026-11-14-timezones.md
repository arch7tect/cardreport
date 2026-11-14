# Timezone hotfix review

Owner requested the agreed date/timestamp matrix, a `datetime` filter, library and
server hotfix releases, tests/docs and a local Compose upgrade. Compatibility was
explicitly waived; this is the authorized 0.9.1 patch exception to normal feature
versioning. See the [decision](../../decisions/timezones.md).

Restricted Claude design and implementation reviews completed successfully with
read-only source access. Confirmed findings were addressed: naive inputs attach
UTC before any conversion; offset parsing only checks a present suffix; date-only
formatting retains an IANA datetime's offset; invalid/host-dependent zone names
fail; date-axis labels use one formatter in both engines, independently of numeric
formatting. A narrow follow-up reviewed chart padding, documentation and new tests.

The installed-wheel smoke found a real first-date/numeric-axis label intersection
in the existing multi-series example. A small font-relative, integer tick standoff
resolves it without disabling geometry checks. Full ISO datetime labels can still
be too wide in narrow charts; tests pin checked Chromium success and explicit SVG
label overflow for one such layout. Authors can choose a shorter datetime pattern.

Unrelated existing behavior for mixed pure-date/datetime line categories is not
changed. Report-zone changes never alter stored instants or retention timestamps.
Server lock refresh and publication must follow the public library release.

Verification covers the nine timestamp cases, date invariance, midnight and DST,
naive and aware data through Python/JSON/YAML/CSV/pandas, schema identity, both PDF
engines, Jinja type/pattern/null errors, invalid zones and date-axis geometry.
Previous UTC/naive-rejection assertions were updated to the new public contract.

Final local verification: 679 tests passed without skips; strict mypy (49 files),
Ruff lint/format (72 files), 54 executable documentation blocks and 382 local links
passed. Wheel/sdist metadata and fresh core/full installed-wheel checks passed,
including both PDF engines. Daily and multi-series PDFs were generated through
both engines; the new local-time note and repaired date axis were visually checked.
The final restricted follow-up exited successfully with no remaining blocker.
