"""JSON I/O with atomic, owner-readable output files."""

import json
import os
import tempfile
from pathlib import Path


def read_json(path: str) -> object:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: str, value: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".r4dsg-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
