# Text substitutions

Date: 2026-11-14. Implemented in 0.9.0, retaining `cardreport.template/1`.

Daily headings should combine presentation with typed data without requiring callers
to send complete display strings. Reuse Jinja, already a core dependency, directly
in the six existing text-binding positions. A separate plain-text environment is
one configuration object per build, not a process or framework. It uses declared
one-row datasets, mapping-key lookup and a small allowed expression/filter grammar.
No user attributes, function calls, loops or calculations reach evaluation.

Default output uses the existing date/number formatter and report settings; explicit
filters return text and take precedence. Null follows the existing em dash policy.
Missing/invalid references are located errors. No date-looking string inference,
new transport, aliases map or public Python model change is introduced.

Keep existing model length/glyph limits and PDF geometry checks. Per owner decision,
there is no incremental output accounting or separate output quota. Static validation
checks literal text and expression contracts, not sample-rendered string lengths.
This is not a general-purpose sandbox or a claim of arbitrary-template resource isolation.

Existing literal Jinja delimiters in these text fields change meaning; document raw
escaping and upgrade compatibility. Table/series labels and empty text stay literal.
The server uses the library contract with no second interpreter or database migration.
See the [user contract](../../user/templates.md#text-substitutions).
