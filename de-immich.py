#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import shutil as shutil_mod
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

COPY_PREFIXES = {
    "asset": "COPY public.asset ",
    "asset_exif": "COPY public.asset_exif ",
}

REQUIRED_COLUMNS = {
    "asset": {"id", "originalPath", "originalFileName"},
    "asset_exif": {"assetId"},
}


class BackupFormatError(ValueError):
    """Raised when a dump cannot be safely interpreted."""


class UnsafePathError(ValueError):
    """Raised when a database path escapes the configured storage root."""


@dataclass
class ExportStats:
    exported: int = 0
    missing: int = 0
    skipped_deleted: int = 0
    skipped_offline: int = 0
    skipped_missing_name: int = 0
    sidecars_exported: int = 0


class ProgressReporter:
    def __init__(self, total: int, enabled: bool) -> None:
        self.total = total
        self.enabled = enabled
        self.last_len = 0
        self.last_reported = -1
        self.is_tty = sys.stderr.isatty()

    def update(self, processed: int, stats: ExportStats) -> None:
        if not self.enabled or self.total <= 0:
            return
        if self.is_tty:
            self._render_tty(processed, stats)
            return
        if processed == self.last_reported:
            return
        if processed != self.total and processed % 250 != 0:
            return
        self.last_reported = processed
        percent = (processed / self.total) * 100
        print(
            (
                f"Progress: {processed}/{self.total} ({percent:5.1f}%) "
                f"exported={stats.exported} missing={stats.missing} "
                f"deleted={stats.skipped_deleted} offline={stats.skipped_offline}"
            ),
            file=sys.stderr,
        )

    def finish(self, processed: int, stats: ExportStats) -> None:
        if not self.enabled or self.total <= 0:
            return
        if self.is_tty:
            self._render_tty(processed, stats)
            print(file=sys.stderr)
        else:
            self.update(processed, stats)

    def _render_tty(self, processed: int, stats: ExportStats) -> None:
        width = shutil_mod.get_terminal_size((100, 20)).columns
        bar_width = min(24, max(10, width // 5))
        filled = int(bar_width * processed / self.total) if self.total else 0
        bar = "#" * filled + "-" * (bar_width - filled)
        percent = (processed / self.total) * 100 if self.total else 0
        line = (
            f"[{bar}] {processed}/{self.total} {percent:5.1f}% "
            f"ok={stats.exported} miss={stats.missing} "
            f"del={stats.skipped_deleted} off={stats.skipped_offline}"
        )
        if len(line) > width - 1:
            line = line[: width - 1]
        pad = " " * max(0, self.last_len - len(line))
        print(f"\r{line}{pad}", end="", file=sys.stderr, flush=True)
        self.last_len = len(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export original media from an Immich library using the SQL backups. "
            "Restores original filenames, preserves timestamps, and writes manifests."
        )
    )
    parser.add_argument(
        "--library-root",
        type=Path,
        default=Path.cwd(),
        help="Root of the Immich storage directory. Default: current directory.",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help="Path to a specific .sql.gz backup. Default: newest backup in <library-root>/backups.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "immich-export",
        help="Destination directory for restored media. Default: ./immich-export",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Export into a single directory instead of YYYY/MM subfolders.",
    )
    parser.add_argument(
        "--include-deleted",
        action="store_true",
        help="Include rows marked deleted in Immich.",
    )
    parser.add_argument(
        "--include-offline",
        action="store_true",
        help="Include rows marked offline in Immich.",
    )
    parser.add_argument(
        "--copy-sidecars",
        action="store_true",
        help="Copy DB-tracked sidecar files next to exported media when available.",
    )
    parser.add_argument(
        "--write-json-sidecars",
        action="store_true",
        help="Write one JSON metadata sidecar per exported asset.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most N assets. Useful for testing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without copying files.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress output.",
    )
    return parser.parse_args()


def latest_backup(backups_dir: Path) -> Path:
    candidates = sorted(backups_dir.glob("*.sql.gz"))
    if not candidates:
        raise FileNotFoundError(f"No .sql.gz backups found in {backups_dir}")
    return candidates[-1]


def normalize_header_columns(copy_line: str) -> List[str]:
    try:
        column_text = copy_line.split("(", 1)[1].split(")", 1)[0]
    except IndexError as exc:
        raise BackupFormatError(f"Malformed COPY header: {copy_line.rstrip()}") from exc
    columns = [column.strip().strip('"') for column in column_text.split(",")]
    if not columns or any(not column for column in columns):
        raise BackupFormatError(f"Malformed COPY header: {copy_line.rstrip()}")
    return columns


def postgres_copy_unescape(value: str) -> str:
    if "\\" not in value:
        return value

    out: List[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue

        i += 1
        if i >= len(value):
            out.append("\\")
            break

        esc = value[i]
        i += 1
        mapping = {
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "v": "\v",
            "\\": "\\",
        }
        if esc in mapping:
            out.append(mapping[esc])
            continue

        if esc.isdigit():
            octal = esc
            for _ in range(2):
                if i < len(value) and value[i].isdigit():
                    octal += value[i]
                    i += 1
                else:
                    break
            out.append(chr(int(octal, 8)))
            continue

        out.append(esc)

    return "".join(out)


def parse_copy_row(line: str, columns: List[str]) -> Dict[str, Optional[str]]:
    parts = line.rstrip("\n").split("\t")
    if len(parts) != len(columns):
        raise BackupFormatError(
            f"COPY row has {len(parts)} fields; expected {len(columns)}"
        )
    row: Dict[str, Optional[str]] = {}
    for key, value in zip(columns, parts):
        if value == r"\N":
            row[key] = None
        else:
            row[key] = postgres_copy_unescape(value)
    return row


def iter_copy_rows(
    sql_gz_path: Path, table_name: str
) -> Iterator[Dict[str, Optional[str]]]:
    prefix = COPY_PREFIXES[table_name]
    with gzip.open(sql_gz_path, "rt", encoding="utf-8") as handle:
        columns: Optional[List[str]] = None
        in_copy = False
        for line in handle:
            if not in_copy:
                if line.startswith(prefix):
                    columns = normalize_header_columns(line)
                    missing = REQUIRED_COLUMNS[table_name].difference(columns)
                    if missing:
                        names = ", ".join(sorted(missing))
                        raise BackupFormatError(
                            f"COPY public.{table_name} is missing required columns: {names}"
                        )
                    in_copy = True
                continue
            if line.rstrip("\n") == r"\.":
                return
            if columns is None:
                raise RuntimeError(f"Failed to parse columns for {table_name}")
            yield parse_copy_row(line, columns)
        if in_copy:
            raise BackupFormatError(
                f"COPY public.{table_name} has no terminating \\. marker"
            )
        raise BackupFormatError(f"Backup has no COPY public.{table_name} section")


def count_copy_rows(sql_gz_path: Path, table_name: str) -> int:
    return sum(1 for _ in iter_copy_rows(sql_gz_path, table_name))


def parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def choose_media_timestamp(
    asset: Dict[str, Optional[str]], exif: Dict[str, Optional[str]]
) -> Optional[datetime]:
    for key in ("dateTimeOriginal", "modifyDate"):
        dt = parse_timestamp(exif.get(key))
        if dt:
            return dt
    for key in ("localDateTime", "fileCreatedAt", "fileModifiedAt", "createdAt"):
        dt = parse_timestamp(asset.get(key))
        if dt:
            return dt
    return None


def sanitize_filename(name: str) -> str:
    clean = "".join(
        "" if char == "\x00" else "_" if char in "/\\" or ord(char) < 32 else char
        for char in name
    )
    clean = clean.strip()
    return clean if clean not in {"", ".", ".."} else "unnamed"


def split_name(filename: str) -> Tuple[str, str]:
    path = Path(filename)
    suffix = "".join(path.suffixes)
    stem = filename[: -len(suffix)] if suffix else filename
    return stem, suffix


def export_subdir(
    asset: Dict[str, Optional[str]], exif: Dict[str, Optional[str]], flat: bool
) -> Path:
    if flat:
        return Path(".")
    dt = choose_media_timestamp(asset, exif)
    if not dt:
        return Path("unknown-date")
    return Path(f"{dt.year:04d}") / f"{dt.month:02d}"


def resolve_storage_path(library_root: Path, db_path: Optional[str]) -> Optional[Path]:
    if not db_path:
        return None

    root = library_root.resolve()
    path = Path(db_path)
    if path.is_absolute():
        parts = path.parts
        for candidate in (
            "upload",
            "library",
            "thumbs",
            "encoded-video",
            "profile",
            "backups",
        ):
            indexes = [idx for idx, part in enumerate(parts) if part == candidate]
            if indexes:
                rel = Path(*parts[indexes[-1] :])
                break
        else:
            raise UnsafePathError(
                f"Absolute source path is not in a recognized Immich storage directory: {db_path}"
            )
    else:
        rel = path

    candidate = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"Source path contains a symbolic link: {db_path}")

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(f"Source path escapes library root: {db_path}") from exc

    return candidate


def ensure_unique_destination(dest: Path, asset_id: str, reserved: Set[Path]) -> Path:
    if not dest.exists() and dest not in reserved:
        reserved.add(dest)
        return dest

    stem, suffix = split_name(dest.name)
    parent = dest.parent
    candidate = parent / f"{stem}__{asset_id[:8]}{suffix}"
    if not candidate.exists() and candidate not in reserved:
        reserved.add(candidate)
        return candidate

    index = 2
    while True:
        candidate = parent / f"{stem}__{asset_id[:8]}_{index}{suffix}"
        if not candidate.exists() and candidate not in reserved:
            reserved.add(candidate)
            return candidate
        index += 1


def copy_with_metadata(
    src: Path, dest: Path, timestamp: Optional[datetime], dry_run: bool
) -> None:
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".de-immich-", suffix=".tmp", dir=dest.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, src.open("rb") as source:
            shutil.copyfileobj(source, output)
        shutil.copystat(src, temporary)
        if timestamp:
            ts = timestamp.timestamp()
            os.utime(temporary, (ts, ts))
        try:
            os.link(temporary, dest)
        except FileExistsError as exc:
            raise FileExistsError(f"Refusing to overwrite existing export: {dest}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, data: Dict[str, object], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_exif_map(sql_gz_path: Path) -> Dict[str, Dict[str, Optional[str]]]:
    exif_map: Dict[str, Dict[str, Optional[str]]] = {}
    for row in iter_copy_rows(sql_gz_path, "asset_exif"):
        asset_id = row.get("assetId")
        if asset_id:
            exif_map[asset_id] = row
    return exif_map


def manifest_row(
    asset: Dict[str, Optional[str]],
    exif: Dict[str, Optional[str]],
    source_path: Optional[Path],
    exported_path: Optional[Path],
    sidecar_source: Optional[Path],
    sidecar_exported: Optional[Path],
    status: str,
) -> Dict[str, object]:
    data: Dict[str, object] = {
        "status": status,
        "assetId": asset.get("id"),
        "type": asset.get("type"),
        "originalFileName": asset.get("originalFileName"),
        "originalPath": asset.get("originalPath"),
        "resolvedSourcePath": str(source_path) if source_path else None,
        "exportedPath": str(exported_path) if exported_path else None,
        "sidecarPath": asset.get("sidecarPath"),
        "resolvedSidecarPath": str(sidecar_source) if sidecar_source else None,
        "exportedSidecarPath": str(sidecar_exported) if sidecar_exported else None,
        "encodedVideoPath": asset.get("encodedVideoPath"),
        "fileCreatedAt": asset.get("fileCreatedAt"),
        "fileModifiedAt": asset.get("fileModifiedAt"),
        "localDateTime": asset.get("localDateTime"),
        "createdAt": asset.get("createdAt"),
        "updatedAt": asset.get("updatedAt"),
        "deletedAt": asset.get("deletedAt"),
        "isFavorite": asset.get("isFavorite"),
        "isOffline": asset.get("isOffline"),
        "isExternal": asset.get("isExternal"),
        "ownerId": asset.get("ownerId"),
        "libraryId": asset.get("libraryId"),
        "deviceId": asset.get("deviceId"),
        "deviceAssetId": asset.get("deviceAssetId"),
        "livePhotoVideoId": asset.get("livePhotoVideoId"),
        "duplicateId": asset.get("duplicateId"),
        "stackId": asset.get("stackId"),
        "visibility": asset.get("visibility"),
        "statusField": asset.get("status"),
    }
    for key, value in exif.items():
        data[f"exif_{key}"] = value
    return data


def export_assets(args: argparse.Namespace) -> int:
    library_root = args.library_root.resolve()
    backup_path = (
        args.backup.resolve()
        if args.backup
        else latest_backup(library_root / "backups")
    )
    output_dir = args.output.resolve()

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    exif_map = load_exif_map(backup_path)
    total_assets = count_copy_rows(backup_path, "asset")
    stats = ExportStats()
    progress = ProgressReporter(total_assets, enabled=not args.no_progress)
    manifest_csv_rows: List[Dict[str, object]] = []
    manifest_jsonl_rows: List[Dict[str, object]] = []
    reserved_destinations: Set[Path] = set()

    if not args.dry_run:
        existing_manifests = [
            path
            for path in (output_dir / "manifest.csv", output_dir / "manifest.jsonl")
            if path.exists()
        ]
        if existing_manifests:
            names = ", ".join(str(path) for path in existing_manifests)
            raise FileExistsError(f"Refusing to overwrite existing manifest: {names}")

    processed = 0
    for asset in iter_copy_rows(backup_path, "asset"):
        if args.limit is not None and processed >= args.limit:
            break
        processed += 1

        asset_id = asset.get("id")
        if not asset_id:
            continue

        if asset.get("deletedAt") and not args.include_deleted:
            stats.skipped_deleted += 1
            progress.update(processed, stats)
            continue

        if asset.get("isOffline") == "t" and not args.include_offline:
            stats.skipped_offline += 1
            progress.update(processed, stats)
            continue

        original_name = asset.get("originalFileName")
        if not original_name:
            stats.skipped_missing_name += 1
            progress.update(processed, stats)
            continue

        exif = exif_map.get(asset_id, {})
        source_path = resolve_storage_path(library_root, asset.get("originalPath"))
        sidecar_source = resolve_storage_path(library_root, asset.get("sidecarPath"))

        if not source_path or not source_path.exists():
            stats.missing += 1
            row = manifest_row(
                asset, exif, source_path, None, sidecar_source, None, "missing-source"
            )
            manifest_csv_rows.append(row)
            manifest_jsonl_rows.append(row)
            progress.update(processed, stats)
            continue
        if not source_path.is_file():
            raise UnsafePathError(f"Source is not a regular file: {source_path}")

        subdir = export_subdir(asset, exif, args.flat)
        desired_dest = output_dir / subdir / sanitize_filename(original_name)
        final_dest = ensure_unique_destination(
            desired_dest, asset_id, reserved_destinations
        )
        media_timestamp = choose_media_timestamp(asset, exif)

        copy_with_metadata(source_path, final_dest, media_timestamp, args.dry_run)

        sidecar_dest = None
        if args.copy_sidecars and sidecar_source and sidecar_source.exists():
            sidecar_name = sanitize_filename(sidecar_source.name)
            sidecar_dest = ensure_unique_destination(
                final_dest.parent / sidecar_name, asset_id, reserved_destinations
            )
            copy_with_metadata(
                sidecar_source, sidecar_dest, media_timestamp, args.dry_run
            )
            stats.sidecars_exported += 1

        row = manifest_row(
            asset,
            exif,
            source_path,
            final_dest,
            sidecar_source,
            sidecar_dest,
            "exported",
        )
        manifest_csv_rows.append(row)
        manifest_jsonl_rows.append(row)

        if args.write_json_sidecars:
            json_dest = final_dest.with_suffix(final_dest.suffix + ".immich.json")
            if json_dest.exists() or json_dest in reserved_destinations:
                raise FileExistsError(
                    f"Refusing to overwrite existing metadata sidecar: {json_dest}"
                )
            reserved_destinations.add(json_dest)
            write_json(json_dest, row, args.dry_run)

        stats.exported += 1
        progress.update(processed, stats)

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "manifest.csv"
        jsonl_path = output_dir / "manifest.jsonl"

        fieldnames = sorted({key for row in manifest_csv_rows for key in row.keys()})
        with csv_path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest_csv_rows)

        with jsonl_path.open("x", encoding="utf-8") as handle:
            for row in manifest_jsonl_rows:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")

    print(f"Library root: {library_root}")
    print(f"Backup: {backup_path}")
    print(f"Output: {output_dir}")
    print(f"Assets exported: {stats.exported}")
    print(f"Sources missing: {stats.missing}")
    print(f"Skipped deleted: {stats.skipped_deleted}")
    print(f"Skipped offline: {stats.skipped_offline}")
    print(f"Skipped missing name: {stats.skipped_missing_name}")
    print(f"Sidecars exported: {stats.sidecars_exported}")
    if args.dry_run:
        print("Dry-run only: no files were copied and no manifests were written.")
    progress.finish(processed, stats)

    return 0


def main() -> int:
    args = parse_args()
    try:
        return export_assets(args)
    except BrokenPipeError:
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
