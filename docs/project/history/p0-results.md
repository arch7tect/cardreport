# P0 renderer experiment

> Update 2026-11-03: the owner authorized typed components, independent validation
> and a provisional renderer extension with an experimental SVG/WeasyPrint path.
> See [renderer extension](../decisions/renderer-extension.md); the original decision below is historical.


Date: 2026-11-03. Reproduction: experiments/rendering/compare.py and its uv.lock.
Raw HTML/PDF, results and SHA-256 manifest: ignored local/rendering-comparison/p0.

Both candidates generated selectable text and charts on macOS. WeasyPrint 70.0
needed DYLD_FALLBACK_LIBRARY_PATH pointed at existing Homebrew native libraries.
No new system packages were installed. Chromium was installed explicitly.

A fixed 10 mm-high text container was deliberately overfilled. WeasyPrint produced
one page, with its public anchor reporting only the allocated 39.8 px outer box;
the content extends outside it. It did not report overflow. Chromium exposed
38 px clientHeight versus 840 px scrollHeight, giving a direct rejection check.
Natural 120-row tables rendered with repeated headers in both engines (8 pages
in B, 7 in A). This is feasibility evidence, not full production pagination proof.

Choose A for the first working version: its measured layout directly supports
strict no-clipping errors without a second text/layout implementation or private
WeasyPrint box-tree access. This does not establish that B is incapable; it makes
B a less simple route for the agreed nested/overflow contract. Do not ship B.
Full A gates are checked in the library's integration suite, not assumed from this
small experiment. Linux remains unverified until an actual available run.

The verified source inventory maps entirely to the planned API with a small custom
page-size option. No user-visible capability is removed by choosing A. Browser and
JS remain private implementation details; PDF and HTML have no interactive controls.
