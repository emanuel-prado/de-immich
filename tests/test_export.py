import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import write_backup
from load_app import load_app


def arguments(library, backup, output, **overrides):
    values = {
        "library_root": library,
        "backup": backup,
        "output": output,
        "flat": True,
        "include_deleted": False,
        "include_offline": False,
        "copy_sidecars": False,
        "write_json_sidecars": False,
        "limit": None,
        "dry_run": False,
        "no_progress": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "library"
        (self.library / "upload").mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def _collision_backup(self):
        (self.library / "upload/one.bin").write_bytes(b"one")
        (self.library / "upload/two.bin").write_bytes(b"two")
        return write_backup(
            self.root / "backup.sql.gz",
            [
                {"id": "aaaaaaaa-1", "originalPath": "upload/one.bin", "originalFileName": "same.jpg"},
                {"id": "bbbbbbbb-2", "originalPath": "upload/two.bin", "originalFileName": "same.jpg"},
                {"id": "cccccccc-3", "originalPath": "upload/missing.bin", "originalFileName": "missing.jpg"},
            ],
        )

    def test_export_handles_collisions_and_records_missing_source(self):
        backup = self._collision_backup()
        output = self.root / "export"
        self.assertEqual(self.app.export_assets(arguments(self.library, backup, output)), 0)
        self.assertEqual((output / "same.jpg").read_bytes(), b"one")
        token = self.app.hashlib.sha256(b"bbbbbbbb-2").hexdigest()[:12]
        self.assertEqual((output / f"same__{token}.jpg").read_bytes(), b"two")
        with (output / "manifest.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["status"] for row in rows], ["exported", "exported", "missing-source"])
        self.assertEqual(rows[0]["verification"], "verified")
        self.assertEqual(rows[0]["sourceSha256"], rows[0]["exportedSha256"])
        self.assertEqual(len(rows[0]["sourceSha256"]), 64)
        self.assertFalse((output / "manifest.jsonl.partial").exists())

    def test_dry_run_reserves_the_same_collision_destinations(self):
        backup = self._collision_backup()
        destinations = []

        def record_copy(source, destination, timestamp, dry_run):
            destinations.append(destination.name)
            return None, None

        with mock.patch.object(self.app, "copy_with_metadata", side_effect=record_copy):
            self.app.export_assets(arguments(self.library, backup, self.root / "export", dry_run=True))
        token = self.app.hashlib.sha256(b"bbbbbbbb-2").hexdigest()[:12]
        self.assertEqual(destinations, ["same.jpg", f"same__{token}.jpg"])

    def test_atomic_copy_refuses_overwrite(self):
        source = self.root / "source"
        destination = self.root / "destination"
        source.write_bytes(b"new")
        destination.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            self.app.copy_with_metadata(source, destination, None, False)
        self.assertEqual(destination.read_bytes(), b"existing")

    def test_existing_manifest_stops_export_before_copying(self):
        backup = self._collision_backup()
        output = self.root / "export"
        output.mkdir()
        manifest = output / "manifest.csv"
        manifest.write_text("keep me", encoding="utf-8")

        with self.assertRaisesRegex(FileExistsError, "existing manifest"):
            self.app.export_assets(arguments(self.library, backup, output))

        self.assertEqual(manifest.read_text(encoding="utf-8"), "keep me")
        self.assertFalse((output / "same.jpg").exists())

    def test_manifest_verification_detects_corruption(self):
        backup = self._collision_backup()
        output = self.root / "export"
        self.app.export_assets(arguments(self.library, backup, output))

        self.assertEqual(self.app.verify_manifest(output / "manifest.jsonl"), 0)
        (output / "same.jpg").write_bytes(b"corrupt")
        self.assertEqual(self.app.verify_manifest(output / "manifest.jsonl"), 2)

    def test_manifest_verification_preserves_recorded_copy_failure(self):
        backup = self._collision_backup()
        output = self.root / "export"
        self.app.export_assets(arguments(self.library, backup, output))
        manifest = output / "manifest.jsonl"
        rows = [json.loads(line) for line in manifest.read_text().splitlines()]
        rows[0]["verification"] = "failed"
        rows[0]["sourceSha256"] = "0" * 64
        manifest.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )

        self.assertEqual(self.app.verify_manifest(manifest), 2)

    def test_manifest_verification_rejects_unknown_schema(self):
        manifest = self.root / "manifest.jsonl"
        manifest.write_text(
            json.dumps({"reportSchemaVersion": "99.0"}) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            self.app.BackupFormatError, "unsupported report schema"
        ):
            self.app.verify_manifest(manifest)

    def test_manifest_verification_rejects_export_without_fixity(self):
        manifest = self.root / "manifest.jsonl"
        manifest.write_text(
            json.dumps(
                {"reportSchemaVersion": "1.0", "status": "exported"}
            )
            + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            self.app.BackupFormatError, "incomplete fixity record"
        ):
            self.app.verify_manifest(manifest)

    def test_manifest_verification_rejects_symlink_substitution(self):
        backup = self._collision_backup()
        output = self.root / "export"
        self.app.export_assets(arguments(self.library, backup, output))
        exported = output / "same.jpg"
        replacement = self.root / "replacement.jpg"
        replacement.write_bytes(exported.read_bytes())
        exported.unlink()
        exported.symlink_to(replacement)

        self.assertEqual(self.app.verify_manifest(output / "manifest.jsonl"), 2)

    def test_skipped_assets_are_recorded(self):
        backup = write_backup(
            self.root / "skips.sql.gz",
            [
                {"id": "deleted", "originalPath": "upload/a", "originalFileName": "a.jpg", "deletedAt": "2026-01-01 00:00:00+00"},
                {"id": "offline", "originalPath": "upload/b", "originalFileName": "b.jpg", "isOffline": "t"},
                {"id": "unnamed", "originalPath": "upload/c", "originalFileName": None},
            ],
        )
        output = self.root / "export"

        self.app.export_assets(arguments(self.library, backup, output))

        with (output / "manifest.csv").open(newline="", encoding="utf-8") as handle:
            statuses = [row["status"] for row in csv.DictReader(handle)]
        self.assertEqual(
            statuses,
            ["skipped-deleted", "skipped-offline", "skipped-missing-name"],
        )

    def test_interrupted_export_retains_completed_journal_rows(self):
        backup = self._collision_backup()
        output = self.root / "export"
        calls = 0

        def interrupt_second_copy(source, destination, timestamp, dry_run):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated interruption")
            return "a" * 64, "a" * 64

        with mock.patch.object(
            self.app, "copy_with_metadata", side_effect=interrupt_second_copy
        ):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.app.export_assets(arguments(self.library, backup, output))

        partial = output / "manifest.jsonl.partial"
        self.assertTrue(partial.exists())
        self.assertEqual(len(partial.read_text(encoding="utf-8").splitlines()), 1)
        self.assertFalse((output / "manifest.jsonl").exists())

    def test_unused_unsafe_sidecar_path_does_not_block_original(self):
        source = self.library / "upload/one.bin"
        source.write_bytes(b"one")
        backup = write_backup(
            self.root / "backup.sql.gz",
            [
                {
                    "id": "asset-1",
                    "originalPath": "upload/one.bin",
                    "originalFileName": "one.jpg",
                    "sidecarPath": "../../outside.xmp",
                }
            ],
        )
        output = self.root / "export"

        self.assertEqual(
            self.app.export_assets(arguments(self.library, backup, output)), 0
        )
        self.assertEqual((output / "one.jpg").read_bytes(), b"one")

    def test_asset_without_id_is_rejected(self):
        backup = write_backup(
            self.root / "backup.sql.gz",
            [
                {
                    "id": None,
                    "originalPath": "upload/one.bin",
                    "originalFileName": "one.jpg",
                }
            ],
        )

        with self.assertRaisesRegex(self.app.BackupFormatError, "row 1 has no id"):
            self.app.export_assets(
                arguments(self.library, backup, self.root / "export")
            )

    def test_sidecar_directory_is_rejected(self):
        (self.library / "upload/one.bin").write_bytes(b"one")
        (self.library / "upload/not-a-file").mkdir()
        backup = write_backup(
            self.root / "backup.sql.gz",
            [
                {
                    "id": "asset-1",
                    "originalPath": "upload/one.bin",
                    "originalFileName": "one.jpg",
                    "sidecarPath": "upload/not-a-file",
                }
            ],
        )

        with self.assertRaisesRegex(
            self.app.UnsafePathError, "Sidecar source is not a regular file"
        ):
            self.app.export_assets(
                arguments(
                    self.library,
                    backup,
                    self.root / "export",
                    copy_sidecars=True,
                )
            )


if __name__ == "__main__":
    unittest.main()
