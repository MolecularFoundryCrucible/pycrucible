# CLI command reference

This page is the canonical command inventory for the Crucible CLI. Use `crucible <command> --help` or `crucible <resource> <action> --help` for the exact arguments, aliases, defaults, and examples supported by the installed version.

## Global options

| Option | Description |
|---|---|
| `--version` | Print the installed client version and exit |
| `--debug` | Enable Crucible debug logging; place it before the command |

Running `crucible` without a command starts the interactive shell. See the [CLI overview](index.md) for setup, shell completion, and interactive usage.

## Dataset commands

| Command | Description |
|---|---|
| `dataset list` | List datasets with project, measurement, keyword, session, format, type, instrument, and name-pattern filters |
| `dataset get ID` | Show a dataset, its files, and linked resources |
| `dataset create -i FILE` | Create a dataset and upload or catalog files |
| `dataset update ID` | Update model fields or scientific metadata |
| `dataset edit ID` | Edit dataset fields interactively |
| `dataset reassign-project ID PROJECT` | Move a dataset to another project |
| `dataset transfer-ownership ID USER` | Transfer dataset ownership |
| `dataset delete ID` | Permanently delete a dataset after confirmation |
| `dataset search QUERY` | Search dataset names |
| `dataset search-metadata QUERY` | Search scientific metadata; `search-md` is an alias |
| `dataset link` | Link parent and child datasets |
| `dataset remove-child` | Remove a dataset parent-child link |
| `dataset list-parents ID` | List parent datasets |
| `dataset list-children ID` | List child datasets |
| `dataset add-sample ID` | Link a sample to a dataset |
| `dataset remove-sample ID` | Unlink a sample from a dataset |
| `dataset list-samples ID` | List samples linked to a dataset |
| `dataset add-file ID FILE` | Upload files to an existing dataset |
| `dataset list-files ID` | List associated files and available download links |
| `dataset download ID` | Download dataset files with optional include and exclude patterns |
| `dataset ingestion ID` | Show ingestion requests for a dataset |
| `dataset add-keyword ID WORD` | Add a keyword |
| `dataset list-keywords [ID]` | List dataset keywords and usage counts |
| `dataset list-access-groups ID` | List access groups associated with a dataset |
| `dataset add-access-group ID GROUP` | Grant an access group access to a dataset |
| `dataset access ...` | List, grant, or revoke direct access entries |
| `dataset publish ID` | Make a dataset publicly viewable |
| `dataset unpublish ID` | Remove public access from a dataset |
| `dataset parsers` | List installed client-side parsers |
| `dataset ingestors` | List server-advertised ingestion classes |

Common creation example:

```bash
crucible dataset create -i data.csv -pid my-project \
    -n "XRD measurement" -m "X-ray diffraction" \
    --metadata '{"temperature_K": 300}' --keywords "XRD,powder"
```

Fields normally updated through `dataset update --set` include `dataset_name`, `measurement`, `data_type`, `session_name`, `instrument_name`, `instrument_id`, `data_format`, `timestamp`, and `public`. Use `reassign-project` and `transfer-ownership` for project and owner changes.

## Sample commands

| Command | Description |
|---|---|
| `sample list` | List samples with project, name, type, and name-pattern filters |
| `sample get ID` | Show a sample and its linked resources |
| `sample create` | Create a sample |
| `sample update ID` | Update sample fields or scientific metadata |
| `sample edit ID` | Edit sample fields interactively |
| `sample reassign-project ID PROJECT` | Move a sample to another project |
| `sample transfer-ownership ID USER` | Transfer sample ownership |
| `sample search QUERY` | Search sample names |
| `sample search-metadata QUERY` | Search scientific metadata; `search-md` is an alias |
| `sample link` | Link parent and child samples |
| `sample remove-child` | Remove a sample parent-child link |
| `sample list-parents ID` | List parent samples |
| `sample list-children ID` | List child samples |
| `sample add-dataset ID` | Link a dataset to a sample |
| `sample remove-dataset ID` | Unlink a dataset from a sample |
| `sample list-datasets ID` | List datasets linked to a sample |
| `sample access ...` | List, grant, or revoke direct access entries |
| `sample publish ID` | Make a sample publicly viewable |
| `sample unpublish ID` | Remove public access from a sample |

Fields normally updated through `sample update` include `sample_name`, `sample_type`, `description`, `timestamp`, and `public`. Use `reassign-project` and `transfer-ownership` for project and owner changes.

## Project commands

| Command | Description |
|---|---|
| `project list` | List accessible projects |
| `project get PROJECT` | Show a project by MFID or project slug, optionally with its members |
| `project create` | Create a project |
| `project update ID` | Update a project record or scientific metadata |
| `project edit ID` | Edit project fields interactively |
| `project search QUERY` | Search project names and IDs |
| `project search-metadata QUERY` | Search scientific metadata; `search-md` is an alias |
| `project list-users ID` | List project members and roles |
| `project add-user ID` | Add a user to a project |
| `project remove-user ID` | Remove a user from a project |
| `project update-user-role ID` | Change a project member's role |
| `project transfer-ownership ID USER` | Transfer project ownership |
| `project request-join ID` | Request membership in a project |
| `project list-join-requests ID` | List project join requests |
| `project access ...` | List, grant, or revoke direct access entries |
| `project publish ID` | Make a project publicly viewable |
| `project unpublish ID` | Remove public access from a project |

The `access grant` commands accept `viewer`, `contributor`, `editor`, or `admin`. Use the resource's `transfer-ownership` command to change ownership.

## Instrument commands

| Command | Description |
|---|---|
| `instrument list` | List instruments |
| `instrument get INSTRUMENT` | Show an instrument by MFID or instrument slug |
| `instrument create` | Register an instrument |
| `instrument update ID` | Update an instrument record or scientific metadata |
| `instrument edit ID` | Edit instrument fields interactively |
| `instrument search QUERY` | Search names, types, and manufacturers |
| `instrument search-metadata QUERY` | Search scientific metadata; `search-md` is an alias |

## User commands

Most user-management commands require administrator permissions.

| Command | Description |
|---|---|
| `user get USER` | Show a user by ORCID, username, or email |
| `user search QUERY` | Search names and usernames |
| `user list` | List users |
| `user create` | Create a user |
| `user update USER` | Update a user record |
| `user edit USER` | Edit a user record interactively |
| `user list-datasets USER` | List datasets accessible to a user |
| `user check-access USER DATASET` | Check a user's dataset access |
| `user list-access-groups USER` | List a user's access groups |
| `user add-access-group USER GROUP` | Add a user to an access group |
| `user remove-access-group USER GROUP` | Remove a user from an access group |
| `user list-projects USER` | List a user's projects |

## File commands

File commands operate on individual file MFIDs. Dataset-scoped file operations remain available under `dataset`.

| Command | Description |
|---|---|
| `file list` | List files globally or within a dataset |
| `file get ID` | Show file metadata and a download link when available |
| `file download ID` | Download one file |
| `file ingestion ID` | Show ingestion requests for a file |
| `file request-ingestion ID` | Request or repeat ingestion for a cataloged file |
| `file delete ID` | Delete a file |

## Ingestion commands

| Command | Description |
|---|---|
| `ingestion list` | List ingestion requests |
| `ingestion get ID` | Show an ingestion request |
| `ingestion wait ID` | Wait for an ingestion request to finish |
| `ingestion list-ingestors` | List available ingestion classes |

## Service-account commands

`sa` is an alias for `service-account`. These commands require administrator permissions.

| Command | Description |
|---|---|
| `sa create` | Create a service account |
| `sa rotate-key USER` | Generate a new key and invalidate the previous key |
| `sa get USER` | Show a service account |
| `sa list` | List service accounts |
| `sa update USER` | Update a service account |
| `sa edit USER` | Edit a service account interactively |
| `sa list-access-groups USER` | List access groups for a service account |
| `sa add-access-group USER GROUP` | Add a service account to an access group |
| `sa remove-access-group USER GROUP` | Remove a service account from an access group |

## Access-group commands

`ag` is an alias for `access-group`.

| Command | Description |
|---|---|
| `ag request GROUP` | Request to join an access group or project |
| `ag mine` | List the current user's join requests |
| `ag list` | List join requests for review |
| `ag get ID` | Show a join request |
| `ag approve ID...` | Approve pending join requests |
| `ag reject ID...` | Reject pending join requests |

## Account commands

These commands operate on the currently authenticated account and do not require administrator permissions.

| Command | Description |
|---|---|
| `account show` | Show the current profile |
| `account update` | Update profile fields |
| `account edit` | Edit the current profile interactively |
| `account api-key` | Show the current API key |
| `account verify` | Check API-key validity and expiry |

Treat output from `account api-key` as a secret. Do not include it in logs, issue reports, or agent prompts.

## Deletion commands

The deletion-request workflow is separate from direct permanent deletion. Review and audit commands require administrator permissions.

| Command | Description |
|---|---|
| `deletion request RESOURCE` | Request deletion of a dataset or sample |
| `deletion list` | List deletion requests |
| `deletion get ID` | Show a deletion request |
| `deletion approve ID...` | Approve pending requests |
| `deletion reject ID...` | Reject pending requests |
| `deletion delete RESOURCE` | Permanently delete a resource |
| `deletion list-deleted` | List permanent-deletion audit records |
| `deletion get-deleted ID` | Show a permanent-deletion audit record |

## Cast command

`cast` loads a declarative `.crux` recipe containing datasets, samples, files, and links.

| Command | Description |
|---|---|
| `cast FILE` | Execute a recipe |
| `cast FILE --validate` | Validate references and cycles without executing |
| `cast FILE --dry-run` | Preview execution without API mutations |
| `cast FILE --show` | Show the plan and lock status |
| `cast FILE --force` | Clear the lock and recreate entities |
| `cast FILE --reupload` | Re-upload files without recreating records |

## Configuration and cache

| Command | Description |
|---|---|
| `config init` | Run interactive configuration setup |
| `config show` | Show the current configuration |
| `config get KEY` | Print one configuration value |
| `config set KEY VALUE` | Set one configuration value |
| `config path` | Show the configuration-file path |
| `config edit` | Edit the configuration file |
| `cache show` | Show cache location and disk usage |
| `cache clear` | Remove cached files by dataset, age, or all entries |

Configuration values can come from environment variables, the platform-specific config file, or defaults. Avoid displaying `api_key` in shared terminals or logs.

## General utility commands

| Command | Description |
|---|---|
| `status` | Check API reachability, database health, and authentication |
| `whoami` | Show the identity associated with the configured key |
| `get ID` | Show a dataset or sample after detecting its resource type |
| `edit ID` | Edit a dataset, sample, or instrument after detecting its type |
| `download ID` | Save a record and, for datasets, associated files |
| `link` | Link parent-child resources or associate a dataset and sample |
| `unlink ID1 ID2` | Remove a resource relationship |
| `tree ID` | Display connected ancestors and descendants |
| `open [ID]` | Open the Graph Explorer or print its URL |
| `qr ID` | Print a terminal QR code for an MFID |
| `completion [SHELL]` | Generate and install completion for bash, zsh, fish, or tcsh |
| `upload ...` | Deprecated upload command; use `dataset create` |

## Deprecated aliases

| Old form | Current form |
|---|---|
| `dataset update-metadata` | `dataset update --metadata` |
| `dataset get-keywords` | `dataset list-keywords` |
| `sample link-dataset` | `sample add-dataset` |
| `user get-access-groups` | `user list-access-groups` |
| `user get-projects` | `user list-projects` |
| `project get-users` | `project list-users` |

Deprecated forms remain available for compatibility but emit a warning. New documentation and scripts should use the current forms.
