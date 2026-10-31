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
        token_two = self.app.hashlib.sha256(b"bbbbbbbb-two").hexdigest()[:12]
        token_three = self.app.hashlib.sha256(b"bbbbbbbb-three").hexdigest()[:12]
        self.assertEqual(second, self.root / f"photo__{token_two}.jpg")
        self.assertEqual(third, self.root / f"photo__{token_three}.jpg")
        self.assertEqual(len(reserved), 3)

    def test_collision_asset_id_cannot_create_path_components(self):
        desired = self.root / "export" / "photo.jpg"
        reserved = {desired}

        collision = self.app.ensure_unique_destination(
            desired, "../../outside", reserved
        )

        self.assertEqual(collision.parent, desired.parent)
        self.assertNotIn("..", collision.parts)

    def test_symlinked_output_parent_is_rejected(self):
        output = self.root / "export"
        outside = self.root / "outside"
        output.mkdir()
        outside.mkdir()
        (output / "2026").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(self.app.UnsafePathError, "symbolic link"):
            self.app.validate_destination(output, output / "2026/01/photo.jpg")

    def test_dangling_destination_symlink_is_treated_as_collision(self):
        desired = self.root / "photo.jpg"
        desired.symlink_to(self.root / "missing.jpg")

        actual = self.app.ensure_unique_destination(desired, "asset-1", set())

        token = self.app.hashlib.sha256(b"asset-1").hexdigest()[:12]
        self.assertEqual(actual, self.root / f"photo__{token}.jpg")

    def test_output_must_not_overlap_source_library(self):
        library = self.root / "library"
        library.mkdir()

        for output in (library, library / "export", self.root):
            with self.subTest(output=output):
                with self.assertRaisesRegex(
                    self.app.UnsafePathError, "overlaps the source library"
                ):
                    self.app.ensure_separate_trees(library, output)

    def test_long_filename_is_bounded_and_keeps_extension(self):
        original = "é" * 200 + ".jpg"

        sanitized = self.app.sanitize_filename(original)

        self.assertLessEqual(
            len(sanitized.encode("utf-8")), self.app.MAX_EXPORT_FILENAME_BYTES
        )
        self.assertTrue(sanitized.endswith(".jpg"))
        self.assertEqual(sanitized, self.app.sanitize_filename(original))

    def test_limit_must_be_positive(self):
        self.assertEqual(self.app.positive_int("2"), 2)
        with self.assertRaises(self.app.argparse.ArgumentTypeError):
            self.app.positive_int("0")

    def test_filename_sanitization(self):
        cases = (("../photo.jpg", ".._photo.jpg"), (r"folder\photo.jpg", "folder_photo.jpg"), ("\x00", "unnamed"))
        for unsafe, safe in cases:
            with self.subTest(unsafe=unsafe):
                self.assertEqual(self.app.sanitize_filename(unsafe), safe)


if __name__ == "__main__":
    unittest.main()
