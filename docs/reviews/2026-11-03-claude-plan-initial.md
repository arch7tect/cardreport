Read marker: in `docs/implementation-plan.md`, under **P0.2 — attempt B, then construct the A baseline**, the passage ends with *"Kaleido/Plotly static export is not a browser-free alternative."*

# Review of the CardReport implementation plan

## Overall

The order makes sense. P0 compares the two renderers. P1 freezes the model. P2 is the first working slice. P3 adds charts. P4 delivers dashboards, P5 adds flow reports, and P6 gets the release ready. Each stage builds only on the one before it, so there are no circular dependencies. The plan matches the design's scope and adds no new features. It keeps one production renderer and refuses a backend framework. It treats B's custom geometry and line-breaking as a recorded cost, not something assumed to be simple. The acceptance criteria are realistic for a planning stage. The plan also leaves room for "neither renderer passes" and for platforms that haven't been tested.

## Gaps worth fixing (material, small)

1. **P0 has no exit if neither renderer passes.** The stage table's completion condition is "A viable single renderer identified." But P0.2 also allows "If neither passes, report the precise contract conflict." As written, that second outcome can never complete P0.
   *Fix:* change the table cell to "One renderer recommended with evidence, **or** a documented contract conflict escalated to the owner; limitations explicit."

2. **The experiments would end up in the source distribution.** `pyproject.toml` uses Hatchling, and Hatchling's sdist includes every file not listed in `.gitignore`. That means `experiments/rendering/`, with its own `pyproject.toml` and lockfile, would ship in the sdist. This contradicts "Experimental alternatives remain outside the shipped package."
   *Fix:* in P0, add one sentence saying the sdist must exclude `experiments/` (for example with a Hatch sdist `exclude`). In P4's packaging checks, add "inspect sdist contents" next to the clean-wheel install check.

3. **B's chart-label fit check isn't as specific as A's.** For A, the plan says "test measured fit and label density." For B, Matplotlib positions labels using its own text measurements, but WeasyPrint/Pango draws the final text. The decision doc already notes that one bundled font doesn't guarantee matching metrics across the two. Without a matching check, B could pass P0 while its chart labels clip or overlap.
   *Fix:* in P0.2's B paragraph, add "verify that chart text placed by Matplotlib does not overflow or collide after WeasyPrint rendering, using the same 0.5 mm tolerance."

## Optional improvements (not blocking)

- **P0.2:** for B, try WeasyPrint's public anchor/position data before concluding that overflow detection needs private APIs. This would make the "private API" finding fairer.
- **P1:** name the test runner, type checker and PDF parser that go into the main project's dev group. The design says Slice 1 adds them, and "type checks pass" currently has no named tool.
- **P1/P3:** say that P3 may lower the point/series limits set in P1 once label-density boundaries are measured. That avoids an implied freeze before chart evidence exists.
- **P0.3:** allow Linux evidence from a container runtime that's already installed locally. The plan should still not install packages or create cloud infrastructure for this.
- **P0.2:** add a rule for A failing early that mirrors the one for B ("if A fails a hard gate, record it and stop"), for symmetry.

## Verdict

**I endorse the plan once correction 1 (P0 exit) and correction 2 (sdist exclusion) are made.** Correction 3 is a one-line addition and I strongly recommend it, because it keeps the backend comparison fair. Nothing else blocks endorsement. The backend decision is still open, as it should be at this stage.
