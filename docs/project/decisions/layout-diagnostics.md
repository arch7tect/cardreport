# Measured layout diagnostics

Add one optional immutable `LayoutDiagnostic` to `LayoutOverflowError`, preserving
existing exception strings and rejection behavior. Diagnostics describe the first
failed check, not every problem in a report. Existing errors without measurements
remain valid. No template/schema revision, automatic resizing or measure API.

The public record contains a closed reason, renderer component path, optional
one-based page, measurement box (`content`, `padding`, `border`, `viewport`),
available width/height and directional overflow in millimetres. Missing values
mean unmeasured, never zero. The numbers describe the current layout, not a
minimum sufficient new allocation. CSS pixels convert at 96 dpi; PDF points at
72 dpi. UI rounds for display only. The existing one-pixel tolerances stay intact.

WeasyPrint keeps its content-box versus descendant margin-box check and computes
the maximum excess for the failed box. Chromium keeps scroll/client padding-box
checks and border rectangles, explicitly identifying their measurement basis.
Chart collisions receive reason/path/page when available; no fabricated required
size, raw label text, report title or dataset values enter structured fields.

A bounded, validated JSON representation survives both renderer workers and the
Python parent. Invalid optional diagnostics are discarded without losing the
original error. Server consumers forward only this validated representation,
retain generic safe messages and support old errors. The UI shows location,
measured dimensions/excess and a reason-specific suggestion, explicitly stating
that resizing may change layout. No database migration is required.

Verification covers known directional extents, tolerance, first-failure maxima,
no-data-text transport, both real renderers, old/malformed payloads, API and UI.
Release the library first, then update the server's minimum dependency and lock.
