# Language, formatting and release notes

Date: 2026-11-04. Version: 0.3.0.
This record describes local acceptance before the release push. Hosted publication
is verified separately in GitHub Actions and the package registry.

## Delivered scope

Report language tags (without a product allowlist), immutable Formatting, custom
Babel LDML dates/datetimes, report-wide numeric separators and precision, and empty
text inheritance. HTML/PDF language metadata works in both engines. The original
reference remains unchanged; the additional example is Spanish only and reuses
its aggregate values, including the original KPI/table discrepancy.

The owner explicitly kept `cardreport.template/1`: optional display settings extend
its grammar before external adoption. Existing templates/data remain valid; old
package versions cannot read the new keys. `cardreport.data/1` is unchanged.

Root CHANGELOG.md is linked from README and supplies the exact version body for
new GitHub Releases. Version notes are checked before reserving a tag and read from
the exact commit. Published notes/assets are never replaced by the automation.

## Advisory review and disposition

Restricted Claude source consultations covered the revised design, implementation
and focused fixes. These reviews are advisory; command evidence is separate.
The focused follow-up found no remaining release blocker. Its two small additional
findings were also fixed: extended-year `uu` retains the year, and NUL/control
characters cannot be interpreted as quote escapes.
The implementation review identified two reproducible Babel 2.18 defects:

- `O` emitted literal `None`. Missing field output now raises ValidationError.
- `ss.SSS` on 999600 microseconds emitted `45.1000`. A small private adapter uses
  Babel tokenization/field formatting, with exact integer truncation/padding for S.

Regressions exercise boundaries and more than 1000 fractional-second values.
Runtime locale errors are converted to located validation errors, quote/field
syntax is checked, naive datetime calls are rejected, and numeric output uses a
local Decimal context. Datetime axes with UTC offsets are verified in a real PDF.
Template error paths distinguish inherited report language from explicit locale.

Owner-directed choices override earlier proposals: no language allowlist, no fixed
list of date layouts, no template/2, and only a Spanish user-facing example. Date
locale defaults to the explicit report language; it never falls back to the OS.
Caller-chosen patterns may repeat labels or omit precision. Native numeric tick
rounding/minus glyphs are not claimed identical to Decimal data labels. Those
limits and the unchanged experimental renderer capabilities are documented.

## Verification scope

Local verification covers macOS/Python 3.12, both renderers and optional pandas.
The final acceptance targets are 228 tests without skips, strict mypy over 32 files,
41 executable documentation blocks and 233 local links.
It includes Ruff, strict mypy, the full runtime suite with no skipped tests,
executable user documentation and Markdown navigation, wheel/sdist metadata/assets,
Twine, and fresh core-only/full installed-wheel smoke outside the checkout.
Spanish PDFs from both engines were visually inspected for layout and glyphs.
No Linux/Windows PDF support or PDF/UA conformance is claimed.

Raw command/reviewer logs and generated reports stay in ignored local/output paths.
See [language and formats](../../../user/localization.md),
[What's new](../../../../CHANGELOG.md) and [release operations](../../releases.md).
