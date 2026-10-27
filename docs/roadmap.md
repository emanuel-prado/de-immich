# Roadmap: a preservation-first recovery utility

**Product goal:** Recover original Immich media into a human-usable collection while preserving enough context to make the operation inspectable, reproducible, and independently verifiable.

This is a prioritized proposal, **not a list of features already implemented**. Favor small PRs, synthetic fixtures, and clear pass/fail criteria.

## P0 — Trustworthy recovery foundation

### 1. Export planning and filesystem safety

- Validate and contain source, sidecar, and destination paths (including symlink behavior).
- Pre-allocate deterministic destinations for filename collisions and dry-run output.
- Never silently overwrite exports.
- Reject incompatible or incomplete SQL schemas with clear errors.

**Done when:** a synthetic test collection with traversal attempts, collisions, and missing schema sections cannot escape intended directories or silently produce ambiguous results.

### 2. Automated compatibility fixtures and tests

- Use tiny, synthetic `.sql.gz` backups and media placeholders, with no real personal media.
- Cover PostgreSQL COPY escaping, nulls, timestamp precedence, deleted/offline filtering, and manifest status.
- Add CI on documented supported Python versions.

**Done when:** contributors can run a single command to test the complete sample recovery flow without Immich or PostgreSQL.

### 3. Auditable outcomes and safe reruns

- Include skipped, missing, failed, and successful assets in an export journal.
- Separate asset discovery, export planning, writing, and verification phases.
- Add resumable exports that verify prior results before skipping them.
- Make nonzero exit status and failure reporting meaningful for partial recovery.

**Done when:** rerunning a partially completed export neither duplicates files nor loses evidence about what happened.

## P1 — Integrity, provenance, interoperability

### 4. Fixity verification

- Optionally compute SHA-256 for source and exported files.
- Record source checksum, output checksum, verification result, and event time.
- Offer a separate verification command for checking previously exported data.
- Detect truncated and changed media; make failures visible in both exit code and report.

**Done when:** a deliberately corrupted exported file is detected by a reproducible test.

### 5. Structured preservation report

- Add an explicit report schema version and documented field definitions.
- Record tool version, backup identity, export options, timestamps, per-asset outcomes, and preservation actions.
- Prefer relative paths in shareable reports; make sensitive original paths optional/redactable.
- Clearly distinguish measured values from missing values.

**Done when:** an external script can read a report, identify missing/corrupted records, and trace an exported object back to its source reference.

### 6. Tested Immich schema variants

- Capture anonymized table schemas (not user data) from selected Immich versions.
- Detect versions/columns where possible; fail with guidance on unsupported dumps.
- Publish a compatibility matrix of tested backups.

**Done when:** support claims cite a tested fixture and unsupported versions fail explicitly.

## P2 — Preservation packaging and professional showcase

### 7. Optional interoperable package

- Evaluate full BagIt output/validation under [RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html).
- Keep the ordinary dated-directory export as the default.
- Consider descriptive/administrative metadata crosswalks only when source fields justify them.

**Done when:** output passes an independent BagIt validator, not merely the tool's own checks.

### 8. Demonstration and benchmarks

- Publish a fictional, synthetic sample library and before/after results.
- Include a short CLI recording, example manifest with redacted paths, and a recovery report.
- Benchmark time and memory on synthetic 1k/10k/100k datasets, publishing methodology.

**Done when:** someone unfamiliar with Immich can understand the problem, try the sample, and inspect measurable results.

## Not planned

A browser-based DAM, image recognition, face clustering, asset search service, a database service dependency, or a full archival management platform.

The long-term value lies in **reliable extraction, documented metadata, fixity, and portability**—not interface complexity.
