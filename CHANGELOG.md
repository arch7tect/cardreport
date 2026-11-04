# What's new

User-visible changes to CardReport. Installation and usage start in the
[README](README.md). Version numbers come from `pyproject.toml`.

## Unreleased

## 0.3.1 — 2026-11-04

### Fixed

- BarChart date and aware datetime categories now use report date/datetime formats
  in both renderers. Literal strings remain unchanged; equal formatted labels do
  not merge distinct categories.
- JSON bar category fields accept date/datetime within template/1. The Spanish
  reference calendar now uses a typed date and displays its Spanish date pattern.

### Renderer implementers

- For typed bar categories, use `ChartData.labels` as category keys and
  `category_labels` as display text; an empty `category_labels` retains the
  existing string-category representation.

## 0.3.0 — 2026-11-04

### Added

- Report language tags, localized empty states and application-defined empty text.
- Report-wide number separators and decimal precision, plus custom Babel LDML
  date/datetime patterns and an optional date locale override.
- The same settings in `cardreport.template/1`; existing templates remain valid.
- A Spanish report example using the reference report's datasets.
- This changelog, with version entries used as GitHub Release notes.

### Fixed

- Custom fractional-second patterns truncate exactly without float rounding.
  Unsupported Babel fields fail validation instead of displaying a missing value.
- Numeric display is isolated from application Decimal precision and traps.

### Compatibility

- Babel and langcodes are new core dependencies. Language tags have no product
  allowlist; date locale availability and font coverage are checked separately.
- Chromium PDFs are cloned through pypdf to set `/Lang` without rasterizing content.
- ReportDocument and ChartData gain trailing fields with defaults. Templates using
  the new settings require 0.3.0; older packages reject these optional keys.

- Omitting formatting keeps existing number/date output and automatic chart axes.
  Explicit formatting also controls chart labels and axes. Date axes label up to
  six actual data positions; data coordinates and values remain unchanged.
- `Table.empty_text` now defaults to `None`, inheriting the report's empty label.
  An explicit string, including an empty string, keeps its meaning.
- Language tags do not imply font coverage or automatic translation of user text.
  Chromium remains the default; the experimental WeasyPrint subset is unchanged.

## 0.2.1 — 2026-11-04

- First PyPI publication and automated GitHub/PyPI releases from main on version
  increases. Ordinary pushes run checks without publishing a new version.
- Verified distributions, checksum manifests and recovery using the original files.
- PyPI installation documentation and GitHub/PyPI version badges.

## 0.2.0 — 2026-11-04

- JSON report templates separated from named immutable datasets.
- Typed data JSON, schema-driven single-file CSV and optional pandas adapters.
- Reference JSON template/data examples and embedding documentation.
- This version was distributed as a Git tag only, without a GitHub Release or
  PyPI package.
