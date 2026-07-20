# CLI Known Issues and Inconsistencies

Tracked here for future cleanup. Not bugs — the CLI works — but rough edges worth fixing in a future pass.

---

## Short flag conflicts

| Flag | Meaning A | Meaning B | Files |
|------|-----------|-----------|-------|
| `-o` | `--orcid` (user edit) | `--output` / `--output-dir` (get, file download) | user.py, get.py, file.py |
| `-l` | `--last-name` (user create, update) | `--limit` (dataset/sample/project/instrument search) | user.py, dataset.py, sample.py, project.py, instrument.py |
| `-f` | `--first-name` (user create, update) | `--file` (ingestion) | user.py, ingestion.py |
| `-s` | `--set KEY=VALUE` (dataset update) | `--sample` (dataset add-sample, remove-sample) | dataset.py |
| `-p` | `--projects` (user create) | `--parent` (dataset link, sample link) | user.py, dataset.py, sample.py |
| `-d` | `--dataset` (file list, sample add-dataset, ingestion) | `--depth` (tree) | file.py, sample.py, ingestion.py, tree.py |

---

## User identifier inconsistency

Commands that identify a user should accept `--orcid`, `--username`, `--email` as a mutually exclusive group (pattern used by `user get` and `user edit`). These commands still use positional ORCID only:

- `crucible user update ORCID` (user.py)
- `crucible user add-access-group ORCID GROUP` (user.py)
- `crucible user remove-access-group ORCID GROUP` (user.py)

---

## Project ID flag inconsistency

No single convention for project ID across commands:

| Command | Flag used |
|---------|-----------|
| `sample list/create/search` | `-pid/--project-id` |
| `sample update` | `--project` (no short form) |
| `dataset search` | `--project/-pid` |
| `project get/update` | positional |
| `project create` | `--project-id/-id` |

---

## Minor

- `sample create` uses `--sample-type` but `sample update` uses `--type` for the same field (sample.py).
