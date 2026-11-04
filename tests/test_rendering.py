import io
import unicodedata

import pytest
from pypdf import PdfReader

from cardreport import *


def reader(report):
    return PdfReader(io.BytesIO(report.to_pdf()))


def extracted(r):
    return unicodedata.normalize("NFKC", "\n".join(p.extract_text() for p in r.pages))


def images_in(resources):
    resources = resources.get_object()
    for obj in (
        resources.get("/XObject", {}).get_object().values()
        if "/XObject" in resources
        else []
    ):
        obj = obj.get_object()
        if obj.get("/Subtype") == "/Image":
            yield obj
        if "/Resources" in obj:
            yield from images_in(obj["/Resources"])


def test_reference_content_vector_and_page():
    from examples.reference_report import build_report

    r = reader(build_report())
    t = extracted(r)
    assert len(r.pages) == 1
    assert abs(float(r.pages[0].mediabox.width) - 1600) < 0.3
    for label in [
        "Campaign progress",
        "Contact funnel",
        "Call attempt results",
        "Conversation outcomes",
        "Promise rate (PTP rate)",
        "Promised payments calendar",
        "40.0%",
        "60.0%",
        "2026-11-04",
        "Identity confirmed",
        "No answer / busy / voicemail",
        "34",
        "24",
        "21",
    ]:
        assert label in t, label
    assert not list(images_in(r.pages[0]["/Resources"]))
    stream = r.pages[0].get_contents().get_data()
    assert b" re" in stream or b" l" in stream
    fonts = r.pages[0]["/Resources"]["/Font"]
    assert any("DejaVuSans" in str(f.get_object()) for f in fonts.values())


def test_hostile_and_cyrillic_literal():
    phrase = "</script><b>&amp; $x$ <br> Пример"
    report = Report(page=Page(orientation="landscape")).row(
        Card(BarChart([phrase], [2], orientation="horizontal")), height_mm=90
    )
    assert phrase in extracted(reader(report))


@pytest.mark.parametrize(
    "report",
    [
        Report().row(Card(Text("word " * 400)), height_mm=20),
        Report().row(Card(KPI("tiny", 1)), height_mm=10),
        Report().add(Card(Text("word " * 1600))),
        Report().row(
            Card(
                BarChart(["Long label " + str(i) for i in range(30)], list(range(30)))
            ),
            height_mm=40,
        ),
    ],
)
def test_overflow_does_not_publish(report, tmp_path):
    dest = tmp_path / "bad.pdf"
    with pytest.raises(LayoutOverflowError):
        report.write_pdf(dest)
    assert not dest.exists()


def test_flow_exactly_once_rows_and_repeated_titles():
    report = Report("Flow", mode="flow")
    report.add(
        Card(
            Table(
                [TableColumn("id", "Identity"), TableColumn("value", "Value")],
                [
                    {"id": f"ROW-{i:03d}", "value": "Wrapped content " * 4}
                    for i in range(120)
                ],
            ),
            title="Items",
        )
    )
    r = reader(report)
    t = extracted(r)
    assert len(r.pages) > 1
    for i in range(120):
        assert t.count(f"ROW-{i:03d}") == 1
    for page in r.pages:
        assert "Identity" in page.extract_text() and "Items" in page.extract_text()
    assert not list(images_in(r.pages[0]["/Resources"]))


def test_oversized_flow_row():
    report = Report(mode="flow").add(
        Table([TableColumn("x", "X")], [{"x": "long " * 1900}])
    )
    with pytest.raises(LayoutOverflowError):
        report.to_pdf()


def test_pagebreaks_no_empty_pages():
    report = (
        Report()
        .new_page()
        .add(Text("First"))
        .new_page()
        .new_page()
        .add(Text("Second"))
        .new_page()
    )
    r = reader(report)
    assert len(r.pages) == 2
    assert (
        "First" in r.pages[0].extract_text() and "Second" in r.pages[1].extract_text()
    )
    assert len(reader(Report()).pages) == 1


def test_safe_output_and_timeout(tmp_path):
    dest = tmp_path / "existing.pdf"
    dest.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        Report().add(KPI("x", 1)).write_pdf(dest)
    assert dest.read_bytes() == b"original"
    with pytest.raises(RenderTimeoutError):
        Report().add(KPI("x", 1)).write_pdf(dest, overwrite=True, timeout=0.01)
    assert dest.read_bytes() == b"original"
    Report().add(KPI("x", 1)).write_pdf(dest, overwrite=True)
    assert dest.read_bytes().startswith(b"%PDF-")


def test_lines_series_funnel_empty():
    from datetime import date

    report = Report(page=Page(orientation="landscape"))
    report.row(
        Card(
            LineChart(
                [date(2026, 11, i) for i in (1, 2, 3)],
                series={"A": [1, None, 3], "B": [2, 1, 0]},
                x_kind="date",
            )
        ),
        Card(Funnel(["Start", "Finish"], [5, 2])),
        height_mm=90,
    )
    report.row(
        Card(BarChart(["a", "b"], series={"A": [2, -1], "B": [3, 2]}, mode="stacked")),
        Card(BarChart([], [])),
        height_mm=70,
    )
    t = extracted(reader(report))
    assert "Start" in t and "Finish" in t and "No data" in t


def test_fractional_page_and_initial_title_break():
    report = (
        Report("Heading", page=Page(size=(100.3, 150.7)))
        .new_page()
        .add(Text("Content"))
    )
    r = reader(report)
    assert len(r.pages) == 1
    assert "Heading" in extracted(r) and "Content" in extracted(r)


def test_funnel_labels_cannot_be_silently_clipped():
    from cardreport.charts import chart_spec

    chart = Funnel(["A", "B"], [1000000, 5], value_format=Currency("USD"))
    assert chart_spec(chart, Theme(), "test")["data"][0]["cliponaxis"] is False
    report = Report(page=Page(orientation="landscape")).row(Card(chart), height_mm=90)
    try:
        r = reader(report)
    except LayoutOverflowError:
        return  # Explicit rejection is preferable to clipped currency labels.
    assert "USD 1,000,000.00" in extracted(r)


def test_worker_timeout_and_interruption_cleanup(monkeypatch):
    import subprocess
    import time

    import psutil

    import cardreport.pdf as pdf

    original = pdf.stop_worker
    observed = []

    def record_then_stop(process):
        observed.extend(psutil.Process(process.pid).children(recursive=True))
        observed.append(psutil.Process(process.pid))
        original(process)

    monkeypatch.setattr(pdf, "stop_worker", record_then_stop)
    stalled = Report()
    monkeypatch.setattr(
        __import__("cardreport.html", fromlist=["render_html"]),
        "render_html",
        lambda doc: "<script>window.cardreport={ready:false}</script>",
    )
    real_communicate = subprocess.Popen.communicate

    def feed_until_browser(process, payload):
        process.stdin.write(payload)
        process.stdin.close()
        process.stdin = None
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                pytest.fail("worker exited before browser launch")
            try:
                if len(psutil.Process(process.pid).children(recursive=True)) >= 2:
                    return
            except psutil.NoSuchProcess:
                pytest.fail("worker exited before browser launch")
            if time.monotonic() >= deadline:
                pytest.fail("browser did not launch within 30 seconds")
            time.sleep(0.05)

    def time_out(process, payload, *args, **kwargs):
        # Exercise cleanup after launch, independently of machine startup speed.
        feed_until_browser(process, payload)
        return real_communicate(process, timeout=0.1)

    monkeypatch.setattr(subprocess.Popen, "communicate", time_out)
    with pytest.raises(RenderTimeoutError):
        stalled.to_pdf()
    assert len(observed) > 2, "test must reach browser/driver launch"
    assert not any(
        p.is_running() and p.status() != psutil.STATUS_ZOMBIE for p in observed
    )
    observed.clear()

    def interrupt(process, payload, *args, **kwargs):
        feed_until_browser(process, payload)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "communicate", interrupt)
    with pytest.raises(KeyboardInterrupt):
        stalled.to_pdf()
    assert len(observed) > 2, "interrupt test must reach browser launch"
    assert not any(
        p.is_running() and p.status() != psutil.STATUS_ZOMBIE for p in observed
    )


def test_cleanup_permission_race(monkeypatch):
    import subprocess
    import sys

    import cardreport.pdf as pdf

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)"], start_new_session=True
    )

    def denied(*args):
        raise PermissionError("simulated group zombie race")

    monkeypatch.setattr(pdf.os, "killpg", denied)
    pdf.stop_worker(process)
    assert process.poll() is not None
