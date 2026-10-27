# Recovery report schema 1.0

Each export writes the same per-asset records to `manifest.csv` and
`manifest.jsonl`. The JSON Lines representation is the canonical machine-readable
report; the CSV is provided for spreadsheet review.

This is a project-specific recovery report. It is not a PREMIS representation,
a BagIt manifest, or evidence that an export is an archival information package.

## Recovery and fixity fields

| Field | Meaning |
| --- | --- |
| `reportSchemaVersion` | Version of this report contract, currently `1.0` |
| `toolVersion` | Version of de-immich that performed the recovery |
| `recoveryTimestamp` | UTC timestamp shared by all records in one run |
| `status` | Per-record outcome listed below |
| `fixityAlgorithm` | `sha256` when checksums were measured; otherwise null |
| `sourceSha256` | SHA-256 of the source bytes read during the copy |
| `exportedSha256` | SHA-256 independently read from the published export |
| `verification` | `verified`, `failed`, or `not-performed` |

The source checksum represents the byte stream actually read. It does not prove
the source was authentic before recovery, nor does it replace a checksum created
when the source was first acquired.

## Outcomes

- `exported`: copied and source/output SHA-256 values matched.
- `verification-failed`: copied, but the independently read output did not match.
- `planned`: included in a dry run; no bytes were copied or hashed.
- `missing-source`: the database record resolved to a path that was absent.
- `skipped-deleted`: omitted because Immich marked the asset deleted.
- `skipped-offline`: omitted because Immich marked the asset offline.
- `skipped-missing-name`: omitted because no original filename was available.

Other manifest fields retain Immich source names where possible. An `exif_`
prefix distinguishes fields originating in `asset_exif`. Null means the source
did not supply a value; de-immich does not fabricate descriptive metadata.

## Interrupted operations

During export, completed outcomes are appended and synced to
`manifest.jsonl.partial`. On successful completion it becomes `manifest.jsonl`.
If the process stops early, the partial file remains for inspection. It is an
audit trail, not a resume instruction: the current release deliberately refuses
to reuse an output containing a report or partial journal.

## Later verification

Re-read every exported file that has a recorded checksum:

```bash
python3 de-immich.py --verify-manifest /path/to/export/manifest.jsonl
```

The command returns exit status `2` if a file is missing or its SHA-256 differs,
and `1` for an invalid/unreadable report. Rows without an exported path and
checksum are not verification candidates.

## Privacy and portability

Reports currently contain resolved absolute source and destination paths, and
may contain owner, device, location, and other personal metadata copied from the
backup. Treat them as sensitive and redact them before sharing. Absolute paths
also make the report environment-specific; a future schema may add relative
package paths without removing the original source references needed for local
recovery auditing.

