import tempfile
import unittest
from pathlib import Path

from load_app import load_app


class PathAndCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_relative_source_path_cannot_escape_root(self):
        library = self.root / "library"
        library.mkdir()
        with self.assertRaisesRegex(self.app.UnsafePathError, "escapes library root"):
            self.app.resolve_storage_path(library, "../private.jpg")

    def test_unrecognized_absolute_source_path_is_rejected(self):
        with self.assertRaisesRegex(self.app.UnsafePathError, "not in a recognized"):
            self.app.resolve_storage_path(self.root, "/etc/passwd")

    def test_source_symlink_is_rejected(self):
        library = self.root / "library"
        upload = library / "upload"
        upload.mkdir(parents=True)
        target = self.root / "private.jpg"
        target.write_bytes(b"private")
        (upload / "link.jpg").symlink_to(target)
        with self.assertRaisesRegex(self.app.UnsafePathError, "symbolic link"):
            self.app.resolve_storage_path(library, "upload/link.jpg")

    def test_absolute_immich_path_maps_to_storage_root(self):
        self.assertEqual(
            self.app.resolve_storage_path(self.root, "/usr/src/app/upload/library/user/photo.jpg"),
            self.root / "upload/library/user/photo.jpg",
        )

    def test_collision_reservations_match_planned_order(self):
        desired = self.root / "photo.jpg"
        reserved = set()
        first = self.app.ensure_unique_destination(desired, "aaaaaaaa-one", reserved)
        second = self.app.ensure_unique_destination(desired, "bbbbbbbb-two", reserved)
        third = self.app.ensure_unique_destination(desired, "bbbbbbbb-three", reserved)
        self.assertEqual(first, desired)
        self.assertEqual(second, self.root / "photo__bbbbbbbb.jpg")
        self.assertEqual(third, self.root / "photo__bbbbbbbb_2.jpg")
        self.assertEqual(len(reserved), 3)

    def test_filename_sanitization(self):
        cases = (("../photo.jpg", ".._photo.jpg"), (r"folder\photo.jpg", "folder_photo.jpg"), ("\x00", "unnamed"))
        for unsafe, safe in cases:
            with self.subTest(unsafe=unsafe):
                self.assertEqual(self.app.sanitize_filename(unsafe), safe)


if __name__ == "__main__":
    unittest.main()

