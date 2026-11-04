"""Check local Markdown links and execute user-facing Python examples."""

import argparse
import contextlib
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FENCES = re.compile(r"^```([^\n]*)\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
LINKS = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")


def anchors(source: str) -> set[str]:
    result = set(re.findall(r'<a\s+(?:id|name)="([^"]+)"', source))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", source, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def check_links(paths: list[Path]) -> int:
    checked = 0
    errors: list[str] = []
    external: set[str] = set()
    for path in paths:
        source = FENCES.sub("", path.read_text())
        for match in LINKS.finditer(source):
            target = match.group(1).strip().split(' "', 1)[0].strip("<>")
            url = urlsplit(target)
            prefix = "/arch7tect/cardreport/blob/main/"
            if url.netloc == "github.com" and url.path.startswith(prefix):
                destination = ROOT / unquote(url.path.removeprefix(prefix))
            elif url.scheme or url.netloc:
                external.add(target)
                continue
            else:
                destination = path.parent / unquote(url.path) if url.path else path
            checked += 1
            problem = None
            if not destination.exists():
                problem = "missing target"
            elif url.fragment and destination.suffix == ".md":
                if unquote(url.fragment) not in anchors(
                    FENCES.sub("", destination.read_text())
                ):
                    problem = "missing anchor"
            if problem:
                line = source.count("\n", 0, match.start()) + 1
                errors.append(f"{path.relative_to(ROOT)}:{line}: {problem}: {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Checked {checked} local links in {len(paths)} Markdown files")
    if external:
        print("External links (inventory only; not checked offline):")
        for target in sorted(external):
            print(f"  {target}")
    return checked


def check_examples(paths: list[Path]) -> None:
    count = 0
    sys.path.insert(0, str(ROOT))
    for path in paths:
        with tempfile.TemporaryDirectory(prefix="cardreport-docs-") as directory:
            namespace = {"__name__": "__docs__"}
            with contextlib.chdir(directory):
                for block in FENCES.finditer(path.read_text()):
                    if block.group(1).strip() != "python":
                        continue
                    line = path.read_text().count("\n", 0, block.start()) + 2
                    label = f"{path.relative_to(ROOT)}:{line}"
                    print(f"Running {label}", flush=True)
                    code = compile(
                        "\n" * (line - 1) + block.group(2), str(path), "exec"
                    )
                    try:
                        exec(code, namespace)
                    except Exception as error:
                        raise RuntimeError(
                            f"Documentation example failed: {label}"
                        ) from error
                    if "pdf" in namespace:
                        pdf = namespace["pdf"]
                        if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
                            raise AssertionError(f"Invalid PDF result: {label}")
                    count += 1
    print(f"Executed {count} Python blocks in {len(paths)} documentation pages")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--links-only", action="store_true")
    args = parser.parse_args()
    paths = sorted(
        [
            *ROOT.glob("*.md"),
            *ROOT.glob("docs/**/*.md"),
            *ROOT.glob("experiments/**/*.md"),
        ]
    )
    paths = [
        path
        for path in paths
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    ]
    check_links(paths)
    if not args.links_only:
        from cardreport import ReportTemplate, datasets_from_json

        examples = ROOT / "examples"
        template = ReportTemplate.from_json(
            (examples / "reference_template.json").read_bytes()
        )
        for filename in ("reference_data.json", "reference_data_second.json"):
            template.bind(
                datasets_from_json((examples / filename).read_bytes())
            ).validate()
        ReportTemplate.from_json(
            (examples / "spanish_template.json").read_bytes()
        ).bind(
            datasets_from_json((examples / "spanish_data.json").read_bytes())
        ).validate()
        print("Validated reference and Spanish template/data JSON fixtures")
        check_examples([ROOT / "README.md", *sorted(ROOT.glob("docs/user/*.md"))])


if __name__ == "__main__":
    main()
