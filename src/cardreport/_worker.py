"""Private PDF worker. The parent enforces a hard process-tree deadline."""

import io
import json
import sys

from .model import DependencyError, LayoutOverflowError, RenderError


def main() -> None:
    from playwright.sync_api import Error, sync_playwright

    html = sys.stdin.buffer.read().decode("utf-8")
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(timeout=0)
        except Error:
            raise DependencyError(
                "Chromium unavailable. Run: python -m playwright install chromium"
            ) from None
        try:
            context = browser.new_context(
                service_workers="block",
                viewport={"width": int(sys.argv[1]), "height": int(sys.argv[2])},
            )
            context.set_default_timeout(0)
            context.set_default_navigation_timeout(0)
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            failures = []
            requests = []
            page.on("request", lambda request: requests.append(request.url))
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.emulate_media(media="print")
            page.set_content(html, wait_until="load")
            page.wait_for_function(
                "window.cardreport && (window.cardreport.ready || window.cardreport.error)",
                timeout=0,
            )
            state = page.evaluate("window.cardreport")
            if state.get("error"):
                raise (
                    LayoutOverflowError
                    if state["error"]["kind"] == "LayoutOverflowError"
                    else RenderError
                )(state["error"]["message"])
            if failures:
                raise RenderError("Report JavaScript failed")
            if any(not u.startswith(("data:", "blob:", "about:")) for u in requests):
                raise RenderError("Unexpected external resource request")
            data = page.pdf(print_background=True, prefer_css_page_size=True, scale=1)
            from pypdf import PdfReader, PdfWriter
            from pypdf.generic import NameObject, TextStringObject

            if len(PdfReader(io.BytesIO(data)).pages) != state["pages"]:
                raise RenderError("Printed page count differs from measured layout")
            writer = PdfWriter(clone_from=io.BytesIO(data))
            writer.root_object[NameObject("/Lang")] = TextStringObject(
                page.evaluate("document.documentElement.lang")
            )
            output = io.BytesIO()
            writer.write(output)
            data = output.getvalue()
            context.close()
        finally:
            browser.close()
    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        kind = type(exc).__name__
        message = (
            str(exc)
            if kind in ("DependencyError", "LayoutOverflowError", "RenderError")
            else "PDF renderer failed"
        )
        sys.stderr.write("\n" + json.dumps({"kind": kind, "message": message}) + "\n")
        sys.exit(1)
