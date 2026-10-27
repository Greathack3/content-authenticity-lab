# Content Authenticity Lab

A small Python command-line tool that scans a directory of sample media and writes a CSV or JSON manifest containing file type, size, SHA-256, UTC modification timestamp, and status/error information.

## Requirements

- Python 3.10+
- No runtime dependencies

## Install locally

From the project directory:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Then install the package:

```bash
python -m pip install -e .
```

## Usage

JSON output:

```bash
media-manifest ./sample-media --format json --output manifest.json
```

CSV output:

```bash
media-manifest ./sample-media --format csv --output manifest.csv
```

Check basic image signatures:

```bash
media-manifest ./sample-media --format json --output manifest.json --validate-signatures
```

Scan only the top-level folder:

```bash
media-manifest ./sample-media --no-recursive --format csv --output manifest.csv
```

You can also run without installing the console script:

```bash
python -m content_authenticity_lab.cli ./sample-media --format json --output manifest.json
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Manifest fields

| Field | Meaning |
|---|---|
| `path` | Path relative to the scanned folder |
| `file_type` | MIME type guessed from the filename; not proof of actual content |
| `size_bytes` | File size in bytes |
| `sha256` | SHA-256 hash of the file bytes |
| `timestamp_utc` | File-system modification time converted to UTC |
| `status` | `ok`, `malformed`, or `error` |
| `error` | Explanation when validation or reading fails |

## Malformed-file handling

Without `--validate-signatures`, files are hashed and inventoried without attempting to decode them. With that option, the tool checks a small set of common image signatures (JPEG, PNG, GIF, WebP, BMP, TIFF). A mismatch is marked `malformed`; an unreadable file is marked `error`. Unsupported formats are not declared valid or invalid.

These are lightweight checks, not comprehensive media validation. A file can have the correct signature but still be truncated or internally malformed. A file extension can also be misleading. For stronger validation, add format-specific parsers/decoders and preserve their version and results in the manifest.

## Integrity and authenticity caveats

- SHA-256 identifies file bytes with extremely high collision resistance; it does not establish authorship or truthfulness.
- A timestamp here is the file system's modification time, not a trusted creation timestamp. Copying or editing a file can change it.
- A manifest is not tamper-proof merely because it contains hashes. For chain-of-custody workflows, hash the manifest, sign it, record tool versions, and store logs in a trusted location.
- The scanner does not modify the source files.
