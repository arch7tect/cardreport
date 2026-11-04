Read marker: the last section of `docs/project/history/implementation-plan.md`, **Open inputs**, ends with *"These unknowns do not block writing/reviewing this plan."*

# Final review: CardReport implementation plan

## Initial corrections: all applied correctly

| Initial finding | Where it is fixed | Status |
| --- | --- | --- |
| 1. P0 had no exit if neither renderer passes | Stage table row P0; P0.2 "If neither passes…"; P0.3 Exit ("does not authorize P1") | Fixed. A no-go now closes P0 and keeps P1 blocked. |
| 2. Experiments would ship in the sdist | P0 intro (explicit sdist and wheel exclusion, inspect archive contents); P4 checks | Fixed. |
| 3. No B label-fit check after WeasyPrint | P0.2, B paragraph (collision and clipping checks in the final output, 0.5 mm tolerance, never excuses overlap) | Fixed. |
| Optional items | A-fails-early rule (P0.2), existing local container for Linux (P0.3), pytest/mypy/pypdf/pdfplumber named (P1), P3 may tighten P1 limits | Done. None of them introduce contradictions. |

## New reference-example requirement

What's sound:

- **Order of work.** The plan inventories the original in P0.1, assembles the example in P3 and runs the acceptance comparison in P4.
- **Missing original.** If the original is missing, synthetic P0 can still go ahead, but P4 is blocked unless the owner changes the requirement. That is stated the same way in P0.1, the P3 exit, P4 and Open inputs.
- **Data handling and provenance.** Provenance and a hash are recorded locally. The inventory in `docs/project/history/reference-report.md` is sanitized, and any sanitization must be approved and recorded. The attachment is not published by default.
- **Source discrepancies.** The KPI 2 vs table 3 inconsistency is preserved and flagged, never corrected. This matches design §1.
- **README and outputs.** The example is the first README example and runs offline, producing HTML and PDF. No-clobber behaviour is consistent with AGENTS.md.
- **Lookalike vs sanitized data.** "Synthetic lookalike does not satisfy" and "approved sanitized equivalents" don't contradict each other. The first means invented data; the second means data derived from the original.
- **Downstream blocking.** P5 and P6 are blocked too if the original never arrives. That follows from the strict P4 dependency and from the owner's requirement, and the owner-change escape hatch covers it.

## One remaining material blocker: the API-gap check happens too late

P4 says: *"If the source uses a chart outside the closed API, resolve the minimal needed addition/change before marking this example complete."* By P4, three things have already happened:

- P0 has picked the renderer using only synthetic fixtures.
- P1 has frozen the public model.
- P3 has finished the closed chart vocabulary.

So finding out at P4 that the original needs something unsupported would mean rework across P1–P3. It could also invalidate the renderer choice. P4 itself says API changes after that point need migration notes.

The inventory already exists at P0.1, so this is a sequencing fix, not new scope:

- **In P0.1:** map each inventoried element to the planned v0.1 components and options (chart type, orientation and labels, KPI note/format, table formats, card nesting). Send anything unsupported to the owner before the P0 decision.
- **In P0:** make sure the fixtures cover any reference composition the synthetic set doesn't already exercise.
- **If the original arrives after P1:** do the same mapping on arrival, as an explicit change-control item, before P3 starts.
- **At P4:** keep the existing sentence as a final check, not the first time the gap is found.

## Verdict

**I endorse the plan once the API-gap check moves to P0.1, with a fallback for a late-arriving original.** Everything else is sequenced realistically, consistent with `docs/project/history/design.md`, and within scope. Nothing else blocks endorsement.
