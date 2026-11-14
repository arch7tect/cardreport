# Datetime display timezones

Date: 2026-11-14. Owner-approved hotfix 0.9.1; no new template/data envelope.

Mandatory UTC display could change a report author's calendar day near midnight.
Preserve the supplied offset by default, and provide one optional report-level
IANA `timezone` for a common display clock. Interpret datetimes without offsets
as UTC at ingestion and in the direct Python model. The display zone never supplies
an implicit input zone. Calendar dates have neither time nor timezone and never shift.
The public [matrix and examples](../../user/localization.md#timezones) define the contract.

The existing formatter performs conversion before date extraction, including Jinja
`date` and the new `datetime` filter. ReportDocument carries the zone; shared markup
and chart normalization use that context. Both chart adapters consume the same
preformatted labels. Continuous-axis positions and duplicate/order checks remain
canonical instants, including repeated wall times during daylight-saving changes.
Chromium always uses the sampled input-date ticks, including without Formatting.
No backend locale, machine timezone, alternate expression language or date parser
is introduced. Numeric axes retain their existing defaults.

Use standard-library ZoneInfo and an unconditional tzdata fallback. Zone names are
case-sensitive and checked against available IANA names; host-dependent pseudo-zones
are rejected. System tz rules retain standard ZoneInfo precedence. Dataset snapshots
keep fixed offsets, not named-zone identity. JSON Schema permits an omitted timestamp
offset; normal serialization writes the resulting UTC offset explicitly. Original
server uploads remain byte-identical. No server endpoint or database change is needed.

Compatibility was explicitly waived for this hotfix. Authors requiring previous UTC
output can set `timezone: UTC`; existing immutable server templates are not rewritten.
