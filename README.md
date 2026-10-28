# de-immich

**Recover your media. Preserve its history.**

`de-immich` is a small Python CLI that reconnects original media with filenames
and metadata from an Immich database backup. It works directly from a compressed
SQL dump and storage copy; it does not require a running Immich or PostgreSQL.

> **Project status: experimental recovery utility.** Work from copies, start with
> `--dry-run`, and independently validate important recoveries. This is not an
> archival repository, certified preservation system, or replacement for tested
> backups.

## Why this exists

An Immich database backup contains metadata and file references, not the photo or
video bytes. A storage backup contains those bytes, but application-managed names
and paths can make a manual recovery difficult. You need a corresponding copy of
**both** the `.sql.gz` database dump and the Immich storage tree.

The tool reads PostgreSQL `COPY` records, resolves each original asset under the
configured storage root, assigns a dated destination, copies without overwriting,
and produces inspectable CSV and JSONL recovery reports.

## What works today

| Capability | Current behavior |
| --- | --- |
| Original recovery | Copies `asset.originalPath` using `originalFileName` |
| Safe planning | Rejects overlapping source/output trees, traversal, symlinked path components, malformed rows, and missing required schema |
| Collisions | Reserves tool-owned and asset names, bounds long filenames, and uses hashed suffixes; dry-run and export use the same plan against the same starting state |
| Fixity | Records source/output SHA-256 and verifies the published copy |
| Later verification | Re-reads exports and rejects corruption, absence, symlink substitution, unsupported reports, and previously recorded copy failures |
| Auditability | Records exported, missing, and skipped outcomes; retains a partial JSONL journal after interruption |
| Metadata | Retains asset fields and available `asset_exif` fields without inventing values |
| Related files | Supports historical dumps that contain `asset.sidecarPath`; can write per-asset JSON sidecars |

Not implemented: safe resume, explicit external-library path mappings, current
`asset_file` sidecar recovery, schema/version auto-detection, BagIt packages, or a
PREMIS representation. These are not implied by the preservation terminology.

## Quick start

Requirements: Python 3.9+, a matching Immich storage copy, and a plain-text SQL
dump compressed as `.sql.gz`. Runtime dependencies: none beyond Python.

```bash
git clone https://github.com/emanuel-prado/de-immich.git
cd de-immich

# Inspect a small sample first.
python3 de-immich.py \
  --library-root /path/to/immich/storage \
  --backup /path/to/immich/storage/backups/backup.sql.gz \
  --output /path/to/recovered-media \
  --limit 100 \
  --dry-run

# Export after reviewing the paths.
python3 de-immich.py \
  --library-root /path/to/immich/storage \
  --backup /path/to/immich/storage/backups/backup.sql.gz \
  --output /path/to/recovered-media
```

When run from the Immich storage root, `--library-root` and `--backup` may be
omitted. `--output` must still name a separate tree, not the storage root or one
of its descendants. The script selects the last filename in sorted
`backups/*.sql.gz`; pass `--backup` explicitly when that convention is not
reliable for your files.

```text
recovered-media/
├── 2025/
│   └── 02/
│       └── IMG_0001.jpg
├── unknown-date/
├── manifest.csv
└── manifest.jsonl
```

Additional operations:

```bash
# Put assets in one directory.
python3 de-immich.py --flat

# Include records normally skipped because of their Immich state.
python3 de-immich.py --include-deleted --include-offline

# Verify every exported asset with a recorded checksum.
python3 de-immich.py --verify-manifest /path/to/recovered-media/manifest.jsonl

# Show every option.
python3 de-immich.py --help
```

## Why trust the result?

- Source paths are contained within the configured root; traversal, source
  symlinks, and non-regular files fail closed.
- Destination parents are checked for containment and symlinks, and untrusted
  asset IDs are represented by bounded hash tokens in collision filenames.
- Tool-owned report paths are reserved before assets are planned. Overlong
  UTF-8 names are deterministically shortened with a hash instead of failing at
  publication time.
- Files are copied to a same-directory temporary file and published without an
  overwrite operation.
- SHA-256 is calculated from bytes read from the source and independently from
  the published destination. A mismatch is recorded and returns exit status 2.
- Each completed outcome is synced to `manifest.jsonl.partial`. The partial file
  remains inspectable if the process stops before final reports are published.
- Synthetic tests exercise SQL escapes/nulls, malformed schemas, paths,
  collisions, malicious IDs, output symlinks, missing files, dry-run planning,
  interruption, corrupt reports, recorded fixity failures, and corruption.

These safeguards have limits. A matching checksum shows that the exported bytes
match the bytes read during recovery; it does not establish that the source was
authentic before the operation. The tool refuses an output containing an existing
or partial manifest rather than treating it as safely resumable.

## Reports and metadata

The reports retain Immich identity, source references, timestamps, relationships,
available EXIF metadata, recovery outcomes, tool/report versions, and fixity
results. Skipped deleted, offline, and unnamed records are represented
individually. Null values remain null; no missing descriptive metadata is
fabricated.

Reports can reveal filesystem paths, owner/device identifiers, dates, and
location-related EXIF. Treat them as sensitive and redact before sharing.

- [Recovery report schema and status definitions](docs/recovery-report.md)
- [Independent technical assessment and upstream evidence](docs/technical-assessment.md)
- [Preservation concepts and design boundaries](docs/preservation-notes.md)
- [Prioritized development roadmap](docs/roadmap.md)
- [Engineering case study](docs/case-study.md)

## Compatibility and limitations

- Input must contain terminated `COPY public.asset` and
  `COPY public.asset_exif` sections with the documented required columns.
- Immich v3.3.5 has been exercised end to end with a database migrated by that
  release and originals uploaded through its API. The test covered PostgreSQL
  18 `pg_dump` output, images, video, Unicode names, collisions, missing files,
  deleted/offline states, fixity, and repeat-run refusal. This is evidence for
  that release and dump shape only, not a promise of compatibility with other
  Immich versions.
- Current Immich v3.3.5 stores related sidecars/derivatives in `asset_file`; the
  script's optional `asset.sidecarPath` behavior applies only to historical dump
  shapes and is not current-version sidecar support.
- Absolute paths are mapped only when they contain a recognized Immich internal
  storage directory. External libraries need an explicit mapping design and are
  currently rejected rather than guessed.
- Source symlinks are rejected even when they point back inside the storage root.
- Filesystem checks prevent unsafe state observed during planning/copying; the
  CLI is not designed to defend against another process concurrently replacing
  path components during the operation.
- EXIF rows and report rows are retained in memory, and the compressed dump is
  read multiple times. No scale/performance claim has been published.
- Sidecars are not currently included in fixity fields.

See the roadmap for measured acceptance criteria rather than promises of
production readiness.

## Development

The complete synthetic suite uses only the Python standard library:

```bash
python3 -m unittest discover -s tests -v
```

## License and acknowledgments

MIT license. This independent project is not affiliated with or endorsed by
Immich. Immich is an excellent self-hosted photo-management project;
`de-immich` addresses the narrower question of intelligible recovery outside the
running application.
