"""Reject incomplete release test runs, including skipped optional engines."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def check(path: Path) -> None:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    if not cases or any(
        case.find(kind) is not None
        for case in cases
        for kind in ("skipped", "failure", "error")
    ):
        raise ValueError("release tests must pass with no skips")
    print(f"Verified {len(cases)} passing tests without skips")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
