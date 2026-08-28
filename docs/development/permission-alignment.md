# Permission-control alignment decisions

This document records the decisions and implementation work used to align `nano-crucible` with the permission-control changes on the `crucible-api` `feat/permission-roles` branch. It is a development record rather than user documentation.

Implementation follows the repository ownership boundaries and decisions recorded below.

## Repository ownership

- The nano-crucible agent owns changes in this client repository.
- The API agent owns changes in the `crucible-api` repository.
- The nano-crucible agent may inspect API source, schemas, tests, and documentation as read-only contract evidence, but must not modify the API repository.
- Decisions in this document form the shared coordination contract. Each agent should report completed commits and any discovered contract conflict before the other side relies on the change.

## Status key

- `Open`: observed and ready for discussion
- `Decided`: approach agreed, implementation not started
- `Deferred`: intentionally postponed pending another design or dependency
- `Partial`: implemented for the current contract with explicitly retained follow-up work
- `Implemented`: code and documentation updated
- `Verified`: relevant local checks passed

## Recommended discussion order

1. Define whether `owner` is exclusive.
2. Align dataset CLI update fields.
3. Normalize project member mutation responses.
4. Make flexible identifiers explicit.
5. Add instrument ownership transfer to the CLI.
6. Scope resource operations to valid namespaces.
7. Correct the API contract document.
8. Align client API and user documentation.
9. Close focused verification gaps.

## 1. Define whether `owner` is exclusive

Status: `Implemented`

### Issue

The permission design says that a project has exactly one owner and that ownership changes go through `POST /resources/{mfid}/transfer_ownership`. However, `PUT /resources/{mfid}/access/{kind}/{principal}` currently accepts `effective_permission="owner"`. An existing owner or platform administrator can therefore create another owner-level ACL entry without using the ownership-transfer workflow.

For projects, this can create an owner-level ACL outside the project membership record that stores the canonical project lead. A later transfer updates the project-group owner but does not necessarily remove the additional direct owner grant. The CLI also advertises `owner` as a normal permission for `access grant`.

### Best solution

Treat `owner` as an exclusive ownership state, not a generally grantable permission:

- Reject `effective_permission="owner"` in the generic access-grant route with a conflict response that directs callers to `transfer_ownership`.
- Keep internal creation and migration code responsible for establishing the initial owner.
- Remove `owner` from the CLI's advertised `access grant` values.
- Add server coverage proving that generic ACL writes cannot create or replace an owner and that ownership transfer remains the only public ownership mutation.

### Alternative

If multiple owner-level principals are intentional, revise the ownership model and documentation to distinguish the canonical owner from principals with owner-equivalent permission. The transfer code must then define whether those additional grants survive a transfer. This is more complex and weakens the current single-owner invariant.

### Decision

`owner` is exclusive and may be assigned only through the ownership-transfer workflow. Generic access grants will allow permissions up to `admin`, reject `owner`, and direct callers to `transfer_ownership`. The CLI will follow the same rule. Internal creation and migration code may establish the initial owner.

## 2. Align dataset CLI update fields

Status: `Implemented`

### Issue

The client CLI field registry does not match the server's `DatasetUpdate` schema:

- `description` is exposed as editable but is rejected by the server.
- `data_format` is accepted by the server but marked non-editable by the client.
- `instrument_id` is accepted by the server but missing from the dataset CLI field registry.

This can make a documented or interactive client operation fail with 422 while hiding valid update fields.

The API schema comparison also confirms that `description` is absent from `DatasetCreate`, `DatasetUpdate`, `DatasetRead`, and `DatasetResponse`. It is therefore an orphaned client CLI field rather than a missing response declaration.

The client `Dataset` model also relies on permissive extra-field handling for declared API fields:

- `instrument_id`, present in create, update, and read schemas.
- `owner`, used as a flexible creation identifier and as the resolved owner object in `DatasetResponse`.

The dual-purpose `owner` field is tracked under issue 4 because its request and response types require a broader model decision.

At review time, `source_folder` remained in the API's dataset create and read schemas, core database model, and revision-record serialization, but it was deprecated as a dataset field. The API implementation removed it from create and read schemas and stopped serializing it in new revision records. File location belongs to associated-file records. A parser may retain a local working-directory variable for file discovery without sending it as dataset metadata.

### Best solution

Make the client registry match the deployed update contract exactly:

- Remove `description` from editable dataset fields unless the API deliberately adds it.
- Mark `data_format` as editable.
- Add `instrument_id` as an editable field while retaining `instrument_name` for compatibility.
- Declare `instrument_id` on the client `Dataset` model so the supported field does not depend on extra-field handling.
- Remove deprecated `source_folder` from the API dataset create and read schemas and from dataset revision-record serialization. Treat removal of the underlying database column as separate migration work.
- Use one explicit client-side update-field definition for CLI validation, edit prompts, help text, and documentation.

Runtime OpenAPI discovery is not recommended because CLI behavior should remain predictable offline and across server versions.

### Decision

Remove dataset `description` from the CLI, make `data_format` editable, add editable and explicitly modeled `instrument_id`, retain `instrument_name` for compatibility, and keep the CLI registry aligned with the API update schema. Do not add `source_folder` to the client model. Remove it from the API dataset create and read contract because file locations now belong to associated-file records. Address strict extra-field handling under issue 4.

## 3. Normalize project member mutation responses

Status: `Implemented`

### Issue

The server now returns the complete `AccessGroupMemberRead` list from project member POST, PATCH, and DELETE operations. The client parses POST and PATCH results into `ProjectMember` models, but `projects.remove_user()` still declares a dictionary return value, describes a response message, and returns raw response data.

The email and username identification path also returns raw data rather than the same model list as the ORCID path.

### Best solution

Make every project member mutation return `List[ProjectMember]`:

- Parse add, update-role, and remove responses through one private member-list parser.
- Apply the same behavior to ORCID, username, and email identification paths.
- Update docstrings, CLI callers, API reference, and compatibility notes together.

### Decision

Parse every project member mutation response through one shared member-list parser and return `List[ProjectMember]` consistently from add, role-update, and removal operations for ORCID, username, and email identification paths. Correct the annotations and docstrings without changing CLI presentation unless a caller needs the returned list.

## 4. Make flexible identifiers explicit

Status: `Implemented`

### Issue

The server accepts flexible `owner` fields for dataset and sample creation and a flexible `project_lead` field for project creation. The current Pydantic models accept these values only because extra fields are allowed. Consequently, IDE completion, type checking, generated schemas, and the model reference do not expose them.

The broader read-model comparison found additional declarations that are preserved only as extra fields or raw dictionaries:

- `Dataset` does not declare `instrument_id`.
- `Sample` does not declare the resolved `owner` response.
- `Project` does not declare its response `unique_id` or its create-time `project_lead` field.
- `Instrument` does not declare the response `status` field.
- The API has a distinct `ProjectMinimalRead` response for instrument-associated callers, while the client represents both full and minimal project responses as raw dictionaries.

CLI support is incomplete:

- Dataset and sample creation have no option for creating on behalf of a flexible owner.
- `project create --lead` accepts email or ORCID in its help and routes any non-ORCID value through the legacy email field, so a username does not use the flexible server-side resolver.

### Best solution

First make the existing public models explicit without breaking current callers:

- Add a declared `owner` field to `Dataset` and `Sample` that can represent a creation identifier or a resolved owner response.
- Add a declared `instrument_id` field to `Dataset`.
- Add a declared `project_lead: Optional[str]` field to `Project`.
- Add the API response `unique_id` to `Project` and `status` to `Instrument`.
- Validate that callers do not provide both flexible and legacy identifier fields before sending the request, producing a clear local error.
- Keep flexible dataset and sample owners in the Python API only for now, without adding parser or CLI plumbing.
- Make `project create --lead` send `project_lead` directly and describe it as accepting ORCID, username, or email.

Retain `extra="allow"` for the current combined models to preserve forward compatibility and avoid expanding this permission work into a request/response model redesign. Separating strict request models from forward-compatible response models remains a possible later improvement.

### Compatibility decision

Keep permissive extra-field handling for the time being. Declare fields that are part of the known public contract, but do not make strict request/response model separation a prerequisite for this work.

### Decision

Keep `extra="allow"` while explicitly declaring the known public fields. Add flexible or resolved `owner` fields to `Dataset` and `Sample`, add `project_lead` and response `unique_id` to `Project`, add response `status` to `Instrument`, and validate conflicting flexible and legacy identifiers locally. Keep flexible dataset and sample owner selection in the Python API only, with no new CLI option or parser changes. Make `project create --lead` send `project_lead` directly. Continue representing `ProjectMinimalRead` responses as raw dictionaries for now.

## 5. Add instrument ownership transfer to the CLI

Status: `Partial`

### Issue

The ownership-transfer endpoint supports instruments, but the client deliberately does not expose instrument ownership transfer while its semantics remain unsettled. Dataset, sample, and project commands already expose the workflow.

Instrument records also have an `owner` string used as descriptive facility or organization data. The ownership-transfer route changes the owner-level ACL but does not update this free-text field. The CLI and documentation must distinguish permission ownership from the descriptive instrument owner value.

### Best solution

Add `instrument transfer-ownership INSTRUMENT_MFID NEW_OWNER [--confirm]` with the same preview-first behavior and output as the other resources. State that it transfers permission ownership and does not rewrite the instrument's descriptive `owner` field.

Use the existing command pattern for the initial implementation. A shared ownership-command registrar can be considered later, but is not required for this permission alignment.

### Decision

Defer the CLI command until the instrument API clearly defines the relationship between permission ownership and the descriptive `Instrument.owner` field. Make no client or CLI change for this item yet.

## 6. Scope resource operations to valid namespaces

Status: `Implemented`

### Issue

ACL, ownership-transfer, and project-reassignment methods currently live on `BaseResource`. Every resource namespace therefore exposes them, including account, users, files, ingestion, deletion, graphs, access groups, and service accounts. Many of those combinations are invalid or misleading. Project reassignment is specifically valid only for datasets and samples.

### Best solution

Split cross-resource behavior into capability mixins:

- `AccessControlOperations` for resource types supporting ACL and public access.
- `OwnershipOperations` for datasets, samples, and projects. Instrument ownership remains deferred.
- `ProjectAssignmentOperations` for datasets and samples only.

Compose only the appropriate mixins into each operations class. Keep pagination, transport delegation, and scientific metadata behavior in the base class where they are genuinely shared.

### Alternative

Define thin forwarding methods directly on each supported resource class. This is more repetitive but simpler than mixins. Leaving the methods on every namespace is not recommended because it makes invalid operations appear supported.

### Decision

Introduce small, stateless capability mixins for access control, ownership transfer, and project assignment. Compose access control into datasets, samples, projects, and instruments; compose project assignment only into datasets and samples; and compose ownership into datasets, samples, and projects. Defer instrument ownership composition until the instrument API semantics are settled. Preserve existing valid method locations and remove accidental methods from unsupported namespaces.

## 7. Correct the API contract document

Status: `Implemented`

### Issue

`crucible-api/docs/permission_system_api_changes.md` does not exactly match the current server implementation:

- It lists a singular `GET /resources/{mfid}/access/{kind}/{principal}`, but the GET operation is the collection route `GET /resources/{mfid}/access`.
- It says DELETE access and public-access responses contain `effective_permission`, but the implementations return detail messages.
- Its dataset update field list omits the accepted `instrument_id` field.
- It describes dataset and sample create request schemas as unchanged after adding the flexible `owner` field.
- The transfer route's source docstring still says dataset and sample PATCH rejection is not yet implemented.

### Best solution

Update the API contract document from the current route decorators and Pydantic schemas, then regenerate or inspect local OpenAPI as a consistency check. Describe response shapes per HTTP method instead of grouping routes with different responses into one sentence.

The server source docstring should be corrected in the same API-repository change.

### Decision

Correct the API contract and source docstring as part of the API agent's server-side implementation. The API agent will cross-check route declarations, schemas, OpenAPI, and server tests. The nano-crucible agent will not edit the API repository and will use the corrected contract and reported API commit as the basis for client implementation and documentation.

## 8. Align client API and user documentation

Status: `Implemented`

### Issue

The client API reference omits most new permission methods, and several user guides describe pre-change behavior:

- Dataset and sample guides say project and owner fields can be changed through ordinary update calls.
- The project guide says `project_id` is creation-only and does not cover ownership transfer, member roles, or member visibility.
- Sample creation examples use the removed keyword-based calling convention and an incorrect response identifier.
- Project member examples treat `ProjectMember` models as dictionaries.
- Instrument permission and ownership behavior remains unfinished and should not be advertised to users yet.

### Best solution

After the preceding behavior decisions are implemented, update documentation from the resulting public contract:

- Add completed access, publication, ownership, reassignment, and membership-role methods to the API reference.
- Correct model field tables and creation/update examples.
- Explain preview and confirmation semantics for ownership transfer and project reassignment.
- Keep CLI command inventory in `docs/cli/reference.md` and link to it rather than duplicating command tables.
- Exclude unfinished instrument permission and ownership features from user-facing API, CLI, and guide documentation until the instrument API is settled and implemented end to end.

Documentation should follow implementation decisions so it does not need repeated rewrites while the contract remains unsettled.

### Decision

Update client documentation after the corresponding implemented behavior is stable. Cover completed dataset, sample, and project permission workflows, correct stale model tables and examples, keep the canonical CLI inventory in `docs/cli/reference.md`, and avoid documenting unfinished instrument permission or ownership features.

## 9. Close focused verification gaps

Status: `Deferred`

### Issue

The existing focused mocked permission tests do not currently verify several identified boundaries:

- Generic ACL handling of `owner`.
- Dataset CLI update-field parity.
- Parsed project removal responses across all identifier forms.
- Flexible owner and project-lead payloads and mutual exclusion.
- Instrument ownership transfer CLI wiring.
- Absence of invalid methods from unsupported resource namespaces.

### Best solution

Add or update focused mocked tests as each approved behavior is implemented. Keep live integration tests out of the routine workflow because these operations mutate persistent authorization and ownership state. Use server route tests for authorization invariants and client unit tests for payload, parsing, and CLI wiring.

### Decision

Focused mocked coverage now exercises canonical ACL fields and payloads, effective dataset access, identifier dispatch, typed access selectors, project member parsing, and canonical membership targets. Instrument ownership remains deferred, and broader CLI field-parity and capability-absence coverage remains future work. Do not run live integration tests without explicit authorization.

## 10. Complete the staged client rollout

Status: `Implemented` in Nano; release gated on the API rollout

### Issue

The staging API already uses canonical ACL fields and the effective-access response, while repeated typed access selectors and universal public-safe email redaction belong to the next API deployment candidate. Older API versions silently ignore unknown collection query parameters, so a client cannot safely detect unsupported typed selectors from a successful response.

### Decision

- Use `principal_id`, `principal_type`, and `permission` for ACL responses and send `permission` in grant bodies.
- Report `effective_access` directly rather than reconstructing legacy read and write Booleans.
- Accept repeated `accessible_to_user` and `accessible_to_project` selectors on top-level dataset, sample, and project collections, with at most ten selectors and intersection semantics.
- Keep legacy resource and generic membership helpers as deprecated compatibility surfaces while directing new work to canonical ACL, project membership, and instrument service-account operations.
- Resolve project membership usernames and emails through exact user collection lookups, then send the returned canonical user identifier to the membership route.
- Treat directory, project lead, project member, instrument operator, and access-group member records as public-safe and email-free.
- Apply current slug validation only to create and rename operations so existing out-of-range project and instrument slugs remain readable.
- Treat graph and relationship results as permission-filtered authorized views.

Deploy and verify the API candidate in staging, record its commit and deterministic OpenAPI artifact, deploy the API to production, and only then release the Nano version that sends typed selectors. This ordering prevents older servers from silently ignoring selector parameters and returning the wrong authorized collection.
