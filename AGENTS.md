# Repository guide for coding agents

This file is the canonical repository guidance for any coding agent. Tool-specific instruction files should point here instead of duplicating it.

## Project overview

`nano-crucible` is the Python client library and command-line interface for Crucible, the Molecular Foundry's scientific data platform.

- Distribution: `nano-crucible`
- Import package: `crucible`
- CLI entry point: `crucible.cli:main`
- Supported Python: 3.8 and newer
- Default API: `https://crucible.lbl.gov/api/v2`
- Documentation: MkDocs Material, configured in `mkdocs.yml`

The companion server and ingestion repositories are useful references when they are available, but they are separate projects. Do not edit them as part of a client task unless the user explicitly expands the scope.

## Repository map

- `crucible/client.py`: HTTP session, authentication, retries, generic operations, and resource namespace construction.
- `crucible/models.py`: Pydantic request and response models.
- `crucible/resources/`: namespaced Python API (`client.datasets`, `client.samples`, `client.projects`, and peers).
- `crucible/resources/gcs/`: upload and download implementation.
- `crucible/cli/`: argparse command modules and terminal display helpers.
- `crucible/config/`: config-file and environment-variable handling.
- `crucible/parsers/`: file parsers that prepare datasets for upload.
- `crucible/cast/`: declarative `.crux` recipe loading, building, and execution.
- `tests/unit/`: mocked, local tests.
- `tests/integration/`: live-API tests that create real records.
- `docs/`: published user and API documentation.
- `skills/nano-crucible/`: operational guidance for agents helping users use the client.
- `skills/nano-crucible-*-development/`: subsystem-specific guidance for agents developing the package.

## Skill routing

Use the smallest relevant development skill and combine skills only when a change crosses subsystem boundaries:

- Python models, transport, or resource methods: `skills/nano-crucible-api-development/SKILL.md`
- CLI commands, help, display, or completion: `skills/nano-crucible-cli-development/SKILL.md`
- Client-side dataset parsers or parser discovery: `skills/nano-crucible-parser-development/SKILL.md`
- `.crux` recipes, builders, lock files, execution, or resume behavior: `skills/nano-crucible-cast-development/SKILL.md`
- Configuring or operating Crucible on a user's behalf: `skills/nano-crucible/SKILL.md`

This file remains authoritative for shared repository rules. Skills add conditional subsystem guidance and do not expand permission to mutate the live API.

## Development workflow

Install an editable development environment with:

```bash
python -m pip install -e ".[dev,docs]"
```

Run local validation with:

```bash
pytest tests/unit -q
mkdocs build
```

Use the smallest relevant test set while iterating, then run all unit tests. Treat warnings from a strict documentation build as useful cleanup signals, but do not assume all pre-existing annotation warnings belong to the current change.

Do not run `tests/integration/` merely as routine validation. Those tests require credentials, call a live API, create persistent records, and do not clean them up. Run them only when the task needs live verification and the user has authorized that side effect. Use the `crucible-test` project, never a production project.

`crucible/parsers/` and `crucible/cast/` have little dedicated coverage. Changes there need a mocked smoke test or a new unit test. Exercise all stateful paths affected by the change, including resumption paths in `cast`, and search every call site of renamed or removed symbols.

## Implementation conventions

- Public operations belong under a resource namespace rather than on the root client unless they genuinely span resources.
- Resource methods returning dataset, sample, or file records should validate raw API dictionaries through their Pydantic model (`_parse`) so aliases are normalized and extra server fields are preserved.
- Most resource models use `extra="allow"`. Removing a field from a model does not prove callers stopped sending it; search all model constructors and API payload builders for stale fields.
- `AVAILABLE_INGESTORS` is a client-side completion list, not an authoritative statement of what the server currently supports.
- `ingestor=None` means server-side auto-detection. The generic `ApiUploadIngestor` is not currently a fallback for unknown formats.
- Preserve supported Python 3.8 syntax unless the project explicitly raises its minimum version.
- Keep the library quiet by default. Use package logging rather than unconditional prints; CLI presentation belongs in `crucible/cli/`.
- Never log, print, commit, or place real API keys in examples.

## Documentation and compatibility

Update documentation in the same change as public behavior. Prefer examples that use the current namespaced API (`client.datasets.get`, not removed flat methods) and verify CLI examples against `crucible <command> --help`.

`docs/cli/reference.md` is the canonical CLI command inventory. Keep `crucible/cli/README.md` as a contributor pointer and do not duplicate command tables there.

For a user-visible change, add one short line under `## Unreleased` in `docs/changelog.md`, using only the relevant `Added`, `Changed`, or `Fixed` section. Describe what changed for users, not its implementation. Pure internal refactoring does not need a changelog entry.

When changing a public signature, consider deprecation compatibility and update docstrings, API docs, CLI help, examples, and tests together. Do not silently invent server behavior to compensate for a client/server mismatch.

## Git safety

The shared development branch is `dev`; the release branch is `main`. Do not switch branches, commit, push, publish, or modify companion repositories unless the user explicitly asks. Preserve unrelated working-tree changes, including local agent settings and installed skills.
