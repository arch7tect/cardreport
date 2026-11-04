# Typed bar date categories

Date: 2026-11-04. Version: 0.3.1.

The Spanish calendar supplied an ISO string, so the report date pattern could not
apply. BarChart now accepts strings, dates and aware datetimes. Template/1 bar
category fields accept non-null text/date/datetime, and the Spanish data fixture
uses a tagged date. Literal strings remain literal; Funnel and Line contracts stay
unchanged.

Typed bars normalize to positional category keys and separate formatted display
labels. Both adapters retain distinct bars for equal display labels. Duplicate
source categories are checked by kind and canonical value, with datetimes in UTC.
A date, midnight datetime and literal ISO string are distinct categories.
The provisional renderer snapshot adds trailing default-empty category_labels;
third-party adapters must consume it when present. No geometry framework is added.

## Advisory review

A restricted Claude source review completed successfully and found no blocker.
It had read-only tools and reviewed current files, not a git diff; tests were run
separately. Accepted suggestions: document the extension field in the changelog,
add formatted-category overflow/length checks, mixed date/datetime identity and
literal escaping coverage, and verify default ISO display in both engines.
The existing rejection test for date bar categories was updated to reject numeric
category fields, consistent with the expanded contract.

The observation about numeric SVG ticks lacking a language argument does not
require a change: numeric display is explicitly separator-driven, and date value
formats remain prohibited. Locale month abbreviations remain dependent on Babel
data, covered by the locked development environment.

## Acceptance

Verification targets the full macOS/Python 3.12 suite with both engines, strict
mypy, Ruff, executable documentation/link checks and isolated installed-wheel
checks. Both rebuilt Spanish reference PDFs were visually inspected: the calendar
axis and report-date KPI show `4 de noviembre de 2026`. Duplicate displayed dates
remain visible in horizontal and vertical PDF charts in both engines. Excessive
labels fail rather than shrink or disappear. Original English fixtures are intact.

Publication is performed and verified separately through the main release workflow.
Raw review logs, test results and generated reports remain ignored local artifacts.
See [API](../../../user/api.md#barchart), [display settings](../../../user/localization.md)
and [release notes](../../../../CHANGELOG.md).
