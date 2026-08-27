---
name: nano-crucible
description: Help users configure and operate the nano-crucible Python client or CLI, including discovering scientific records, creating datasets and samples, uploading or cataloging files, linking provenance, and diagnosing client errors. Use for Crucible client workflows; do not use for direct server implementation work.
---

# nano-crucible

## Ownership status

This repository copy is a temporary operational template. Shared operational guidance is moving to [`crucible-ecosystem`](https://github.com/MolecularFoundryCrucible/crucible-ecosystem), which will become authoritative after migration. Until then, verify exact package behavior against Nano's published user documentation and the installed CLI help. Repository-specific development skills remain with the Nano source code.

Help the user accomplish a concrete Crucible workflow through the installed Python client or `crucible` CLI. Prefer the interface the user is already using; when they have no preference, use the CLI for interactive one-off work and Python for repeatable automation.

## Establish context

Before a network operation, determine which API URL, project, and identity are in scope. Never request that the user paste an API key into chat or source code. Guide them to `crucible config init` for local use or the `CRUCIBLE_API_KEY` environment variable for automation.

Use these read-only checks when appropriate:

```bash
crucible status
crucible whoami
crucible config get api_url
crucible config get current_project
```

Do not print the entire config: it may contain credentials.

## Discover the installed interface

This client evolves. Before giving exact flags for a nontrivial command, inspect `crucible <resource> --help` and the subcommand's `--help`. In a source checkout, consult the matching module under `crucible/cli/` or `crucible/resources/` when the help text does not answer a Python API question.

Current Python code should use resource namespaces:

```python
from crucible import CrucibleClient

client = CrucibleClient()
datasets = client.datasets.list(project_id="my-project", limit=20)
```

Do not suggest the flat pre-3.0 methods such as `client.get_dataset()` or `client.create_new_dataset()`.

## Respect mutation boundaries

Listing, searching, getting, downloading, identity checks, and status checks are read operations. Creating or updating records, uploading or cataloging files, linking resources, changing access, publishing, transferring ownership, requesting ingestion, and deletion workflows mutate the live service.

Only perform a mutation when the user has asked for that outcome. Before running it, make the target project/resource and important consequences clear. Confirm again when the target is ambiguous, the command changes access or ownership, or the action could expose, overwrite, duplicate, or delete data. A dry run or local example does not authorize a later live mutation.

Do not run this repository's integration tests as a harmless verification step: they create persistent records and do not clean up after themselves.

## Model scientific records well

- A project is both an organizational and access-control boundary.
- A dataset represents an experiment or process and can include files, reproducibility metadata, keywords, and provenance links.
- A sample represents physical or computational material and can form a parent-child preparation history.
- An instrument identifies a specific physical machine, not a generic equipment class.
- Link datasets and samples only when the direction and provenance meaning are known; do not infer parent and child from names alone.
- Use `scientific_metadata` for domain-specific, preferably standardized values; use first-class model fields for shared attributes such as project, measurement, instrument, and timestamp.

For local paths, `datasets.create(..., files=[...])` uploads by default. Passing `upload_files=False` catalogs resolved paths without uploading. An `AssociatedFile` catalogs a non-GCS location such as Globus, NERSC, or a shared filesystem. Explain this distinction before choosing for the user.

Leaving `ingestor` unset asks the server to auto-detect the format. Do not invent an ingestor name from a file extension. If detection fails, inspect `crucible dataset ingestors` and ask which behavior the user wants.

## Communicate results safely

Report created or changed resource IDs and the project involved, but redact API keys, authorization headers, signed URLs, and sensitive file paths. On failure, include the operation and server detail without exposing credentials. Distinguish authentication failures, authorization failures, unsupported ingestion formats, and network problems rather than treating them as one generic client error.

For fuller user guidance in this repository, read [`docs/automation.md`](../../docs/automation.md) and the relevant page under `docs/user-guide/`. For contributor work, follow [`AGENTS.md`](../../AGENTS.md).
