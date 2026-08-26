# Dataset Model

| Field | Description | Settable |
|---|---|---|
| `dataset_name` | Human-readable name for the dataset | create, update |
| `project_id` | Project this dataset belongs to | create; later changes use `reassign_project()` |
| `measurement` | Industry-standard experiment type (e.g. `"Raman Spectroscopy"`) | create, update |
| `data_type` | Institution-specific data organization descriptor (e.g. `"ScopeFoundry H5 file"`) | create, update |
| `instrument_name` | Name of the instrument as registered in Crucible | create, update |
| `instrument_id` | Instrument identifier | create, update |
| `data_format` | File type or extension (e.g. `"h5"`, `"dat"`) | create, update |
| `session_name` | Optional tag grouping datasets collected in the same session | create, update |
| `timestamp` | When the data was collected (ISO 8601 format) | create, update |
| `public` | Whether the dataset is publicly accessible (default: `False`) | create, update |
| `owner_orcid` | Dataset owner ORCID; defaults to the authenticated user | create only; later changes use `transfer_ownership()` |
| `owner` | Flexible owner identifier or resolved owner record | create only as an ORCID, username, email, or service-account MFID |
| `unique_id` | System-assigned MFID identifier | server-assigned |
| `size` | Total file size in bytes | server-assigned |
| `creation_time` | When the record was created | server-assigned |
| `modification_time` | When the record was last modified | server-assigned |

### Relationships

| Relationship | Key(s) | Description |
|---|---|---|
| **Files** | `files` in `create()`; `add_file(dsid, file_path)` to add later | Zero or more files can be attached to a dataset. Each file is uploaded to cloud storage and triggers an ingestion process to parse metadata and generate thumbnails. |
| **Scientific metadata** | `scientific_metadata` in `create()`; `metadata` in `update_scientific_metadata()` / `replace_scientific_metadata()` | A free-form JSON object for experiment-specific parameters. Stored separately from structured fields and searchable across datasets. |
| **Thumbnails** | `add_thumbnail(dsid, image)` | Small preview images representing the data or results. Generated automatically by ingestors where supported, or uploaded manually. |
| **Samples** | `sample_id` in `add_sample(dataset_id, sample_id)` | A dataset can be linked to one or more samples, and a sample to one or more datasets — capturing which material was measured. |
| **Parent/child datasets** | `parent_dataset_id`, `child_dataset_id` in `link_parent_child()` | Datasets can be linked in a directed hierarchy to represent processing pipelines (e.g. raw → calibrated → analyzed). |

# Working with Datasets
## Creating a dataset

Pass a `Dataset` model and optional files to `client.datasets.create()`:

```python
from crucible.models import Dataset

result = client.datasets.create(
    dataset=Dataset(
        dataset_name="XRD run 5",
        measurement="X-ray diffraction",
        instrument_name="Beamline 12.3.2",
        project_id="my-project",
    ),
    files=["xrd_run5.xy"],
    scientific_metadata={"wavelength_angstrom": 0.7749, "temperature_K": 300},
    keywords=["XRD", "powder"],
)

dsid = result["dsid"]
```

You can upload multiple files in one call:

```python
result = client.datasets.create(
    dataset=Dataset(dataset_name="Multi-file dataset", project_id="my-project"),
    files=["file1.dat", "file2.dat", "thumbnail.png"],
)
```
!!! note "What happens when you call create()"
    `create()` is a client-side convenience method that chains several API calls:

    1. **POST** `/datasets` — creates the dataset record and returns a `dsid`
    2. **POST** `/resources/{dsid}/metadata` — adds scientific metadata (if provided)
    3. **POST** `/datasets/{dsid}/keywords` — adds each keyword individually (if provided)
    4. Uploads each file via GCS and triggers an ingestion request per file (if `files` is provided)


## Retrieving a dataset

```python
ds = client.datasets.get("ds-abc123")
ds_with_metadata = client.datasets.get("ds-abc123", include_metadata=True, include_links=True)
```

## Listing datasets

```python
# All datasets in a project
datasets = client.datasets.list(project_id="my-project", limit=50)

# Filter by measurement type
datasets = client.datasets.list(project_id="my-project", measurement="SEM imaging")

# Filter by keyword
datasets = client.datasets.list(project_id="my-project", keyword="gold")

# Datasets linked to a specific sample
datasets = client.datasets.list(sample_id="sm-xyz789")
```

## Updating a dataset

```python
client.datasets.update(
    "ds-abc123",
    dataset_name="XRD run 5 (corrected)",
    measurement="Powder X-ray diffraction",
)
```

Project and ownership changes use preview-first workflows. Pass `confirm=True` only after reviewing the preview:

```python
project_preview = client.datasets.reassign_project("ds-abc123", "new-project")
client.datasets.reassign_project("ds-abc123", "new-project", confirm=True)

owner_preview = client.datasets.transfer_ownership("ds-abc123", "new-owner@example.org")
client.datasets.transfer_ownership("ds-abc123", "new-owner@example.org", confirm=True)
```

## Managing access

```python
grants = client.datasets.list_access("ds-abc123")
client.datasets.set_access("ds-abc123", "users", "0000-0002-1825-0097", "editor")
client.datasets.revoke_access("ds-abc123", "users", "0000-0002-1825-0097")
client.datasets.set_public("ds-abc123")
client.datasets.unset_public("ds-abc123")
```

Normal access grants accept `viewer`, `contributor`, `editor`, or `admin`. Use `transfer_ownership()` for ownership.

## Adding files to a dataset

Add files to an existing dataset:

```python
client.datasets.add_file("ds-abc123", "additional_file.dat")
```

### How the data ingestion process works

When a file is added to a dataset, three things happen:

1. The file is uploaded to cloud storage
2. A file record is created in the database linked to the dataset
3. An ingestion request is sent to the backend

Data type-specific ingestion classes parse scientific metadata, structured metadata, and thumbnails from the file. If an ingestion class is specified via the `ingestor` parameter, that class is used. Otherwise available classes are scanned from most to least specific, if there are no ingestion classes that support the data type, then metadata and thumbnails will not be extracted from the file.

Ingestors will not overwrite the dataset attributes provided at dataset creation. Structured metadata for the primary dataset record (eg. timestamp, dataset_name, data_type) can be updated using the `client.datasets.update()` method. 

For updates to the scientific metadata, the ingestion process uses the `client.datasets.update_scientific_metadata(overwrite = False)` method. As a result, new key-value pairs parsed during the ingestion process will be appended to the existing `scientific_metadata` and newly parsed values for existing keys will be updated. If you would like to replace the entire scientific_metadata dictionary, it can be done manally with `update_scientific_metadata(overwrite=True)`.

Files are deduplicated by sha256 hash. If you add the same file twice it will not be reuploaded, but ingestion will be re-requested. This operation is **idempotent**.

!!! warning
    If two files with the same name but different contents are added to the same dataset, the upload proceeds but **replaces the original file in cloud storage**. A new file record is created with a new `mfid` and hash; the old record remains but its download link points to the new file. We are actively working on updated logic to address this.

If no ingestion class exists for your data type, reach out on [Discord](https://discord.gg/Wrepphsgbx) or contribute to the [crucible-ingestion](https://github.com/MolecularFoundryCrucible/crucible-ingestion) repository.

## Remote (non-GCS) files

Sometimes a file isn't worth (or isn't possible to) upload to GCS - it lives on Globus, at an HPC center, or on a shared filesystem. Crucible can still catalog it: it records where the file lives, but never verifies it exists, uploads it, or fetches it on your behalf.

```python
from crucible.models import AssociatedFile

client.datasets.add_remote_file(dsid, AssociatedFile(
    filename="raw_data.tar",
    storage_backend="globus",
    storage_path="https://app.globus.org/file-manager?origin_id=...&origin_path=...",
    access_note="request access via NERSC allocation X",
))
```

`storage_path` is optional - catalog the file now and set its location later with `client.files.update(mfid, storage_path=...)`.

You can also mix remote and uploaded files in one `create()` call:

```python
result = client.datasets.create(
    dataset=Dataset(dataset_name="Mixed dataset", project_id="my-project"),
    files=[
        "local_results.csv",                                     # uploaded to GCS
        AssociatedFile(filename="raw.tar", storage_backend="globus",
                       storage_path="https://app.globus.org/..."),  # cataloged only
    ],
)
```

A plain local path with `upload_files=False` is cataloged too, using its resolved absolute path and `storage_backend="local"`:

```python
result = client.datasets.create(
    dataset=Dataset(dataset_name="Cataloged only", project_id="my-project"),
    files=["/mnt/lustre/big_simulation_output.h5"],
    upload_files=False,
)
```

Downloading and ingestion are GCS-only: `client.files.download()`/`client.datasets.download()` skip non-GCS files (logging why), and the server rejects ingestion requests for them. Check `storage_backend` before assuming a file is fetchable - `crucible file get MFID` and `crucible dataset list-files` both show the backend name for non-GCS files instead of an "ingested" status.

## Scientific metadata

Scientific metadata stores experiment-specific parameters as a free-form JSON object.

```python
# Merge new keys into existing metadata (PATCH — appends/updates individual keys)
client.datasets.update_scientific_metadata(
    "ds-abc123",
    metadata={"temperature_K": 300, "pressure_bar": 1.0, "scan_rate_mV_s": 50},
)

# Retrieve it
meta = client.datasets.get_scientific_metadata("ds-abc123")

# Search across all datasets
results = client.datasets.search_scientific_metadata("temperature", limit=20)
```

`update_scientific_metadata()` merges new keys into the existing metadata (PATCH). To replace all existing metadata entirely, use `replace_scientific_metadata()`:

```python
# Replace all metadata entirely (POST)
client.datasets.replace_scientific_metadata("ds-abc123", {"new_key": "value"})
```

## Keywords

```python
client.datasets.add_keyword("ds-abc123", "annealed")
keywords = client.datasets.get_keywords(dataset_id="ds-abc123")
```

## Thumbnails

```python
client.datasets.add_thumbnail("ds-abc123", "preview.png")
thumbnails = client.datasets.get_thumbnails("ds-abc123")
```

## Downloading

```python
# Download all files for a dataset
client.datasets.download("ds-abc123", output_dir="./downloads")

# Download only matching files
client.datasets.download("ds-abc123", output_dir="./downloads", include=["*.dat"])

# Get temporary signed download URLs, keyed by file MFID
links = client.datasets.get_download_links("ds-abc123")
```

## Parent-child relationships between datasets

Link datasets to represent a processing pipeline:

```python
# raw → processed
client.datasets.link_parent_child(parent_dataset_id=raw_dsid, child_dataset_id=processed_dsid)

# List relationships
parents = client.datasets.list_parents("ds-processed")
children = client.datasets.list_children("ds-raw")
```

## Requesting dataset deletion

```python
client.deletions.request("ds-abc123", reason="Superseded dataset")
```

!!! note
    A deletion request does not immediately remove the resource. An admin must approve it before permanent deletion.
