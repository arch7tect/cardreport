"""Plan main releases and preserve the exact verified distribution across retries."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import tomllib
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Literal

REPO = "arch7tect/cardreport"
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def version_key(version: str) -> tuple[int, ...]:
    if not VERSION.fullmatch(version):
        raise ValueError("release versions must be canonical X.Y.Z")
    return tuple(int(part) for part in version.split("."))


def project_version() -> str:
    version = str(
        tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    )
    version_key(version)
    return version


def changelog_notes(version: str, source: str) -> str:
    """Extract one dated entry, refusing ambiguous or incomplete release notes."""
    version_key(version)
    sections = list(re.finditer(r"^## (.+)$", source, re.MULTILINE))
    if not sections or sections[0].group(1) != "Unreleased":
        raise ValueError("changelog must start with an Unreleased section")
    known: list[str] = []
    result = None
    for i, section in enumerate(sections[1:], 1):
        match = re.fullmatch(r"(\d+\.\d+\.\d+) — (\d{4}-\d{2}-\d{2})", section.group(1))
        if match is None:
            raise ValueError("invalid changelog version heading")
        current, released = match.groups()
        date.fromisoformat(released)
        version_key(current)
        if current in known or (
            known and version_key(current) >= version_key(known[-1])
        ):
            raise ValueError("changelog versions must be unique and descending")
        known.append(current)
        if current == version:
            end = sections[i + 1].start() if i + 1 < len(sections) else len(source)
            body = source[section.end() : end].strip()
            if not body or not any(
                line.strip() and not line.startswith("#") for line in body.splitlines()
            ):
                raise ValueError("empty changelog version section")
            result = body + "\n"
    if result is None:
        raise ValueError("missing changelog version section")
    return result


def release_notes(version: str, sha: str) -> str:
    if not SHA.fullmatch(sha):
        raise ValueError("invalid commit SHA")
    return changelog_notes(version, run("git", "show", f"{sha}:CHANGELOG.md"))


def tags() -> dict[str, str]:
    return {
        tag: run("git", "rev-parse", f"{tag}^{{}}")
        for tag in run("git", "tag", "--list", "v*").splitlines()
        if VERSION.fullmatch(tag[1:])
    }


def plan(
    version: str, sha: str, known: Mapping[str, str]
) -> Literal["new", "resume", "skip"]:
    current = version_key(version)
    if not SHA.fullmatch(sha):
        raise ValueError("expected a full commit SHA")
    tag = "v" + version
    # Resume an already reserved version even after newer releases exist.
    if known.get(tag) == sha:
        return "resume"
    if any(version_key(t[1:]) > current for t in known):
        raise ValueError("version is below an existing release tag")
    return "skip" if tag in known else "new"


def output(**values: str) -> None:
    text = "".join(f"{key}={value}\n" for key, value in values.items())
    print(text, end="")
    if target := os.environ.get("GITHUB_OUTPUT"):
        with Path(target).open("a") as handle:
            handle.write(text)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def filenames(version: str) -> set[str]:
    version_key(version)
    return {f"cardreport-{version}-py3-none-any.whl", f"cardreport-{version}.tar.gz"}


def freeze(directory: Path, version: str, sha: str) -> None:
    if not SHA.fullmatch(sha) or {p.name for p in directory.iterdir()} != filenames(
        version
    ):
        raise ValueError(
            "expected exactly one wheel and one sdist for this commit/version"
        )
    manifest = {
        "version": version,
        "commit": sha,
        "files": {
            name: digest(directory / name) for name in sorted(filenames(version))
        },
    }
    (directory / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verify(directory: Path, version: str, sha: str) -> None:
    if not SHA.fullmatch(sha):
        raise ValueError("invalid commit SHA")
    expected = filenames(version)
    manifest = json.loads((directory / "release.json").read_text())
    if not isinstance(manifest, dict) or set(manifest) != {
        "version",
        "commit",
        "files",
    }:
        raise ValueError("invalid release manifest")
    if manifest["version"] != version or manifest["commit"] != sha:
        raise ValueError("release version/commit mismatch")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != expected:
        raise ValueError("invalid release file set")
    if {p.name for p in directory.iterdir()} != expected | {"release.json"}:
        raise ValueError("unexpected or missing release assets")
    for name in expected:
        if digest(directory / name) != files[name]:
            raise ValueError("release asset checksum mismatch")


def restore(directory: Path, version: str, sha: str) -> bool:
    """Reuse this run's original artifact, including a full workflow rerun."""
    run_id = os.environ["GITHUB_RUN_ID"]
    if not run_id.isdigit():
        raise ValueError("invalid run ID")
    count = run(
        "gh",
        "api",
        f"repos/{REPO}/actions/runs/{run_id}/artifacts",
        "--jq",
        '[.artifacts[] | select(.name == "distribution" and .expired == false)] | length',
    )
    if int(count):
        run(
            "gh",
            "run",
            "download",
            run_id,
            "--repo",
            REPO,
            "--name",
            "distribution",
            "--dir",
            str(directory),
        )
        verify(directory, version, sha)
        return True
    if tags().get("v" + version) == sha:
        raise ValueError(
            "reserved version has no retained run artifact; use published release assets for PyPI recovery"
        )
    return False


def release_info(tag: str) -> dict[str, object] | None:
    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", REPO, "--json", "isDraft,assets"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        if "release not found" in result.stderr.lower():
            return None
        raise RuntimeError(result.stderr.strip())
    value: dict[str, object] = json.loads(result.stdout)
    return value


def publish_github(directory: Path, version: str, sha: str) -> None:
    verify(directory, version, sha)
    run("git", "fetch", "origin", "--tags")
    action = plan(version, sha, tags())
    if action == "skip":
        raise ValueError("this version belongs to a different commit")
    tag = "v" + version
    notes = (
        release_notes(version, sha)
        if action == "new" or version_key(version) >= (0, 3, 0)
        else None
    )
    if action == "new":
        run(
            "git",
            "-c",
            "user.name=github-actions[bot]",
            "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "tag",
            "-a",
            tag,
            sha,
            "-m",
            f"CardReport {version}",
        )
        run("git", "push", "origin", f"refs/tags/{tag}")
    info = release_info(tag)
    with tempfile.TemporaryDirectory() as temporary:
        notes_path = Path(temporary) / "notes.md"
        if notes is not None:
            notes_path.write_text(notes, encoding="utf-8")
        if info is None:
            run(
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                REPO,
                "--verify-tag",
                "--draft",
                "--title",
                f"CardReport {version}",
                *(
                    ["--notes-file", str(notes_path)]
                    if notes is not None
                    else ["--generate-notes"]
                ),
            )
            info = release_info(tag)
        elif info["isDraft"] and notes is not None:
            run(
                "gh",
                "release",
                "edit",
                tag,
                "--repo",
                REPO,
                "--notes-file",
                str(notes_path),
            )
    assert info is not None
    assets = info["assets"]
    if not isinstance(assets, list):
        raise ValueError("invalid GitHub assets response")
    existing = {str(asset["name"]) for asset in assets}
    expected = filenames(version) | {"release.json"}
    if existing - expected:
        raise ValueError("unexpected existing GitHub assets")
    for name in sorted(expected):
        if name in existing:
            with tempfile.TemporaryDirectory() as temporary:
                run(
                    "gh",
                    "release",
                    "download",
                    tag,
                    "--repo",
                    REPO,
                    "--pattern",
                    name,
                    "--dir",
                    temporary,
                )
                if digest(Path(temporary) / name) != digest(directory / name):
                    raise ValueError(
                        "existing GitHub asset differs; refusing replacement"
                    )
        elif info["isDraft"]:
            run("gh", "release", "upload", tag, str(directory / name), "--repo", REPO)
        else:
            raise ValueError("published GitHub release is incomplete")
    if info["isDraft"]:
        latest = max(version_key(t[1:]) for t in tags()) == version_key(version)
        run(
            "gh",
            "release",
            "edit",
            tag,
            "--repo",
            REPO,
            "--draft=false",
            "--latest=" + str(latest).lower(),
        )


def download_release(directory: Path, tag: str) -> None:
    if not tag.startswith("v"):
        raise ValueError("expected vX.Y.Z")
    version = tag[1:]
    version_key(version)
    sha = tags()[tag]
    run("git", "merge-base", "--is-ancestor", sha, "origin/main")
    info = release_info(tag)
    if info is None or info["isDraft"]:
        raise ValueError("PyPI requires a completed GitHub Release")
    run("gh", "release", "download", tag, "--repo", REPO, "--dir", str(directory))
    verify(directory, version, sha)
    output(version=version, sha=sha)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["plan", "freeze", "restore", "github", "download", "notes"]
    )
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--tag")
    args = parser.parse_args()
    if args.command == "download":
        if not args.tag:
            parser.error("download requires --tag")
        download_release(args.dist, args.tag)
        return
    version, sha = project_version(), run("git", "rev-parse", "HEAD")
    if args.command == "notes":
        print(
            changelog_notes(version, Path("CHANGELOG.md").read_text(encoding="utf-8")),
            end="",
        )
    elif args.command == "plan":
        action = plan(version, sha, tags())
        if action == "new":
            release_notes(version, sha)
        output(action=action, version=version, tag="v" + version)
    elif args.command == "freeze":
        freeze(args.dist, version, sha)
    elif args.command == "restore":
        output(restored=str(restore(args.dist, version, sha)).lower())
    else:
        publish_github(args.dist, version, sha)


if __name__ == "__main__":
    main()
