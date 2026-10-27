# de-immich

Look, Immich is awesome. But if you ever end up with a storage backup and a database dump in your hands and just want your original files back with sane names and timestamps, recovery is not exactly the fun part. So I made this.

`de-immich` is a small Python script that reads an Immich `.sql.gz` backup, matches it against the files in your Immich storage directory, and exports your media with:

- original filenames
- preserved timestamps
- optional sidecars
- CSV and JSONL manifests so you can see what was exported and what was missing

It does not need a running PostgreSQL instance. It parses the compressed SQL backup directly.

## What It Exports

The script reads the `asset` and `asset_exif` tables from an Immich backup and restores files from the Immich storage layout under your library root.

By default it:

- finds the newest backup in `<library-root>/backups`
- exports files into `./immich-export`
- groups output by `YYYY/MM` using EXIF or asset timestamps
- skips deleted assets
- skips offline assets
- writes `manifest.csv` and `manifest.jsonl`

## Requirements

- Python 3.9+
- an Immich storage directory available locally
- at least one Immich `.sql.gz` backup in the `backups/` folder, unless you pass `--backup`

## Compatibility

- Not guaranteed for all Immich versions; schema or storage changes may require updates.
- Use `--dry-run` first.

## Usage

Basic usage, from the Immich storage root:

```bash
python3 de-immich.py
```

Specify paths explicitly:

```bash
python3 de-immich.py \
  --library-root /path/to/immich/storage \
  --backup /path/to/immich/storage/backups/your-backup.sql.gz \
  --output /path/to/exported-files
```

Flat export:

```bash
python3 de-immich.py --flat
```

Include assets Immich marked as deleted or offline:

```bash
python3 de-immich.py --include-deleted --include-offline
```

Copy sidecars and write JSON metadata sidecars:

```bash
python3 de-immich.py --copy-sidecars --write-json-sidecars
```

Dry run:

```bash
python3 de-immich.py --dry-run
```

Verify the SHA-256 checksums recorded by a completed export:

```bash
python3 de-immich.py --verify-manifest /path/to/immich-export/manifest.jsonl
```

Test with a small subset:

```bash
python3 de-immich.py --limit 100
```

Note: `--limit` applies to processed asset rows, not guaranteed exported files. If some rows are skipped or missing, the export count may be lower than the limit.

## Output

The script prints a summary at the end, including:

- exported assets
- missing source files
- skipped deleted assets
- skipped offline assets
- skipped rows without an original filename
- exported sidecars

When not in `--dry-run` mode, it also writes:

- `manifest.csv`
- `manifest.jsonl`

These manifests include source paths, exported paths, timestamps, and copied EXIF-related metadata where available.
They also include SHA-256 source/output checksums, verification outcomes, tool and
report versions, and individual skipped/missing outcomes. See the
[recovery report schema](docs/recovery-report.md) for field meanings and limits.

## How Path Resolution Works

Immich stores file references in the database. This script tries to map those references back into your local storage root.

It handles common Immich storage prefixes like:

- `upload`
- `thumbs`
- `encoded-video`
- `profile`
- `backups`

If a referenced source file is missing, the script records that in the manifest instead of failing the whole run.

## License

MIT
