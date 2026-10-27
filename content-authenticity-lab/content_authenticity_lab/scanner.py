from __future__ import annotations

import hashlib
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHUNK_SIZE = 1024 * 1024

# Lightweight signature checks for common image formats. These checks are
# intentionally not full decoders and cannot prove that a file is valid media.
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),  # Additional WEBP marker checked below.
    ".bmp": (b"BM",),
    ".tif": (b"II*\x00", b"MM\x00*"),
    ".tiff": (b"II*\x00", b"MM\x00*"),
}

FIELDS = [
    "path",
    "file_type",
    "size_bytes",
    "sha256",
    "timestamp_utc",
    "status",
    "error",
]


def _timestamp_utc(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def _identify_type(path: Path) -> str:
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _check_signature(path: Path, header: bytes) -> str | None:
    """Return an error message for a detectable signature mismatch, else None."""
    suffix = path.suffix.lower()
    signatures = SIGNATURES.get(suffix)
    if not signatures:
        return None  # Unknown format: do not pretend to validate it.

    if not header:
        return "empty file; expected a media file signature"

    if not any(header.startswith(sig) for sig in signatures):
        return f"file signature does not match extension {suffix!r}"

    if suffix == ".webp" and header[8:12] != b"WEBP":
        return "RIFF header found, but WEBP marker is missing"

    return None


def scan_file(path: Path, root: Path, validate_signatures: bool = False) -> dict[str, Any]:
    """Create a manifest record. File-level errors become records, not crashes."""
    record: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "file_type": _identify_type(path),
        "size_bytes": None,
        "sha256": None,
        "timestamp_utc": None,
        "status": "ok",
        "error": "",
    }

    try:
        stat = path.stat()
        if not path.is_file():
            record["status"] = "error"
            record["error"] = "not a regular file"
            return record

        record["size_bytes"] = stat.st_size
        record["timestamp_utc"] = _timestamp_utc(stat.st_mtime)

        digest = hashlib.sha256()
        header = b""
        with path.open("rb") as handle:
            header = handle.read(16)
            digest.update(header)
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)

        record["sha256"] = digest.hexdigest()

        if validate_signatures:
            signature_error = _check_signature(path, header)
            if signature_error:
                record["status"] = "malformed"
                record["error"] = signature_error

    except (OSError, PermissionError) as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        # Keep a problematic file from aborting the rest of the scan.
        record["status"] = "error"
        record["error"] = f"unexpected {type(exc).__name__}: {exc}"

    return record


def scan_folder(
    folder: str | Path,
    recursive: bool = True,
    validate_signatures: bool = False,
) -> list[dict[str, Any]]:
    """Scan regular files below folder and return records sorted by relative path."""
    root = Path(folder).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"input folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {root}")

    candidates = root.rglob("*") if recursive else root.glob("*")
    paths = sorted(
        (p for p in candidates if p.is_file() or p.is_symlink()),
        key=lambda p: p.as_posix().casefold(),
    )

    records = []
    for path in paths:
        # Do not follow symlinks to files outside the scanned root.
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            records.append({
                "path": path.relative_to(root).as_posix(),
                "file_type": _identify_type(path),
                "size_bytes": None,
                "sha256": None,
                "timestamp_utc": None,
                "status": "error",
                "error": "symlink target is missing or outside the input folder",
            })
            continue

        records.append(scan_file(path, root, validate_signatures))

    return records
