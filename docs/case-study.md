# Case study: getting a photo collection out of Immich

> **Portfolio summary:** A standalone Python recovery utility that reconnects media files with their original filenames and database metadata, producing an inspectable export without a running Immich or PostgreSQL service.

## Problem

Self-hosted media management applications are useful for organizing collections, but recovery can become difficult when you have a database backup and a storage directory without the application running.

The storage files alone may not preserve the filenames, collection references, timestamps, or descriptive context needed to make a recovered collection intelligible.

## Engineering approach

I built `de-immich` to read the compressed PostgreSQL SQL dump produced by Immich, locate its asset and EXIF records, and match them to media in the storage tree.

The utility:

1. Parses `COPY` data directly from the compressed backup using Python's standard library.
2. Recovers original filenames and selects dates from EXIF or database timestamps.
3. Recreates the files in a human-friendly dated directory structure.
4. Optionally copies sidecar files and emits JSON metadata alongside assets.
5. Calculates and compares SHA-256 for source bytes and the published copy.
6. Writes versioned CSV/JSONL reports for exported, missing, skipped, and
   fixity-failed assets, with an incremental journal for interrupted runs.

The implementation is deliberately a single-file CLI rather than another application that requires deployment or a database server.

## Skills demonstrated

- **Data recovery and migration:** reconciling structured database records with unstructured storage.
- **Metadata management:** extracting descriptive and technical fields while maintaining links to the source system.
- **Python and structured formats:** compressed SQL parsing, filesystems, CSV, JSONL, and EXIF-related metadata from source records.
- **Pragmatic software design:** a small dependency-free tool for a clearly bounded recovery task.
- **Digital-preservation engineering:** identification, provenance, copy fixity,
  later verification, auditability, and explicit limits on authenticity claims.

## Tradeoffs and limitations

- Requires both the backup and original media; it cannot reconstruct deleted or absent file contents.
- Database parser currently expects specific Immich COPY sections. Immich
  v3.3.5 has one end-to-end synthetic validation; a multi-version compatibility
  matrix remains to be built.
- Current manifests are a practical export inventory, **not** standards-conformant preservation records.
- Safe resume, external-library mapping, current-schema sidecar recovery, and a
  complete preservation-event model remain to be implemented.
- Path validation assumes no other process is concurrently replacing filesystem
  components during recovery; the utility is not an operating-system sandbox.
- No published performance, scale, or recovery-success claims are made without measured evidence.

## Next steps

The next milestones are fixture-backed Immich version compatibility, explicit
external-library mappings, and verified resume semantics. BagIt remains deferred
until transfer packaging is a demonstrated need.

See [the project README](../README.md), [preservation notes](preservation-notes.md), and [roadmap](roadmap.md).

## Positioning

This is **not** a general-purpose DAM platform. It is a focused example of building software around digital assets and their long-term usability, with transparency about what has and has not been implemented.
