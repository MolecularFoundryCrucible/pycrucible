# Changelog

## Unreleased

- `search_metadata()`: updated for API change — response is now unwrapped from the paginated envelope, default limit changed to 20, and each result now includes `resource_type`, `name`, `owner_orcid`, `creation_time`, `modification_time`, and `rank` alongside `scientific_metadata`.

- `include_owner=True` on `datasets.get/list()`, `samples.get/list()`, and `client.get()` resolves the owner into a full user object. CLI shows "First Last (@username)" instead of a raw ORCID. Support on `GET /resources/{id}` is pending API deployment.

- `client.files.delete(file_id)` and `crucible file delete FILE_ID` to delete a file by MFID (`DELETE /files/{file_id}`).
- `samples.create()` now takes a `Sample` model as its first argument, consistent with `datasets.create()`. Passing keyword arguments still works but raises a `DeprecationWarning`.
- `crucible project list-users` now shows the username column and correctly reads `unique_id` as the ORCID (field was renamed on the API side).
- Default graph explorer URL updated to `https://crucible.lbl.gov/explore`.

## 3.0.1

- Fix `datasets.download()`: data files now saved inside `output_dir/{dsid}/` alongside `record.json`, not directly in `output_dir/`.

## 3.0.0

This is a major release. The flat `client.*` API that was deprecated in 2.x has been
removed. All operations now live under typed resource namespaces.

!!! danger "Breaking changes"
    **Before upgrading**, update any code that uses the old flat API:

    | Old (removed) | New |
    |---|---|
    | `client.get_dataset(dsid)` | `client.datasets.get(dsid)` |
    | `client.create_new_dataset(...)` | `client.datasets.create(...)` |
    | `client.list_datasets(...)` | `client.datasets.list(...)` |
    | `client.get_sample(sid)` | `client.samples.get(sid)` |
    | `client.add_sample(...)` | `client.samples.create(...)` |
    | `client.list_samples(...)` | `client.samples.list(...)` |
    | `client.get_project(pid)` | `client.projects.get(pid)` |
    | `client.get_user(orcid=...)` | `client.users.get(orcid=...)` |
    | `client.download(resource_id)` | `client.datasets.download(dsid)` or `client.samples.download(sid)` |
    | `pip install nano-crucible[shell]` | `pip install nano-crucible` (now core) |
    | `pip install nano-crucible[gcs]` | `pip install nano-crucible` (now core) |
    | `pip install nano-crucible[all]` | `pip install nano-crucible` |

### New resource namespaces

- **`client.account`** — self-service profile management (`profile()`, `update_profile()`,
  `api_key()`, `verify()`, `whoami()`). No admin required.
- **`client.ingestions`** — ingestion request management (`list()`, `get()`, `wait()`, `update()`).
- **`client.files`** is now a proper peer resource (previously a base class for `DatasetOperations`).
  Scoped to file MFIDs: `get()`, `list()`, `download()`, `get_download_link()`, `request_ingestion()`.

### Architecture changes

- `DatasetOperations` no longer inherits from `FileOperations`. All dataset-scoped file
  operations (`add_file`, `list_files`, `get_download_links`, `download`, thumbnails,
  ingestion) now live directly on `DatasetOperations`.
- Upload logic extracted to `crucible/resources/gcs/upload.py` — standalone functions
  testable in isolation.
- Download logic extracted to `crucible/resources/gcs/download.py` — parallel file downloads
  via `ThreadPoolExecutor`.
- Scientific metadata methods (`search_metadata`, `get_scientific_metadata`,
  `update_scientific_metadata`, `get_access_groups`, `add_access_group`) unified on
  `BaseResource` — available on all resource types.
- `search_scientific_metadata()` renamed to `search_metadata()` (deprecated alias kept).

### New features

- **Parallel GCS multipart upload** — `add_file()` uses `transfer_manager.upload_chunks_concurrently()`
  by default (8 workers, 64 MiB chunks, benchmarked). Falls back to sequential resumable upload
  with `multipart=False`. Upload settings configurable via `crucible config set upload_chunk_size_mb`
  and `upload_max_workers`.
- **Sequential per-dataset downloads** — files within a dataset download sequentially; to
  parallelise across datasets, wrap `datasets.download()` in a `ThreadPoolExecutor` at the
  caller level.
- **Fuzzy name search** — `datasets.search(q)`, `samples.search(q)`, `projects.search(q)`,
  `instruments.search(q)` via new API endpoints. Typo-tolerant, returns top-N by relevance.
- **Scientific metadata search** renamed — `search_metadata(q)` on all resources.
- **Username support** — `users.get(username=...)`, `users.search(q)`, `user set-username`,
  `project add-user -u USERNAME`.
- **`samples.download(sid)`** — saves sample record as `record.json`.
- **`files.download(file_id)`** — single-file download by MFID.
- **`ingestions.wait(request_id)`** — public polling method.

### Packaging

- `google-cloud-storage>=2.7.0` and `prompt_toolkit>=3.0` moved to core dependencies.
- `[shell]`, `[gcs]`, and `[all]` extras removed — `pip install nano-crucible` installs everything.
- `[parsers]` remains optional (ASE/LAMMPS support).

### CLI additions

- `crucible account` — `show`, `edit`, `update`, `api-key`, `verify`
- `crucible ingestion` — `list`, `get`, `wait`
- `crucible user search TERM` — non-admin user lookup
- `crucible {dataset,sample,project,instrument} search TERM` — fuzzy name search
- `crucible {dataset,sample,project,instrument} search-metadata TERM` (also `search-md`)
- `crucible dataset list-access-groups`, `add-access-group`
- `crucible user add-access-group`, `remove-access-group`
- `crucible deletion list-deleted`, `get-deleted`, `delete --force`
- `--json` flag on all `get` and `list` commands (replaces `--output json`)
- `sample update` — named flags (`-n`, `-t`, `--description`, `--project`, `--public`)

### Deprecations (still work, emit warnings)

- `client.download()` → `client.datasets.download()` or `client.samples.download()`
- `datasets.get_associated_files()` → `datasets.list_files()`
- `datasets.search_scientific_metadata()` → `datasets.search_metadata()`
- `datasets.add_file_to_dataset()` → `datasets.add_file()`
- `datasets.graph()` → `client.graphs.get()`
- `datasets.get_ingestion_requests()` → `client.ingestions.list()`
- `datasets.get_request_status()` → `client.ingestions.get()`
- `datasets.update_ingestion_status()` → `client.ingestions.update()`
- `users.me()` → `client.account.profile()`
- `users.get_api_key()` → `client.account.api_key()`

---

## 2.1.0 → 2.1.2

Although versioned as a patch series, this span (late March to mid-May) is effectively a
feature release. The notes below focus on what affects code you write against the client.

!!! warning "Likely breaking changes"
    Most users only need to address three things:

    - User responses now key identity as `unique_id` instead of `orcid` (e.g. `user["orcid"]` → `user["unique_id"]`).
    - File methods now live under `client.files` (backward-compat shims on `client.*` still work).
    - `add_metadata` was renamed to `replace_scientific_metadata`.

### New resource namespaces

- **`client.files`** — file operations moved here from `datasets`: chunked GCS upload, plus
  listing, inspecting, and downloading files by `dataset_mfid` or SHA-256 hash.
- **`client.deletions`** — deletion-request workflow (request / approve / reject).
- **`client.graphs`** — graph queries.

### New top-level client methods

- `client.live()` / `client.health()` — unauthenticated health checks.
- `client.search_scientific_metadata(q)` — full-text search across scientific metadata.
- `client.get_links(resource_id)` — immediate links for any resource.

### Moved or renamed methods

- **File methods moved `datasets` → `files`**: `add_associated_file`, `get_associated_files`,
  `upload_file`, and download helpers. Backward-compat shims on `client.*` still work.
- **Scientific-metadata methods moved to the shared base resource** — now available on
  `datasets`, `samples`, `projects`, *and* `instruments`.
- **`add_metadata` → `replace_scientific_metadata`** (rename). Use
  `update_scientific_metadata(..., overwrite=False)` to merge (PATCH) or `overwrite=True` to
  replace (POST).
- **`users`**: removed `get_or_create` and `get_user_from_api`; added `update()`,
  `get_api_key()`, and `remove_from_access_group()`.
- **`projects`**: added `update()`, `remove_user()`, `add_scientific_metadata()`, and
  `update_scientific_metadata()`.
- **`instruments`**: added `update()`, `add_scientific_metadata()`, and
  `update_scientific_metadata()`.
- **`samples` / `datasets`**: added `count()` and `graph()`.

### Model field changes

- **`User`**: `orcid` field renamed to `unique_id` (with a `.orcid` property alias for
  backward compatibility); removed `lbl_email` and `employee_number`; added
  `is_service_account`.
- **`Sample`**: added `public`, `scientific_metadata`, `datasets`, `links`,
  `deletion_request`, `resource_type`; removed `owner_user_id`.
- **`Dataset`**: added `data_type`, `scientific_metadata`, `links`, `deletion_request`,
  `resource_type`; removed `owner_user_id` and `instrument_id`; dropped `file_to_upload` and
  `sha256_hash_file_to_upload`.
- **`Project`**: `project_lead_email` is now optional (previously required); added
  `project_lead_orcid`, `lead`, `scientific_metadata`, and timestamp fields.
- New **`DeletionRequest`** model.

### Behavior changes

- `projects.add_user()` / `remove_user()` accept an email directly — no more client-side
  ORCID resolution.
- Chunked GCS uploads: 32 MiB chunks with per-chunk CRC32C and incremental SHA-256, verified
  at `/complete`.
- Fixed a hashing bug affecting larger files (the actual 2.1.1 → 2.1.2 change).
- Public-sample support (`sample create --public`).

### Packaging

- New required dependencies: `configupdater`, `pyyaml`, `google-crc32c`.
- New optional extras: `[shell]` (`prompt_toolkit`) and `[docs]` (mkdocs).

### CLI

New subcommands: `crucible file`, `crucible deletion`, `crucible status`, `crucible qr`,
`crucible tree`, and `crucible cast`, plus an interactive shell when you run `crucible` with
no arguments.
