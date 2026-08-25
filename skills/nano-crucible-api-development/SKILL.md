---
name: nano-crucible-api-development
description: Implement or review nano-crucible Python API changes across client transport, Pydantic models, and resource namespaces. Use for work in crucible/client.py, crucible/models.py, or crucible/resources/; do not use for server implementation or CLI-only presentation changes.
---

# nano-crucible API development

Follow the repository-wide rules in [`AGENTS.md`](../../AGENTS.md), then use this skill for the Python client API portion of a change.

## Trace the complete contract

Inspect the target resource method, its Pydantic model, neighboring methods, unit tests, API documentation, and any CLI caller before editing. Treat the server repository as read-only evidence when it is available. Do not infer an endpoint contract solely from a stale client example.

When adding a new resource namespace, export the operations class from `crucible/resources/__init__.py` and construct it in `CrucibleClient.__init__`. Keep operations on the narrowest resource namespace; add a root-client method only when the behavior genuinely spans resources.

## Preserve response and payload behavior

- Filter `None` values from request payloads unless the endpoint distinguishes an explicit null from an omitted field.
- Use `BaseResource._paginate()` for paginated envelopes. Datasets and samples use cursor pagination; other current resources use offsets.
- When a response has the shape of an existing dataset, sample, or file model, pass it through the resource's `_parse()` method before returning it.
- Most resource models allow extra fields. Removing a declared field does not prevent callers from sending it, so search model constructors, payload builders, CLI code, parsers, cast, tests, and docs for the old field.
- Preserve intentional compatibility with `_deprecated` or `_removed` helpers when changing a public method or parameter. Do not retain an alias silently.
- Keep endpoint-specific handling narrow. Do not hide authorization, schema, or server errors behind broad exception handling.

If the change also adds or alters a command, load [`nano-crucible-cli-development`](../nano-crucible-cli-development/SKILL.md).

## Verify without live side effects

Add or update unit tests with a mocked client request boundary. Cover the HTTP method, endpoint, parameters or JSON payload, response-envelope handling, model normalization, and compatibility warning when relevant. Use a live integration test only when the user authorizes persistent test-server mutations.

Update the affected docstring, API reference page, examples, and `docs/changelog.md` for user-visible behavior. Run the focused unit tests, then `pytest tests/unit -q` and `mkdocs build`.
