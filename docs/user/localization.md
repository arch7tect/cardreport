# Language and display formats

[Documentation home](../../README.md) · [API](api.md#language-and-formatting) · [Templates](templates.md)

Language and display formats are report settings. They do not translate your data,
change Dataset values, parse localized CSV, choose a currency or select a timezone.
Dates in data JSON and CSV retain their existing ISO grammar.

## Embed a localized report

```python
from datetime import date
from decimal import Decimal
from cardreport import Card, Currency, Formatting, KPI, Report, Table, TableColumn

report = Report(
    "Resultados de llamadas",
    language="es-MX",
    formatting=Formatting(
        decimal=",",
        group=".",
        number_decimals=2,
        percent_decimals=1,
        currency_decimals=2,
        date_format="d 'de' MMMM 'de' yyyy",
    ),
)
report.row(
    Card(KPI("Importe", Decimal("1234.50"), format=Currency("EUR"))),
    Card(Table([TableColumn("day", "Fecha")], [{"day": date(2026, 11, 4)}])),
    height_mm=55,
)
html = report.to_html()
pdf = report.to_pdf()
assert "EUR 1.234,50" in html
assert "4 de noviembre de 2026" in html
```

All children inherit the report settings. The existing component `format` or
`value_format` still chooses number, integer, percent, currency or date. There are
no per-component separator, precision or locale overrides.

## Language and empty states

`language` defaults to `en`. Language tags are parsed/canonicalized by langcodes,
not restricted to a CardReport language list. For example, `es-mx` becomes `es-MX`,
and `fr-CA`, `zh-Hant-TW` and private-use tags are accepted. Tag syntax does not
promise a translation, a known date locale or font coverage. Output text is still
checked against the bundled fonts; unsupported glyphs fail validation.

Both HTML renderers set `lang`. Both PDF engines write the document `/Lang` metadata;
this alone is not a PDF accessibility or PDF/UA conformance claim.

Built-in empty table/chart labels are `No data`, `Sin datos` for Spanish and
`Нет данных` for Russian, selected by the primary language. Other languages use
`No data`. Use `Report(empty_text="...")` to supply the application's wording for
all empty tables/charts. A table's `empty_text` overrides the report; `None` inherits
and `""` intentionally renders no message. User labels and strings remain literal.

```python
from cardreport import BarChart

empty = Report(language="pt-BR", empty_text="Sem dados").add(BarChart([], []))
assert "Sem dados" in empty.to_html()
```

## Numbers

`Formatting()` retains the existing scalar defaults: comma grouping, decimal dot,
up to two number decimals, zero integer decimals, one percent decimal and two
currency decimals. `number_decimals`, `percent_decimals` and `currency_decimals`
accept integers from 0 to 6; booleans are rejected. Number trailing zeros are
trimmed; percent/currency precision is fixed. Currency codes stay explicit prefixes,
e.g. `EUR 12,50`; currency minor-unit rules and symbols are not inferred.

`decimal` is `.` or `,`. `group` is `,`, `.`, `'`, `space` (U+00A0 nonbreaking space)
or `none`. Decimal and grouping separators must differ. Scalar/value labels retain
Decimal half-even rounding, isolated from the caller’s Decimal context, and
normalize negative zero. Strings pass through
unchanged and `None` displays an em dash. Numbers themselves never change.

## Custom dates and datetimes

`date_format` and `datetime_format` accept custom [Babel LDML patterns](https://babel.pocoo.org/en/latest/dates.html#pattern-syntax),
not Python strftime or Plotly d3 patterns. Examples: `yyyy-MM-dd`, `dd/MM/yyyy`,
`d MMMM yyyy`, `yyyy-MM-dd HH:mm:ss.SSSSSS XXX`. Quoted literals use single quotes;
write two single quotes for an apostrophe. Use `y` for calendar year; `Y` is the
week-based year. There is no closed list of date layouts. Patterns are bounded to
200 characters, checked for balanced quotes and tested against the value type.
Invalid patterns and unavailable date locale data raise `ValidationError`.
Unquoted ASCII letters must be LDML fields. Unsupported Babel fields (including
single `O` in Babel 2.x) fail explicitly. Fractional-second `S` fields truncate
exactly, padding with zeros beyond six digits, without rounding into the next second.

Month/day names use `Formatting.locale` when supplied, otherwise `Report.language`.
The locale is always passed explicitly to Babel. There is no process-global locale
change and no operating-system language fallback. Unicode extensions/private-use
subtags are not Babel options; date locale lookup uses language/script/region/variants.
Locale data availability is independent of font coverage. Babel/CLDR updates can
change localized wording; pin dependencies in the application's lockfile when needed.

- A `date` uses `date_format`; with no pattern it remains ISO `YYYY-MM-DD`.
- An aware `datetime` is normalized to UTC, as before. With no patterns it retains
  the complete ISO timestamp, including seconds, microseconds and offset.
- With only `date_format`, its date portion changes and the complete ISO time and
  UTC offset follow after a space.
- With `datetime_format`, the supplied pattern determines the fields and precision
  shown. Omitted fields do not remove precision from the underlying value.
- Component `format="date"` displays only the UTC date, using `date_format`.
  Naive datetimes remain invalid. A custom pattern never changes the timezone.

```python
from datetime import datetime, timezone, timedelta

closing = datetime(2026, 11, 4, 23, 30, 45, 123456,
                   tzinfo=timezone(timedelta(hours=-2)))
time_report = Report(language="es", formatting=Formatting(date_format="dd/MM/yyyy"))
time_report.add(KPI("Cierre", closing))
assert "05/11/2026 01:30:45.123456+00:00" in time_report.to_html()
```

## Chart axes and compatibility

Omitting `formatting` (`None`) preserves automatic legacy axes, including Plotly's
compact numeric labels and automatic date wording. Explicit `Formatting()`, even
with default fields, enables controlled axis display. Numeric tick positions stay
engine-owned. Formatting sets separators and precision; float tick rounding and
minus-sign typography can differ from the exact Decimal value labels.

With explicit formatting, a LineChart date axis uses up to six actual input date
positions, sorted and sampled evenly by index with both endpoints included. Their
labels use the same date/datetime formatter as tables; the underlying coordinates
remain ISO UTC dates on a continuous date axis. Repeated formatted labels are
allowed when the chosen pattern deliberately omits distinguishing fields. The
pattern is the caller's choice; prefer a time-bearing pattern for intraday data.
Long labels still fail geometric overflow checks rather than being silently hidden
or shrunk. There is no shared tick-layout engine or JavaScript locale dependency.

BarChart accepts Python `date` and aware `datetime` categories. They use the same
report patterns as table cells; datetimes normalize to UTC. Category spacing stays
equal and input order is preserved. Different values remain separate bars even
when a pattern produces identical labels. Both renderers support typed categories
within their existing bar capabilities. Strings remain literal, including ISO
strings such as `"2026-11-04"`; they are never guessed or parsed as dates.

```python
from datetime import date
from cardreport import BarChart, Formatting, Report

report = Report(language="es", formatting=Formatting(date_format="d MMM yyyy"))
report.add(BarChart([date(2026, 11, 4), date(2026, 11, 5)], [2, 3]))
html = report.to_html()  # Axis labels: 4 nov 2026, 5 nov 2026
```

In JSON templates, declare the bar category field as `date` or `datetime` and
supply tagged values, e.g. `{"$type":"date","value":"2026-11-04"}`. This remains
`cardreport.template/1` and `cardreport.data/1`.
The WeasyPrint adapter still supports only its documented single-series bar subset;
localization does not add date axes or new chart types to that renderer.

See the [Spanish reference example](examples.md#spanish-reference-report) for
separate JSON presentation/data files and both PDF engines.
