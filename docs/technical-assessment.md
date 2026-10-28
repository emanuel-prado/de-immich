# Independent technical assessment

Assessment date: 2026-10-27. Scope: repository history through PRs #1–#4,
application source, documentation, synthetic reproductions, and upstream
specifications/source noted below.

An adversarial follow-up review of the draft stack found and corrected additional
issues before merge:

- raw asset-ID prefixes in collision names allowed path separators to influence
  the destination; collision tokens now use bounded SHA-256 text;
- an existing symlinked year/month output directory could redirect writes outside
  the export; destination parents are now contained and checked;
- null asset IDs disappeared silently, and non-file sidecars were not rejected;
- an unused unsafe sidecar reference could block original recovery;
- later verification could print `OK` for a file whose report already recorded a
  failed source/output comparison;
- verification followed a substituted output symlink and accepted identical
  target bytes;
- the report schema documented a dry-run `planned` row that is never persisted.

Regression tests now cover each corrected behavior. Filesystem checks assume the
tool has exclusive control of its output; defending against a malicious process
racing path components would require descriptor-relative filesystem operations
and is not claimed.

## Findings that changed the plan

The original single-file architecture was not itself the problem. Parsing,
resolution, copying, and report generation were already separate functions, so a
package refactor would have increased change risk before adding recovery value.
The implementation stayed dependency-free and gained tests at those seams.

The most urgent gaps were more basic than preservation packaging:

- `../outside.jpg` resolved outside `--library-root` and could be copied.
- A source symlink was followed without policy or containment checks.
- Two colliding assets received the same destination in dry-run because planned
  names were not reserved.
- An absent COPY section produced zero rows rather than an unsupported-input error.
- A short COPY row was silently accepted because `zip()` discarded absent fields.
- Media, JSON sidecars, and manifests used operations that could overwrite or
  publish partial results under unexpected filesystem conditions.
- Skipped records were counted but absent from the audit inventory.
- Reports existed only in memory until the end of a run.

Minimal synthetic reproductions confirmed the first five behaviors before code
was changed. Tests now retain those cases as regressions.

## Pull-request review

PR #1 appropriately establishes conservative branch, source-data, and
verification rules. It is process documentation and does not establish that the
application meets those guarantees.

PR #2 is directionally strong: it states the project boundary, avoids compliance
claims, and names fixity/resume/path safety as missing. Several statements needed
revision after implementation and upstream review:

- “resolves existing filename collisions” did not explain dry-run divergence or
  duplication on rerun;
- a blanket proposal to contain every source under the Immich root overlooked
  legitimate external libraries, which instead need explicit mappings;
- optional sidecar wording did not distinguish historical `asset.sidecarPath`
  dumps from the current `asset_file` schema;
- BagIt was presented as a natural later feature without evidence that transfer
  packaging is a user need;
- a metadata crosswalk needed stronger warnings against treating filenames,
  owner UUIDs, or ambiguous timestamps as Dublin Core semantics.

PR #2 has therefore been revised as a documentation-only stack above the safety
and fixity work rather than merged as an aspirational standalone narrative.

## Upstream evidence and compatibility

- The [Immich backup documentation](https://immich.app/docs/administration/backup-and-restore/)
  confirms that database dumps contain metadata but not media, that originals
  live under `upload/` or `library/`, and that database/filesystem snapshots can
  be inconsistent when taken while the service changes.
- Immich v3.3.5 source retains `asset.originalPath` and `asset_exif`, but models
  related files in `asset_file`. That supports original recovery in principle but
  contradicts any current-version sidecar claim.
- PostgreSQL [COPY text format](https://www.postgresql.org/docs/current/sql-copy.html#SQL-COPY-FILE-FORMATS)
  defines backslash escapes, `\N` nulls, and the `\.` terminator. The parser now
  rejects field-count and termination errors instead of silently proceeding.
- PREMIS 3.0 informs the questions asked of Objects, Events, Agents, and fixity;
  the project report does not implement that data model.
- [RFC 8493](https://www.rfc-editor.org/rfc/rfc8493.html) requires substantially
  more than a checksum list for BagIt. Bagging is deferred, not advertised.

Immich v3.3.5 is the first named, end-to-end-tested release. A native instance at
upstream commit `8303cb117e197c700332b33b61b45314c9cc5bb4` migrated a PostgreSQL
18 database and accepted synthetic image and video uploads through its API. A
plain `pg_dump`, compressed with gzip, was then recovered with this tool. The
exercise covered duplicate and Unicode original names, dated and flat exports,
limits, deleted/offline/missing outcomes, JSON metadata sidecars, source/output
SHA-256 agreement, later corruption and absence detection, and repeat-run
refusal. The source storage snapshot was unchanged after recovery.

This is deliberately narrow evidence. The instance ran from pinned source
because OCI registries were unavailable in the test environment, not from the
published production image. Immich's microservices worker also requires a
geodata bundle normally supplied by that image, so background metadata
extraction was not part of the run. The database schema and storage paths were
nevertheless produced by v3.3.5 itself; the result does not establish support
for earlier or later releases, external libraries, or current `asset_file`
sidecar recovery.

## Residual risks

Highest priority is verified resume: current behavior safely refuses an output
with a complete or partial report, but assets copied before an interruption can
remain. External libraries are rejected rather than recoverable. Sidecars are not
covered by fixity. Reports expose absolute paths and potentially identifying
metadata. EXIF/report rows consume memory and the gzip dump is read multiple
times; optimization should follow measured scale tests, not speculation.

The project is substantially safer, but “production ready,” “PREMIS compliant,”
“BagIt compatible,” and broad Immich-version support would all be unsupported
claims.
