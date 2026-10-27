# de-immich

**Recover your media. Preserve its history.**

A small, standalone Python CLI for recovering original media from an **Immich database backup and its corresponding storage directory**. It reconstructs human-readable filenames, organizes files by date, and exports metadata inventories so the result remains understandable outside Immich.

This project is also a practical exploration of **digital preservation**, **Digital Asset Management (DAM)**, and data portability: recovering digital objects is only one part of making them useful in the future.

> **Project status: experimental recovery utility.** Use copies of your backups and media, run a small trial first, and validate results independently. This is not a certified archival system or a substitute for verified backups.

## Why this exists

A collection of photos and videos is more than a pile of files. Without its original names, dates, source relationships, and descriptive metadata, recovered media can lose much of its context.

Immich stores useful information in its database. `de-immich` helps bring that information back together with the original files, without requiring a running Immich or PostgreSQL instance.

**You need both:** an Immich `.sql.gz` database dump **and** the underlying media files. The database dump does not contain the photo/video contents.

## What works today

| Capability | Current behavior |
| --- | --- |
| Recover original media | Reads Immich database COPY records and resolves stored media paths |
| Retain filenames | Restores original filenames; resolves existing filename collisions |
| Organize by date | Exports into `YYYY/MM` based on available EXIF and asset timestamps; `--flat` is available |
| Preserve useful metadata | Exports CSV and JSONL inventories, with asset fields and available EXIF records |
| Preserve related files | Optionally copies Immich-tracked sidecars and writes per-asset JSON metadata |
| Review before copying | Provides `--dry-run` and `--limit` |
| Handle incomplete collections | Reports missing original files and summarizes skipped assets |

**Not yet implemented:** file checksums/fixity verification, resumable exports, complete preservation-event logs, schema auto-detection, BagIt packages, and standards-compliant PREMIS records. These are design goals, not advertised features. See [preservation notes](docs/preservation-notes.md) and the [roadmap](docs/roadmap.md).

## Quick start

Requirements: **Python 3.9+**, an Immich storage directory, and a matching `.sql.gz` database backup. The script uses the Python standard library.

```bash
git clone https://github.com/emanuel-prado/de-immich.git
cd de-immich

# Inspect a small sample before exporting the collection.
python3 de-immich.py \
  --library-root /path/to/immich/storage \
  --backup /path/to/immich/storage/backups/backup.sql.gz \
  --output /path/to/recovered-media \
  --limit 100 \
  --dry-run

# Export after reviewing your paths and backups.
python3 de-immich.py \
  --library-root /path/to/immich/storage \
  --backup /path/to/immich/storage/backups/backup.sql.gz \
  --output /path/to/recovered-media
```

If you run the script **from the Immich storage directory**, you may omit `--library-root` and `--backup`; it selects the last backup by sorted filename from `backups/*.sql.gz`. Prefer specifying the backup explicitly if you have several versions.

By default, files are exported in a layout like this:

```text
recovered-media/
├── 2025/
│   ├── 02/
│   │   └── IMG_0001.jpg
│   └── 07/
│       └── holiday.mp4
├── unknown-date/
├── manifest.csv
└── manifest.jsonl
```

*Illustrative layout and filenames.*

### Additional options

```bash
# Export to one directory instead of YYYY/MM.
python3 de-immich.py --flat

# Copy tracked sidecar files and write metadata next to each asset.
python3 de-immich.py --copy-sidecars --write-json-sidecars

# Include assets normally skipped by Immich status.
python3 de-immich.py --include-deleted --include-offline

# View all arguments.
python3 de-immich.py --help
```

## What the inventory preserves

The exported `manifest.csv` and `manifest.jsonl` contain useful context about each successfully exported asset and missing-source record, including:

- **Identity:** Immich asset ID, original filename, media type.
- **Provenance clues:** Original Immich path, resolved local source path, export path, owner/library/device references when present.
- **Dates and description:** Asset timestamps plus EXIF fields included in the database backup.
- **Relationships:** Sidecar paths, live photo, duplicate, and stack references when present.
- **Recovery outcome:** The export status (`exported` or `missing-source`).

These are **source-system metadata and recovery inventories**, not a formal preservation metadata package. Skipped deleted/offline/unnamed rows are currently counted in the summary but are **not** represented individually in the exported manifests. The roadmap includes making those outcomes auditable.

Read [Preservation notes](docs/preservation-notes.md) for how these fields relate to DAM and archival concepts.

## Compatibility and limitations

- Currently parses `COPY public.asset` and `COPY public.asset_exif` sections in plain-text Immich PostgreSQL dumps compressed as `.sql.gz`. Other schemas and dump styles are **not verified**.
- Compatibility with specific Immich releases is **not yet tested or guaranteed**. Schema changes may require adaptations.
- Existing name-collision handling is not a safe resume mechanism. Re-running into the same output directory can create duplicate exports.
- A dry run does **not** reserve destinations, so collision filenames in its preview may differ from a real export.
- Export files are not currently checksum-verified; do not treat a successful copy as proof of bit-level integrity.
- Path handling and filesystem edge cases need stronger safety validation before untrusted backups or storage trees should be used.
- The exporter is designed to read source media rather than modify it, but you should still **work from copies** and keep your original backups untouched.
- Inventories can contain sensitive paths, device IDs, owner IDs, dates, and location-related EXIF. Review or redact before sharing.

## Why these design choices?

The current tool deliberately avoids requiring a database service or a web application. This keeps the recovery path simple, portable, and inspectable.

The next preservation-oriented steps prioritize **fixity**, **provenance**, **repeatability**, and **portable metadata**, rather than building a general-purpose DAM interface.

- [Preservation concepts and current mappings](docs/preservation-notes.md)
- [Prioritized development roadmap](docs/roadmap.md)
- [Engineering case study for a professional portfolio](docs/case-study.md)

## License and acknowledgments

MIT license. Independent project; not affiliated with or endorsed by Immich.

Immich is an excellent self-hosted photo-management solution. `de-immich` explores a complementary question: *if the application disappears, can I still understand and recover my digital collection?*
