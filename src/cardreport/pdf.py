"""Bound the complete Chromium export in an owned, isolated process."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack

from .document import ReportDocument
from .model import (
    DependencyError,
    LayoutOverflowError,
    RenderError,
    RenderTimeoutError,
    UnsupportedFeatureError,
)

# Keep OS waits representable even when the caller supplies a very large deadline.
_MAX_WAIT_SECONDS = 3600


def render_pdf(report: ReportDocument, *, deadline: float) -> bytes:
    if any(
        importlib.util.find_spec(name) is None
        for name in ("playwright", "psutil", "pypdf")
    ):
        raise DependencyError(
            "Install cardreport[pdf] and run: python -m playwright install chromium"
        )
    from .html import render_html

    html = render_html(report)
    left = deadline - time.monotonic()
    if left <= 0:
        raise RenderTimeoutError("HTML preparation exceeded export deadline")
    w, h = report.page.dimensions()
    return run_worker(
        "cardreport._worker",
        html.encode(),
        [str(math.ceil(w * 96 / 25.4)), str(math.ceil(h * 96 / 25.4))],
        deadline=deadline,
    )


def run_worker(
    module: str, payload: bytes, args: list[str], *, deadline: float, pdf: bool = True
) -> bytes:
    left = deadline - time.monotonic()
    if left <= 0:
        raise RenderTimeoutError("Export deadline expired")
    with ExitStack() as stack:
        pending: bytes | None = payload
        source = None
        if left > _MAX_WAIT_SECONDS:
            # communicate(None) cannot resume partially sent stdin on POSIX.
            # A seekable input avoids pipe backpressure across repeated waits.
            source = stack.enter_context(tempfile.TemporaryFile())
            source.write(payload)
            source.seek(0)
            pending = None
        left = deadline - time.monotonic()
        if left <= 0:
            raise RenderTimeoutError("Export preparation exceeded deadline")
        process = subprocess.Popen(
            [sys.executable, "-m", module, *args],
            stdin=source if source is not None else subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            while True:
                try:
                    out, err = process.communicate(
                        pending, timeout=min(left, _MAX_WAIT_SECONDS)
                    )
                    break
                except subprocess.TimeoutExpired:
                    if left <= _MAX_WAIT_SECONDS:
                        raise
                    left = deadline - time.monotonic()
                    if left <= 0:
                        raise
                    pending = None
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError(
                "Export exceeded deadline; owned renderer was stopped"
            ) from None
        finally:
            if process.poll() is None:
                stop_worker(process)
    if process.returncode:
        try:
            error = json.loads(
                err.decode("utf-8", errors="replace").strip().splitlines()[-1]
            )
            if not isinstance(error, dict) or not isinstance(error.get("message"), str):
                raise ValueError("invalid error payload")
        except (ValueError, IndexError):
            raise RenderError("PDF worker failed unexpectedly") from None
        classes = {
            "DependencyError": DependencyError,
            "LayoutOverflowError": LayoutOverflowError,
            "RenderError": RenderError,
            "UnsupportedFeatureError": UnsupportedFeatureError,
            "RenderTimeoutError": RenderTimeoutError,
        }
        raise classes.get(str(error.get("kind", "RenderError")), RenderError)(
            error["message"]
        )
    if pdf and not out.startswith(b"%PDF-"):
        raise RenderError("Renderer did not return a PDF")
    return out


def stop_worker(process: subprocess.Popen[bytes]) -> None:
    """Kill this worker's descendants, including Chromium's detached process group."""
    import psutil

    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []
    # Stop the worker first so it cannot react to a dying driver or spawn more work.
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, PermissionError):
        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
    for child in reversed(descendants):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    process.wait()
    psutil.wait_procs(descendants, timeout=3)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
