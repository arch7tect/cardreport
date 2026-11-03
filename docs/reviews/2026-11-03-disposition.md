# Design review disposition

Date: 2026-11-03. Three successful read-only Claude CLI consultations, exit 0.
Raw responses remain in ignored local/reviews; document copies omit unrelated
connector diagnostics. No reviewer modified files or ran commands.

## Initial design review

Source: [initial review](2026-11-03-claude-initial.md).
Claude endorsed the initial structure with four required design corrections.
Verified and incorporated:

- Nested example: 90 mm minus a 4 mm gap, divided [3,1], allocated only 21.5 mm
  to a 28 mm minimum KPI. Corrected to 100 mm and [2,1], giving 32 mm.
- Explicit layout authority; Python static validation vs browser measurement for A.
- Containment grammar, top-aligned unweighted columns and unsupported flow mode.
- Chart-label wrapping/overlap, fixed sizes, explicit category ticks, literal
  markup/math behavior and HTML-safe serialization for A.
- Currency format API and rounding; font load before chart creation; preview scope;
  PDF parser/test dependency planning. Fixed the "no network" typo.

The claimed missing reviews directory was not confirmed: it existed before the
call, but had no files yet. It now contains the review records. No change was
needed beyond completing these records. Optional new API features were deferred.

## Backend correction

Source: [backend review](2026-11-03-claude-backends.md).
The user reopened the renderer choice during review. Claude recommends testing
browser-free SVG/WeasyPrint first. See [backend decision](../backend-decision.md)
for accepted advice, qualifications and untested claims. The recommendation to
write custom chart/layout code is not automatically accepted. No final backend
endorsement is implied by the initial baseline review.

## Verification scope

Package environment, import, wheel and source build are checked separately.
No PDF renderer, visual equivalence, platform installation matrix or performance
has been validated. This is a reviewed design scaffold, not a working report engine.

## Final reconciliation

[Final Claude review](2026-11-03-claude-final.md) endorses the revised design-stage
baseline with no material contradictions or blockers. Backend selection remains
pending the comparative experiment. The suggested explicit candidate-A tag on
browser pagination has been added. No benchmark or production-engine selection
is implied by this endorsement.
