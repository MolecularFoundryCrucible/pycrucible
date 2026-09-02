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

## User identifier inconsistency — RESOLVED

Fixed: all `user` subcommands and `project add-user`/`remove-user` now accept a single
identifier (ORCID, MFID, username, or email) that's format-sniffed via `helpers.parse_user_ref()`.

- Commands with no other required positional (`user get`, `user edit`) take it as a
  positional `USER` argument.
- Commands with an existing positional ORCID slot (`user update`, `add-access-group`,
  `remove-access-group`, `list-datasets`, `check-access`, `list-access-groups`,
  `list-projects`) had that slot's accepted values widened from ORCID-only to
  ORCID/MFID/username/email, resolved to a canonical user ID via
  `helpers.resolve_user_id()` before the API call.
- Commands with a different required positional (`project add-user PROJECT_ID`,
  `project remove-user PROJECT_ID`) got a new `--user`/`-u` flag instead.

Old `--orcid`/`--username`/`--email` flags on `user get`, `user edit`, `project add-user`,
`project remove-user` still work but emit a `DeprecationWarning` pointing at the new form.

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
