"""Publish complete output without destroying an existing report on failure."""

import os
import tempfile
from pathlib import Path


def publish(path: str | Path, data: bytes, overwrite: bool) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".cardreport-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp, target)
        else:
            # Same-directory hard link atomically fails if a competing writer won.
            os.link(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return target
