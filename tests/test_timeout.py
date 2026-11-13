import time

import pytest

from cardreport import Report, ValidationError
from cardreport.pdf import run_worker
from cardreport.validation import validate_timeout


@pytest.mark.parametrize(
    "value", [0, -1, float("nan"), float("inf"), -float("inf"), True, "30", 10**400]
)
def test_invalid_timeout(value):
    with pytest.raises(ValidationError, match="finite positive"):
        validate_timeout(value)


@pytest.mark.parametrize("value", [301, 3600, 1e7])
def test_long_timeout_reaches_renderer(value):
    # Deliberately duck-typed: exports do not add a runtime inheritance gate.
    class Renderer:
        def render_pdf(self, doc, *, deadline):
            assert value - 2 < deadline - time.monotonic() <= value
            return b"%PDF-test"

        def render_html(self, doc):
            return ""

    assert Report().to_pdf(timeout=value, renderer=Renderer()) == b"%PDF-test"


def test_large_timeout_does_not_overflow_system_wait():
    assert b"Zen of Python" in run_worker(
        "this", b"", [], deadline=time.monotonic() + 1e100, pdf=False
    )


def test_chunked_wait_preserves_input_and_output(tmp_path, monkeypatch):
    import cardreport.pdf as pdf

    (tmp_path / "timeout_fixture.py").write_text(
        "import sys,time\n"
        "time.sleep(0.05)\n"
        "data=sys.stdin.buffer.read()\n"
        "sys.stdout.buffer.write(b'before:'); sys.stdout.buffer.flush()\n"
        "time.sleep(0.1)\n"
        "sys.stdout.buffer.write(data)\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(pdf, "_MAX_WAIT_SECONDS", 0.02)
    payload = b"payload" * 100000
    assert (
        run_worker(
            "timeout_fixture", payload, [], deadline=time.monotonic() + 10, pdf=False
        )
        == b"before:" + payload
    )


def test_chunked_wait_expiry_stops_worker(tmp_path, monkeypatch):
    import cardreport.pdf as pdf
    from cardreport import RenderTimeoutError

    (tmp_path / "timeout_sleep.py").write_text("import time; time.sleep(60)\n")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(pdf, "_MAX_WAIT_SECONDS", 0.02)
    stopped = []
    original = pdf.stop_worker

    def stop(process):
        original(process)
        stopped.append(process.poll())

    monkeypatch.setattr(pdf, "stop_worker", stop)
    with pytest.raises(RenderTimeoutError):
        run_worker("timeout_sleep", b"", [], deadline=time.monotonic() + 0.2, pdf=False)
    assert len(stopped) == 1 and stopped[0] is not None
