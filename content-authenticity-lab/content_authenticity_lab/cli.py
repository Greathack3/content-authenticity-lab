from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .manifest import write_manifest
from .scanner import scan_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="media-manifest",
        description="Scan a folder and write a SHA-256 media metadata manifest.",
    )
    parser.add_argument("folder", type=Path, help="folder containing sample media")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output manifest path (default: manifest.<format> in current directory)",
    )
    parser.add_argument(
        "-f", "--format", choices=("csv", "json"), default="json",
        help="manifest format (default: json)",
    )
    parser.add_argument(
        "--no-recursive", action="store_true",
        help="scan only files directly inside the folder",
    )
    parser.add_argument(
        "--validate-signatures", action="store_true",
        help="check basic signatures for common image extensions; not a full decoder",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output = args.output or Path(f"manifest.{args.format}")

    try:
        records = scan_folder(
            args.folder,
            recursive=not args.no_recursive,
            validate_signatures=args.validate_signatures,
        )
        write_manifest(records, output, args.format)
    except (OSError, ValueError) as exc:
        print(f"media-manifest: error: {exc}", file=sys.stderr)
        return 2

    malformed = sum(r["status"] == "malformed" for r in records)
    errors = sum(r["status"] == "error" for r in records)
    print(
        f"Scanned {len(records)} file(s); "
        f"{malformed} malformed; {errors} error(s). Manifest: {output}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
