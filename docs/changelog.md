# Changelog

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
