# Project documentation

[User documentation](../../README.md)

These documents explain implementation and maintenance. Application developers
should begin with the [quickstart](../user/quickstart.md) and [API reference](../user/api.md).

## Current implementation

- [Release operations](releases.md) — version bumps, GitHub/PyPI setup and recovery.

- [Architecture](architecture.md) — module boundaries, snapshots and rendering.
- [Development](development.md) — setup, checks, packaging and documentation maintenance.
- [Renderer extension decision](decisions/renderer-extension.md) — current extension scope.

- [YAML and schema decision](decisions/yaml-and-json-schema.md) — standard library integration and shared contracts.

- [Text substitution decision](decisions/text-substitutions.md) — Jinja display strings and shared formatting.

## Decisions and history

- [Release automation review](history/reviews/2026-11-04-release-automation.md) — implementation findings and verification.

- [Template implementation review](history/reviews/2026-11-04-template-implementation.md) — delivery, advisory findings and release checks.

- [Template implementation plan](template-implementation-plan.md) — six delivery slices with documentation and acceptance checks.
- [JSON templates and named datasets](decisions/report-templates.md) — implemented extension above the Python API.
- [Template architecture review](history/reviews/2026-11-04-template-architecture.md) — findings, scope decisions and verification.
- [Initial backend selection](decisions/backend-selection.md) — historical Chromium selection.
- [Original design](history/design.md) — reviewed baseline, superseded where current docs differ.
- [Implementation plan](history/implementation-plan.md) — completed initial stages.
- [Implementation status](history/implementation-status.md) — dated delivery record.
- [P0 comparison](history/p0-results.md) — original renderer experiment.
- [Reference inventory](history/reference-report.md) — source composition and provenance.
- [Architecture audit](history/reviews/2026-11-03-architecture-audit.md).
- [Renderer refactor and verification](history/reviews/2026-11-04-renderer-refactor.md).
- [Final renderer advisory review](history/reviews/2026-11-04-claude-refactor-final.md).
- [Documentation review and verification](history/reviews/2026-11-04-documentation.md).

Other dated [review records](history/reviews) preserve the earlier discussions.
History documents record what was decided/tested at that time; they are not the
current user API specification. No report evidence or original source PDF is published.

Language, formatting and template compatibility are described in the
[architecture](architecture.md#report-display-context) and [user contract](../user/localization.md).
User-facing release history lives in [What’s new](../../CHANGELOG.md).

- [Data loading performance](data-loading-performance.md): reproducible load/bind measurements and the 0.7.1 fix.
