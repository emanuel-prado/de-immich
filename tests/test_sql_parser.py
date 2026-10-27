import gzip
import tempfile
import unittest
from pathlib import Path

from helpers import write_backup
from load_app import load_app


class SqlParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_copy_escaping_and_nulls(self):
        backup = write_backup(
            self.root / "backup.sql.gz",
            [{"id": "asset-1", "originalPath": "upload/one.jpg", "originalFileName": "tab\tline\nslash\\.jpg"}],
        )
        row = next(self.app.iter_copy_rows(backup, "asset"))
        self.assertEqual(row["originalFileName"], "tab\tline\nslash\\.jpg")
        self.assertIsNone(row["deletedAt"])

    def test_postgres_octal_and_hexadecimal_escapes(self):
        self.assertEqual(
            self.app.postgres_copy_unescape(r"photo\056jpg-\x41"),
            "photo.jpg-A",
        )

    def test_non_octal_digit_is_not_consumed_as_octal(self):
        self.assertEqual(self.app.postgres_copy_unescape(r"value\8"), "value8")

    def test_missing_copy_section_is_rejected(self):
        backup = self.root / "empty.sql.gz"
        with gzip.open(backup, "wt", encoding="utf-8") as handle:
            handle.write("-- no asset data\n")
        with self.assertRaisesRegex(self.app.BackupFormatError, "no COPY public.asset"):
            list(self.app.iter_copy_rows(backup, "asset"))

    def test_missing_required_column_is_rejected(self):
        backup = self.root / "missing-column.sql.gz"
        with gzip.open(backup, "wt", encoding="utf-8") as handle:
            handle.write('COPY public.asset ("id", "originalPath") FROM stdin;\n')
            handle.write("id-1\tupload/a.jpg\n\\.\n")
        with self.assertRaisesRegex(self.app.BackupFormatError, "originalFileName"):
            list(self.app.iter_copy_rows(backup, "asset"))

    def test_wrong_field_count_is_rejected(self):
        backup = self.root / "malformed.sql.gz"
        with gzip.open(backup, "wt", encoding="utf-8") as handle:
            handle.write('COPY public.asset ("id", "originalPath", "originalFileName") FROM stdin;\n')
            handle.write("only-one-field\n\\.\n")
        with self.assertRaisesRegex(self.app.BackupFormatError, "1 fields; expected 3"):
            list(self.app.iter_copy_rows(backup, "asset"))


if __name__ == "__main__":
    unittest.main()
