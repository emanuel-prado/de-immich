# Preservation-oriented design notes

`de-immich` is a recovery and preservation-preparation utility. The goal is an
intelligible, verifiable export—not a general DAM, archival repository, OAIS
implementation, or substitute for multiple tested backups.

## Evidence produced today

| Concern | Current evidence | Important limit |
| --- | --- | --- |
| Identification | Immich asset ID, original filename, media type | Source-system IDs are not universal identifiers |
| Descriptive/technical metadata | Asset fields and `exif_*` fields | Source values, not a normalized interchange record |
| Provenance | Original/resolved/export paths, owner/library references, timestamp, tool version | Not a complete chain of custody |
| Relationships | Sidecar, live-photo, duplicate, and stack reference IDs when present | References are retained, not fully reconstructed |
| Recovery outcomes | Exported, missing, skipped, or fixity-failed per asset | Not a complete preservation-event history |
| Fixity | Source/output SHA-256 and later manifest verification for originals and copied sidecars | Copy equivalence, not prior authenticity |
| Portability | CSV and JSONL | Reports contain environment-specific absolute paths |

The source checksum describes the bytes actually read during recovery. Matching
source and output digests demonstrate that publication preserved that byte
stream. They cannot prove when, how, or by whom the source was created, or that it
was unaltered before recovery.

## Standards inform decisions; they are not badges

### PREMIS

The [PREMIS Data Dictionary 3.0](https://www.loc.gov/standards/premis/v3/)
distinguishes Objects, Events, Agents, and Rights. That model usefully prompts
questions about the object processed, action performed, outcome, time, software
agent, and fixity evidence.

The project report is only **PREMIS-informed**. It does not serialize PREMIS,
model Rights, identify external Agents, or express the richer Object/Event
relationships required for a validated representation. Adding PREMIS-shaped
field names without those semantics would make the report less honest.

### BagIt

[BagIt, RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) defines a transfer
package layout, payload manifests, tag files, and validation rules. An ordinary
de-immich export is a working directory, not a bag, and its SHA-256 fields are not
a substitute for that structure.

BagIt is deliberately deferred. If users demonstrate a transfer-packaging need,
an implementation must follow the RFC and pass an independent validator. Merely
adding `manifest-sha256.txt` would not be compliant.

### Dublin Core and metadata crosswalks

No Dublin Core record is emitted. An original filename is not automatically a
trustworthy `dc:title`, an owner UUID is not a `dc:creator`, and file/capture/
database timestamps are not interchangeable `dc:date` values. A future crosswalk
should map only semantically supported source fields, distinguish descriptive,
technical, administrative, and preservation metadata, and cite every source
field. Until then, Immich names plus the `exif_` prefix retain more provenance
than a superficial normalization.

## Implemented recovery sequence

```text
backup + storage copy (read only)
             |
      parse and validate
             |
 contain paths and reserve names
             |
   copy without overwriting
             |
 SHA-256 source/output comparison
             |
 sync per-asset outcome journal
             |
 publish CSV and JSONL reports
```

Path traversal, source or destination symlink components, non-regular sources,
missing COPY sections, null asset IDs, missing required columns, and malformed
field counts fail closed. Collision suffixes use bounded hashes rather than raw
identifiers and are reserved so dry-run and export agree when they start from the
same filesystem state. An interrupted run retains `manifest.jsonl.partial`.

## Remaining preservation safeguards

- Resume must verify prior output and reuse stable planned destinations; today a
  prior report or partial journal causes a safe refusal.
- External libraries need explicit recorded-root to local-root mappings. Guessing
  arbitrary absolute paths is unsafe.
- Named Immich release support requires fixtures captured from those releases.
- Current Immich XMP sidecars in `asset_file` and historical
  `asset.sidecarPath` references are supported; other derivative relationships
  remain report-only or unsupported.
- Reports are sensitive because paths, identifiers, dates, and EXIF may identify
  people or places. Relative/redacted reporting needs an explicit schema change.
- Generated JSON metadata sidecars are not independently inventoried or covered
  by fixity fields.
- The CLI assumes exclusive control of the output during a run. Its path checks
  do not constitute a sandbox against a concurrent process racing filesystem
  components between validation and use.

These boundaries keep the project focused: serious preservation engineering can
improve a small recovery tool without pretending it is an archival system.
