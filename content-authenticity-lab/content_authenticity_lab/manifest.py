from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .scanner import FIELDS


def write_manifest(records: Iterable[dict[str, Any]], output: str | Path, fmt: str) -> None:
    """Write records to CSV or JSON."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(records)

    if fmt == "json":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            json.dump(rows, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    elif fmt == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    else:
        raise ValueError(f"unsupported manifest format: {fmt}")
