# Preservation-oriented design notes

This document explains the thinking behind `de-immich` as an exploratory **digital-preservation and metadata-recovery** project. It deliberately distinguishes what the tool currently does from preservation capabilities we want to add.

## Preservation question

A successful recovery is not just a directory containing readable images. It should help answer:

1. **What is this object?** Original identity, name, format, dates, and descriptive context.
2. **Where did it come from?** Source collection, asset identifiers, and the metadata used to reconstruct it.
3. **What happened to it?** Which extraction and copy operations took place, when, and with what result.
4. **Is it intact?** Could the bytes be compared to a recorded checksum, now and later?
5. **Can another system use it?** Open inventories, documented field semantics, portable paths and metadata.

## Current evidence and metadata

| Archival/DAM concern | Current de-immich fields or behavior | Caveat |
| --- | --- | --- |
| Identification | `assetId`, `originalFileName`, `type` | Immich IDs identify records inside the source system, not universal identifiers |
| Descriptive / technical metadata | `exif_*`, timestamp fields, `type` | Limited to what the backup stores; not a normalized interchange schema |
| Provenance | `originalPath`, `resolvedSourcePath`, `exportedPath`, `ownerId`, `libraryId` | Captures paths/relations but not a complete chain of custody |
| Relationships | `sidecarPath`, `livePhotoVideoId`, `duplicateId`, `stackId` | Records reference IDs; does not reconstruct every relationship |
| Recovery events | `status`, CLI summary | No timestamped event history, agent identity, or standardized event schema |
| Fixity | Not implemented | Neither source nor output checksums are recorded or verified |
| Portability | CSV/JSONL manifests; optional JSON sidecars | Contains environment-specific absolute paths; should support redacted/relative paths |

## Standards as design references (not claims of compliance)

### PREMIS: preservation objects and events

The [PREMIS Data Dictionary 3.0](https://www.loc.gov/standards/premis/v3/) distinguishes Objects, Events, Agents, and Rights. For a future provenance report, that provides useful questions:

- **Object:** Which file/asset was processed? What is its checksum and identifier?
- **Event:** Was the file discovered, copied, verified, skipped, or found missing? When?
- **Agent:** Which version of the tool performed the action?
- **Rights:** What usage or custody information exists? (Not currently tracked.)

For now, the export manifest is **PREMIS-inspired at most**. It does not produce PREMIS XML, JSON, or a validated PREMIS representation.

### BagIt: portable, verifiable packages

[BagIt (RFC 8493)](https://www.rfc-editor.org/rfc/rfc8493.html) describes a directory-based transfer package with file checksum manifests.

A future optional `--bagit` output could package the recovered payload, manifest, and contextual metadata for transfer. Adding a file named `manifest-sha256.txt` alone would **not** make a valid bag; layout, required tags, tag manifests, and validation must follow the specification.

### Metadata interoperability

CSV and JSONL work well for analysis and migration, but currently expose source-system field names.

A future documented crosswalk could separate:

- **Descriptive metadata:** Human titles, dates, subjects, location where available.
- **Technical metadata:** Media type, dimensions, encoding, capture metadata.
- **Administrative metadata:** Source library, status, recovery timestamps.
- **Preservation metadata:** Fixity values and event outcomes.

Do not invent missing fields or silently normalize ambiguous date/time values. Track field provenance and mapping decisions.

## Workflow to aim for

```text
Original backup + storage tree (read-only)
                 |
          Parse + validate
                 |
          Plan destinations
                 |
       Recover original objects
                 |
      Verify copy integrity / fixity
                 |
     Write auditable recovery events
                 |
      Export portable metadata
                 |
     Optional validated BagIt bag
```

The **implemented** subset today is SQL parsing, destination selection, copies, optional sidecars, and basic inventories. Validation, full event logging, fixity, and BagIt packaging are planned, not done.

## Preservation safeguards before new features

- Never overwrite or mutate backup/source media.
- Contain all resolved input and output paths; reject traversal and unsafe symlinks.
- Plan deterministic collision names and make `--dry-run` describe the actual intended operation.
- Make reruns idempotent and resumable; verify previously exported content before trusting it.
- Include **all outcomes**, including skipped and failed records, in the audit inventory.
- Treat manifests as sensitive: paths and embedded EXIF can reveal personal information.
- Verify claims with synthetic fixtures and explicit, versioned Immich compatibility tests.

## Scope boundary

This is a **recovery and preservation-preparation utility**, not a full DAM, catalog, records-management system, archival repository, or OAIS implementation. It is also not a substitute for maintaining multiple tested backups.

That boundary is intentional: a small, comprehensible tool that exports intelligible data can itself be a meaningful contribution to digital preservation.
