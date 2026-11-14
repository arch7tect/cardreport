# Text substitution review

The implementation follows the [decision](../../decisions/text-substitutions.md).
A restricted, read-only Claude review found no blocking implementation issue.
It checked reference/filter restrictions, key-only lookup, plain-text escaping,
format defaults, timezone behavior, error locations and compatibility.

Applied review feedback: fix a Markdown table pipe; simplify static date and
currency checks; add datetime-to-date UTC, parsed newline and legacy-delimiter tests.
The owner explicitly chose existing post-render model length checks instead of a
new incremental output quota. No resource-isolation claim is made.

Validation covers six text positions, mapping-name collisions, JSON/YAML round
trips, no recursive substitution, literal Python/bound strings, invalid expressions,
nullable values, formatting, actual length limits, CLI CSV dates and both PDF
engines. Ruff, strict mypy, executable documentation and isolated core/full wheel
smokes are part of release verification. The first full run exposed a stale
schema-ID expectation. The owner requested removing that recurring maintenance:
the test now checks the canonical versioned URL shape and equality with the source
schema, without copying a release number. Data/template schema revisions remain
independent of the package version.

The separate server review confirmed delegation through the existing public APIs,
source-expression storage, sanitized error handling and original-file preservation.
It requested explicit read-only stored-template revalidation instructions, which
were added to the server's upgrade guide. No new endpoint or DB migration is needed.
