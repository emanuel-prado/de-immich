# Repository Agent Rules

These instructions apply to the entire repository. Repository-specific safety rules below take precedence over the shared delivery contract.

## Shared Delivery Contract

- Never implement directly on `main`, `master`, or another default branch.
- Start each implementation slice from an up-to-date default branch and create `agent/<issue-or-slice>-<short-kebab-description>`.
- Keep one coherent implementation slice per branch, worktree, commit series, and pull request.
- Use a separate git worktree for concurrent or unfinished agent sessions. Never reuse a dirty worktree or overwrite unrelated user work.
- Use Conventional Commits: `<type>(optional-scope): <imperative summary>`.
- Run the narrowest relevant checks while developing, then the complete documented verification suite before publishing.
- Report exactly which checks ran, their results, and anything skipped. Never claim an unrun check passed.
- Open pull requests as drafts by default. Link the owning issue and use `Closes #...` only when the pull request fully satisfies it.
- Do not expand scope, perform drive-by refactors, merge, enable auto-merge, mark ready for review, force-push, rewrite published history, resolve review threads, or dismiss feedback unless explicitly asked.

## Recovery Safety

- Treat Immich backups, storage trees, manifests, and exported media as user-owned recovery data.
- Never delete, move, rename, overwrite, or mutate source media, backups, or database dumps unless the user explicitly requests it.
- Preserve dry-run behavior for any operation that can write files, and recommend `--dry-run` before destructive or large exports.
- Make collision handling explicit and deterministic. Do not silently overwrite an existing export.
- Keep missing, malformed, deleted, and offline assets observable in summaries and manifests rather than failing silently.
- Do not commit real backups, manifests containing private paths, exported media, or user-specific filesystem locations.

## Engineering and Verification

- Preserve compatibility with the documented Python baseline unless an issue explicitly changes it.
- Keep SQL parsing, path resolution, export planning, filesystem writes, and manifest generation separable and testable.
- Add tests for schema variants, malformed rows, missing files, path normalization, name collisions, timestamp fallback, and dry-run behavior when changing those areas.
- Prefer fixture-based tests with synthetic paths and metadata. Tests must not require a real Immich library.
- Update compatibility notes when supporting or dropping an Immich schema or storage-layout variant.
