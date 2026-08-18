# nano-crucible - Project Instructions

## What this is

Python client library + CLI for Crucible, Lawrence Berkeley Lab's Molecular Foundry data lakehouse.

- **Package**: `crucible` (installed editable)
- **Main branch**: `main`, shared dev branch: `dev` - push local work with `git push origin dev` (or `<local-branch>:dev`)
- **Companion repos**: `crucible-api` (server, read-only reference), `crucible-ingestion` (server-side ingestion workers), `crucible-labs`/`clabs` (downstream consumer), `crucible-lens` (Android/iOS app, separate stack)

## Testing

- `pytest tests/integration/` hits a live API, not mocks. Some `test_samples.py`/`test_metadata.py` sample tests fail independent of any change (pre-existing, server-side) - before treating a failure as a regression, `git stash` and rerun to confirm it fails on a clean tree too.
- `pytest tests/unit/` is mocked, no live API needed - use this for anything too new/risky to assume the live test server has deployed (e.g. a feature that just landed server-side), or for `crucible/parsers/`/`crucible/cast/` work (see below).
- `crucible/parsers/` and `crucible/cast/` have **no test suite at all**. Nothing but manual verification catches a regression there. When touching either:
  - Write a throwaway mocked-client smoke test exercising the change before calling it done (a real one under `tests/unit/` is even better).
  - Exercise *every* distinct code path a stateful feature can take (e.g. cast's fresh-create *and* resume-after-partial-failure *and* CLI status display), not just the common one - a signature change or deleted method can pass a smoke test of one path while still crashing another.
  - `grep` for every call site of anything you rename or delete; don't rely on the smoke test alone to surface them.

## Changelog discipline

Add a `docs/changelog.md` entry under `## Unreleased` **as part of the same change** that makes something user-visible - not just when preparing a release. Group entries under `### Added`/`### Changed`/`### Fixed` (only the sections that apply). Older, pre-existing versions are flat bullets - leave them as-is, don't retroactively regroup history.

**Style**: one short line per entry, under ~15 words. State *what* changed for the user, never *why*/*how* - no root cause, no file/line/class specifics, no mechanism. That detail belongs in the commit message. Purely internal changes with zero user-visible effect get no entry at all; a real bug fix that fell out of one still gets its own line.

Bad: "Fix: `cast` called nonexistent `client.datasets.upload_file()`/`request_ingestion()`; any recipe with files crashed. Now uses `add_file()` (upload + ingestion request in one call, per file) and tracks each file's ingestion request separately in the lock."
Good: "Fix `cast`: uploading files in a recipe always crashed."

## Things that have bitten us before

- Any model field with `extra='allow'` (most of `crucible/models.py`) silently accepts and forwards fields that were removed from the schema - a stale kwarg won't raise, it'll just get POSTed to the API. Removing a model field means grepping for every place that still constructs that model with the old field, not just checking for a runtime error.
- `AVAILABLE_INGESTORS` (`crucible/constants.py`) is a client-side-only reference/tab-completion list - it is not authoritative against the server and can silently drift out of sync with what `crucible-ingestion` actually supports.
- `ingestion_class=None` on `add_file()`/`datasets.create()` (and `BaseParser`, `dataset create --ingestor`, `cast` - all now default to `None`) means "let the server auto-detect from the file." That's correct when a format has a matching ingestor, but `ApiUploadIngestor` (generic, no-parse) is excluded from the server's auto-detect scan list in `crucible-ingestion` - a file with no specific ingestor gets `"not supported"`, not `"complete"`. Known, unresolved gap; the fix (add `ApiUploadIngestor` as a final fallback) lives in that separate repo.
- `DatasetOperations`/`FileOperations` read/write methods (`get`, `list`, `list_files`, `update`) validate raw API dicts through their Pydantic model before returning (`self._parse(raw)`) rather than returning untouched dicts - keeps new API fields from being silently dropped. Follow this pattern for any new resource method that returns a record shaped like an existing model.
