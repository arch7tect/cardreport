# Implementation-plan review disposition

Date: 2026-11-03. Scope: documentation only; no implementation or experiment run.

## Initial review

[Claude initial plan review](2026-11-03-claude-plan-initial.md) completed with exit 0
and endorsed the sequence conditionally on two corrections. All three material
findings were accepted after inspection of the plan and packaging configuration:

1. P0 completion now includes an evidence-backed no-go when neither candidate
   passes. P1 stays blocked on resolving the contract conflict; failure is not a
   forced selection of A.
2. Experiment sdist exclusion and archive inspection are explicit work items.
   Current Hatch configuration has no custom exclusion; implementation must add
   it when experiment files are introduced. No experiment exists yet to test.
3. Final WeasyPrint chart-label collision and position checks mirror A's fit
   checks. Font identity alone cannot establish final geometry.

Optional clarity accepted: named development tools, measured chart limits may
be tightened before the dashboard milestone, an available local container may
supply Linux evidence, and early-failure stopping is symmetric between A and B.
These are future tasks, not claims of tested behavior.

## Owner's reference-report requirement

The owner explicitly requested the original report as the first usage example.
The plan now requires source provenance/inventory in P0, public-API assembly in
P3, and full reference comparison in P4. README must present it first. Missing
source blocks example acceptance, not unrelated synthetic experiments. Approved
sanitized data must be labelled; inconsistencies must not be silently repaired.

## Final review

[Final Claude review](2026-11-03-claude-plan-final.md) completed with exit 0 and
endorsed the plan conditional on moving reference-to-API gap detection earlier.
That correction is incorporated: P0 maps the original before final renderer
selection and expands fixtures for uncovered compositions. A synthetic-only
recommendation is provisional. If the source arrives after P1, revisit affected
contracts before P3; P3 now requires that mapping. An unavailable original blocks
P3 completion/start under the full plan until supplied or the owner changes scope.
P4 retains a final regression check, not first discovery of missing chart support.
The applied correction was checked directly against stage dependencies and exit
criteria. Both plan reviews are retained; this is conditional reviewer endorsement
with its stated condition fulfilled, not runtime verification.

## Verification scope

Local document links, neutral-path hygiene and whitespace checked. CodexHome wiki
lint passed with unrelated existing expiry warnings. No runtime tests were run
for this documentation-only change, and no implementation or publication occurred.
