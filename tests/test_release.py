import json
from pathlib import Path

import pytest

from scripts.check_test_results import check
from scripts.release import filenames, freeze, plan, verify, version_key

SHA = "a" * 40
OLD = "b" * 40


def test_release_selection():
    assert plan("0.2.0", SHA, {"v0.2.0": OLD}) == "skip"
    assert plan("0.2.1", SHA, {"v0.2.0": OLD}) == "new"
    assert plan("0.2.1", SHA, {"v0.2.1": SHA}) == "resume"
    assert plan("0.2.1", SHA, {"v0.2.1": SHA, "v0.3.0": OLD}) == "resume"
    with pytest.raises(ValueError):
        plan("0.1.9", SHA, {"v0.2.0": OLD})
    with pytest.raises(ValueError):
        plan("0.1.9", SHA, {"v0.1.9": OLD, "v0.2.0": OLD})


@pytest.mark.parametrize(
    "version",
    ["v0.2.1", "0.02.1", "0.2", "0.2.1.dev1", "0.2.1+local", "0.2.1\n", "../../x"],
)
def test_version_policy(version):
    with pytest.raises(ValueError):
        version_key(version)


def bundle(path: Path):
    for name in filenames("0.2.1"):
        (path / name).write_bytes(name.encode())
    freeze(path, "0.2.1", SHA)


def test_exact_artifact_integrity(tmp_path):
    bundle(tmp_path)
    verify(tmp_path, "0.2.1", SHA)
    with pytest.raises(ValueError):
        verify(tmp_path, "0.2.1", OLD)
    (tmp_path / "cardreport-0.2.1.tar.gz").write_bytes(b"different build")
    with pytest.raises(ValueError, match="checksum"):
        verify(tmp_path, "0.2.1", SHA)


@pytest.mark.parametrize("change", ["extra", "missing", "path", "version"])
def test_manifest_rejects_changes(tmp_path, change):
    bundle(tmp_path)
    path = tmp_path / "release.json"
    obj = json.loads(path.read_text())
    if change == "extra":
        (tmp_path / "secret.env").write_text("test")
    elif change == "missing":
        (tmp_path / "cardreport-0.2.1.tar.gz").unlink()
    elif change == "path":
        obj["files"]["../outside"] = "0" * 64
    else:
        obj["version"] = "0.2.2"
    path.write_text(json.dumps(obj))
    with pytest.raises(ValueError):
        verify(tmp_path, "0.2.1", SHA)


@pytest.mark.parametrize("status", ["skipped", "failure", "error"])
def test_release_tests_may_not_skip(tmp_path, status):
    path = tmp_path / "results.xml"
    path.write_text(
        f"<testsuites><testsuite><testcase><{status}/></testcase></testsuite></testsuites>"
    )
    with pytest.raises(ValueError):
        check(path)
    path.write_text("<testsuites><testsuite><testcase/></testsuite></testsuites>")
    check(path)


def test_github_resume_checks_existing_assets(tmp_path, monkeypatch):
    import scripts.release as release

    bundle(tmp_path)
    calls = []
    monkeypatch.setattr(release, "tags", lambda: {"v0.2.1": SHA})
    monkeypatch.setattr(
        release,
        "release_info",
        lambda tag: {"isDraft": True, "assets": [{"name": "release.json"}]},
    )

    def run(*args):
        calls.append(args)
        if args[:3] == ("gh", "release", "download"):
            directory = Path(args[args.index("--dir") + 1])
            (directory / "release.json").write_bytes(
                (tmp_path / "release.json").read_bytes()
            )
        return ""

    monkeypatch.setattr(release, "run", run)
    release.publish_github(tmp_path, "0.2.1", SHA)
    assert not any("tag" in command for command in calls)
    assert len([command for command in calls if "upload" in command]) == 2
    assert any("--draft=false" in command for command in calls)


def test_github_resume_refuses_replacement(tmp_path, monkeypatch):
    import scripts.release as release

    bundle(tmp_path)
    monkeypatch.setattr(release, "tags", lambda: {"v0.2.1": SHA})
    monkeypatch.setattr(
        release,
        "release_info",
        lambda tag: {
            "isDraft": False,
            "assets": [
                {"name": name} for name in filenames("0.2.1") | {"release.json"}
            ],
        },
    )

    def run(*args):
        if args[:3] == ("gh", "release", "download"):
            directory = Path(args[args.index("--dir") + 1])
            name = args[args.index("--pattern") + 1]
            (directory / name).write_bytes(b"different")
        assert "upload" not in args
        return ""

    monkeypatch.setattr(release, "run", run)
    with pytest.raises(ValueError, match="refusing replacement"):
        release.publish_github(tmp_path, "0.2.1", SHA)


def test_rerun_restores_original_artifact(tmp_path, monkeypatch):
    import scripts.release as release

    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    calls = []

    def run(*args):
        calls.append(args)
        if args[:2] == ("gh", "api"):
            return "1"
        bundle(tmp_path)
        return ""

    monkeypatch.setattr(release, "run", run)
    assert release.restore(tmp_path, "0.2.1", SHA)
    assert any(command[:3] == ("gh", "run", "download") for command in calls)


def test_reserved_version_without_original_artifact_fails(tmp_path, monkeypatch):
    import scripts.release as release

    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setattr(release, "run", lambda *args: "0")
    monkeypatch.setattr(release, "tags", lambda: {"v0.2.1": SHA})
    with pytest.raises(ValueError, match="no retained run artifact"):
        release.restore(tmp_path, "0.2.1", SHA)


def test_pypi_recovery_requires_completed_main_release(tmp_path, monkeypatch):
    import scripts.release as release

    monkeypatch.setattr(release, "tags", lambda: {"v0.2.1": SHA})
    monkeypatch.setattr(release, "release_info", lambda tag: {"isDraft": True})
    commands = []
    monkeypatch.setattr(release, "run", lambda *args: commands.append(args) or "")
    with pytest.raises(ValueError, match="completed GitHub Release"):
        release.download_release(tmp_path, "v0.2.1")
    assert commands == [("git", "merge-base", "--is-ancestor", SHA, "origin/main")]
    with pytest.raises(ValueError):
        release.download_release(tmp_path, "v../../main")
