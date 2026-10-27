import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from content_authenticity_lab.manifest import write_manifest
from content_authenticity_lab.scanner import scan_file, scan_folder


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_hash_size_and_timestamp_are_recorded(self):
        payload = b"sample media bytes"
        path = self.root / "sample.bin"
        path.write_bytes(payload)

        record = scan_file(path, self.root)
        self.assertEqual(record["size_bytes"], len(payload))
        self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertTrue(record["timestamp_utc"].endswith("Z"))
        self.assertEqual(record["status"], "ok")

    def test_signature_mismatch_is_marked_malformed(self):
        path = self.root / "fake.png"
        path.write_bytes(b"this is not a PNG")

        record = scan_file(path, self.root, validate_signatures=True)
        self.assertEqual(record["status"], "malformed")
        self.assertIn("signature", record["error"])

    def test_empty_png_is_malformed(self):
        path = self.root / "empty.png"
        path.write_bytes(b"")

        record = scan_file(path, self.root, validate_signatures=True)
        self.assertEqual(record["status"], "malformed")
        self.assertIsNotNone(record["sha256"])

    def test_recursive_scan_finds_nested_files(self):
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "one.txt").write_text("one", encoding="utf-8")
        (self.root / "two.txt").write_text("two", encoding="utf-8")

        records = scan_folder(self.root)
        self.assertEqual([r["path"] for r in records], ["nested/one.txt", "two.txt"])

    def test_non_recursive_scan_only_finds_top_level(self):
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "one.txt").write_text("one", encoding="utf-8")
        (self.root / "two.txt").write_text("two", encoding="utf-8")

        records = scan_folder(self.root, recursive=False)
        self.assertEqual([r["path"] for r in records], ["two.txt"])

    def test_json_manifest_round_trip(self):
        path = self.root / "a.txt"
        path.write_text("hello", encoding="utf-8")
        records = scan_folder(self.root)
        output = self.root / "out.json"

        write_manifest(records, output, "json")
        loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded[0]["sha256"], records[0]["sha256"])

    def test_csv_manifest_has_expected_columns(self):
        path = self.root / "a.txt"
        path.write_text("hello", encoding="utf-8")
        records = scan_folder(self.root)
        output = self.root / "out.csv"

        write_manifest(records, output, "csv")
        text = output.read_text(encoding="utf-8")
        self.assertIn("path,file_type,size_bytes,sha256,timestamp_utc,status,error", text)

    def test_missing_folder_raises(self):
        with self.assertRaises(FileNotFoundError):
            scan_folder(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
