# Roadmap: a preservation-first recovery utility

**Product goal:** recover original Immich media into a human-usable collection
while retaining enough evidence to inspect and independently verify the result.

## Completed foundation (pending review)

- Contained internal source and output paths; rejected traversal, symlinked
  components, and non-files; hashed untrusted IDs used in collision suffixes.
- Required/validated `asset` and `asset_exif` COPY sections and row widths.
- Reserved collisions consistently within dry-run and export.
- Published files without overwriting existing paths.
- Added synthetic tests for SQL escaping/nulls, malformed data, paths,
  collisions, malicious identifiers, output symlinks, missing files, dry-run,
  interruption, invalid reports, recorded fixity failures, and corruption.
- Recorded all normal skipped/missing/export outcomes in a synced journal.
- Compared source/output SHA-256 and added later manifest verification.
- Documented the versioned recovery report and its authenticity/privacy limits.
- Recovered current `asset_file` XMP sidecars and recorded independent sidecar
  fixity, validated against an API-created Immich v3.3.5 asset.

GitHub Actions remains blocked by the current automation token's missing
`workflow` scope. The suite itself has no third-party dependency and runs with:

```bash
python3 -m unittest discover -s tests -v
```

## P0 — Next recovery guarantees

### 1. Verified resume

- Plan stable destinations independently of transient filesystem state.
- Read a prior versioned report and verify content before skipping it.
- Define recovery from `manifest.jsonl.partial` without trusting incomplete work.
- Never turn a changed existing file silently into another collision copy.

**Done when:** interruption followed by resume neither duplicates content nor
trusts a modified prior output, with tests for both outcomes.

### 2. Evidence-backed Immich compatibility

- Generate or anonymize dump shapes from named Immich releases without user data.
- Extend named-version fixtures beyond the validated Immich v3.3.5 shape.
- Detect unsupported shapes and publish a narrow compatibility matrix.

**Done when:** every release claim cites a fixture and unsupported required
relationships fail with actionable guidance.

### 3. Explicit external-library mappings

- Map a recorded database root to a user-supplied local root through repeatable
  CLI options.
- Apply containment and symlink policy independently to every configured root.
- Include the selected mapping (with an optional redacted form) in run metadata.

**Done when:** synthetic internal and external assets recover without permitting
an unmapped absolute path.

## P1 — Report and interoperability improvements

### 4. Run-level provenance and privacy

- Record backup identity, export options, start/end times, and aggregate outcomes.
- Add relative destination paths and an explicit redaction mode.
- Define schema migration and backwards-compatibility rules.

### 5. Metadata crosswalk only where semantics support it

- Inventory fields available in tested schemas.
- Separate source values from normalized values and document every mapping.
- Do not infer Dublin Core titles, creators, or dates from ambiguous identifiers
  and timestamps.

## P2 — Demonstration and measured scale

- Publish a fictional sample library and before/after report.
- Benchmark 1k/10k/100k synthetic datasets with commands, hardware, time, and peak
  memory recorded.
- Reassess streaming EXIF/report data only if measurements justify complexity.
- Reconsider BagIt only for a real transfer workflow and require validation with
  an independent RFC 8493 implementation.

## Not planned

A web interface, image recognition, face clustering, asset search service,
database daemon, plugin framework, full DAM, or archival repository. The value is
reliable extraction, documented metadata, fixity, and portability—not feature
volume.
