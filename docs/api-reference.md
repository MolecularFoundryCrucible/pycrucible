# API Reference

Complete reference for all PycrucibleClient functions organized by category.

## Table of Contents

- [Client Initialization](#client-initialization)
- [Authentication & Account](#authentication--account)
- [Project Management](#project-management)
- [User Management](#user-management)
- [Dataset Operations](#dataset-operations)
- [File Management](#file-management)
- [Metadata Management](#metadata-management)
- [Sample Management](#sample-management)
- [Instrument Management](#instrument-management)
- [Processing Workflows](#processing-workflows)
- [Utilities](#utilities)

## Client Initialization

### CrucibleClient

```python
CrucibleClient(api_url: str, api_key: str)
```

Initialize the Crucible API client for accessing the Molecular Foundry data lakehouse.

**Parameters:**
- `api_url` (str): Base URL for the Crucible API
- `api_key` (str): API key for authentication

**Returns:**
- CrucibleClient instance

**Example:**
```python
client = CrucibleClient(
    api_url="https://crucible-api.example.com",
    api_key="your-api-key-here"
)
```

---

## Authentication & Account

### \_request

```python
_request(method: str, endpoint: str, **kwargs) -> Any
```

Make an HTTP request to the API (internal method).

**Parameters:**
- `method` (str): HTTP method (get, post, put, delete)
- `endpoint` (str): API endpoint path
- `**kwargs`: Additional arguments to pass to requests

**Returns:**
- Parsed JSON response

---

## Project Management

### list_projects

```python
list_projects() -> List[Dict]
```

List all accessible projects.

**Returns:**
- `List[Dict]`: Project metadata including project_id, project_name, description, project_lead_email

**Example:**
```python
projects = client.list_projects()
for project in projects:
    print(f"Project: {project['project_name']} (ID: {project['project_id']})")
```

### get_project

```python
get_project(project_id: str) -> Dict
```

Get details of a specific project.

**Parameters:**
- `project_id` (str): Unique project identifier

**Returns:**
- `Dict`: Complete project information

### add_project

```python
add_project(project_info: Dict) -> Dict
```

Add a new project to the system.

**Parameters:**
- `project_info` (Dict): Project information with required fields:
  - `project_id`: str
  - `organization`: str
  - `project_lead_email`: str
  - Optional fields: status, title, project_lead_name

**Returns:**
- `Dict`: Created project object

### get_project_users

```python
get_project_users(project_id: str) -> List[Dict]
```

Get users associated with a project (admin access required).

**Parameters:**
- `project_id` (str): Unique project identifier

**Returns:**
- `List[Dict]`: Project team members (excludes project lead)

---

## User Management

### get_user

```python
get_user(orcid: str) -> Dict
```

Get user details by ORCID (admin access required).

**Parameters:**
- `orcid` (str): ORCID identifier (format: 0000-0000-0000-000X)

**Returns:**
- `Dict`: User profile with orcid, name, email, timestamps

### get_user_by_email

```python
get_user_by_email(email: str) -> Dict
```

Get user details by email address.

**Parameters:**
- `email` (str): Email address to search for

**Returns:**
- `Dict`: User information if found, searches both email and lbl_email fields

### add_user

```python
add_user(user_info: Dict) -> Dict
```

Add a new user to the system (admin access required).

**Parameters:**
- `user_info` (Dict): User information including 'projects' key

**Returns:**
- `Dict`: Created user object

---

## Dataset Operations

### list_datasets

```python
list_datasets(sample_id: Optional[str] = None, **kwargs) -> List[Dict]
```

List datasets with optional filtering.

**Parameters:**
- `sample_id` (str, optional): If provided, returns datasets for this sample
- `**kwargs`: Query parameters for filtering (keyword, owner_orcid, etc.)

**Returns:**
- `List[Dict]`: Dataset objects matching filter criteria

**Example:**
```python
# Get all datasets
all_datasets = client.list_datasets()

# Filter by keyword
raman_datasets = client.list_datasets(keyword="raman")

# Filter by sample
sample_datasets = client.list_datasets(sample_id="sample-001")
```

### get_dataset

```python
get_dataset(dsid: str, include_metadata: bool = False) -> Dict
```

Get dataset details, optionally including scientific metadata.

**Parameters:**
- `dsid` (str): Dataset unique identifier
- `include_metadata` (bool): Whether to include scientific metadata

**Returns:**
- `Dict`: Dataset object with optional metadata

### create_dataset

```python
create_dataset(
    dataset_name: Optional[str] = None,
    unique_id: Optional[str] = None,
    public: bool = False,
    owner_orcid: Optional[str] = None,
    owner_user_id: Optional[int] = None,
    project_id: Optional[str] = None,
    instrument_name: Optional[str] = None,
    instrument_id: Optional[int] = None,
    measurement: Optional[str] = None,
    session_name: Optional[str] = None,
    creation_time: Optional[str] = None,
    data_format: Optional[str] = None,
    scientific_metadata: Optional[dict] = None,
    keywords: List[str] = None
) -> Dict
```

Create a new dataset with metadata.

**Parameters:**
- `dataset_name` (str, optional): Name of the dataset
- `unique_id` (str, optional): Unique identifier
- `public` (bool): Whether dataset is public
- `owner_orcid` (str, optional): Owner's ORCID
- `owner_user_id` (int, optional): Owner's user ID
- `project_id` (str, optional): Associated project ID
- `instrument_name` (str, optional): Instrument name
- `instrument_id` (int, optional): Instrument ID
- `measurement` (str, optional): Type of measurement
- `session_name` (str, optional): Session name
- `creation_time` (str, optional): Creation timestamp
- `data_format` (str, optional): Data format
- `scientific_metadata` (dict, optional): Scientific metadata
- `keywords` (List[str], optional): Keywords to associate

**Returns:**
- `Dict`: Created dataset object

**Example:**
```python
dataset = client.create_dataset(
    dataset_name="Temperature Study",
    measurement="Raman Spectroscopy",
    scientific_metadata={
        "temperature": 298.15,
        "laser_wavelength": 532,
        "integration_time": 10
    },
    keywords=["raman", "temperature", "materials"]
)
```

### delete_dataset

```python
delete_dataset(dsid: str) -> Dict
```

Delete a dataset (not implemented in API).

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `Dict`: Deletion response

---

## File Management

### upload_dataset

```python
upload_dataset(dsid: str, file_path: str) -> Dict
```

Upload a file to a dataset.

**Parameters:**
- `dsid` (str): Dataset unique identifier
- `file_path` (str): Local path to file to upload

**Returns:**
- `Dict`: Upload response with ingestion request info

### download_dataset

```python
download_dataset(dsid: str, file_name: Optional[str] = None, output_path: Optional[str] = None) -> None
```

Download a dataset file.

**Parameters:**
- `dsid` (str): Dataset ID
- `file_name` (str, optional): File to download (uses dataset's file_to_upload if not provided)
- `output_path` (str, optional): Local save path (saves to crucible-downloads/ if not provided)

### get_associated_files

```python
get_associated_files(dsid: str) -> List[Dict]
```

Get associated files for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `List[Dict]`: File metadata with names, sizes, and hashes

### add_associated_file

```python
add_associated_file(dsid: str, file_path: str, filename: str = None) -> Dict
```

Add an associated file to a dataset.

**Parameters:**
- `dsid` (str): Dataset ID
- `file_path` (str): Path to file (for calculating metadata)
- `filename` (str, optional): Filename to store (uses basename if not provided)

**Returns:**
- `Dict`: Created associated file object

### get_thumbnails

```python
get_thumbnails(dsid: str) -> List[Dict]
```

Get thumbnails for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `List[Dict]`: Thumbnail objects with base64-encoded images

### add_thumbnail

```python
add_thumbnail(dsid: str, file_path: str, thumbnail_name: str = None) -> Dict
```

Add a thumbnail to a dataset.

**Parameters:**
- `dsid` (str): Dataset ID
- `file_path` (str): Path to image file
- `thumbnail_name` (str, optional): Display name (uses filename if not provided)

**Returns:**
- `Dict`: Created thumbnail object

---

## Metadata Management

### get_scientific_metadata

```python
get_scientific_metadata(dsid: str) -> Dict
```

Get scientific metadata for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `Dict`: Scientific metadata containing experimental parameters and settings

### update_scientific_metadata

```python
update_scientific_metadata(dsid: str, metadata: Dict) -> Dict
```

Create or replace scientific metadata for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID
- `metadata` (Dict): Scientific metadata dictionary

**Returns:**
- `Dict`: Updated metadata object

### get_dataset_keywords

```python
get_dataset_keywords(dsid: str) -> List[Dict]
```

Get keywords associated with a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `List[Dict]`: Keyword objects with keyword text and usage counts

### add_dataset_keyword

```python
add_dataset_keyword(dsid: str, keyword: str) -> Dict
```

Add a keyword to a dataset.

**Parameters:**
- `dsid` (str): Dataset ID
- `keyword` (str): Keyword/tag to associate with dataset

**Returns:**
- `Dict`: Keyword object with updated usage count

### get_dataset_access_groups

```python
get_dataset_access_groups(dsid: str) -> List[str]
```

Get access groups for a dataset (admin access required).

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `List[str]`: List of access group names with dataset permissions

---

## Sample Management

### list_samples

```python
list_samples(dataset_id: str = None, parent_id: str = None, **kwargs) -> List[Dict]
```

List samples with optional filtering.

**Parameters:**
- `dataset_id` (str, optional): Get samples from specific dataset
- `parent_id` (str, optional): Get child samples from parent
- `**kwargs`: Query parameters for filtering samples

**Returns:**
- `List[Dict]`: Sample information

### get_sample

```python
get_sample(sample_id: str) -> Dict
```

Get sample information by ID.

**Parameters:**
- `sample_id` (str): Sample unique identifier

**Returns:**
- `Dict`: Sample information with associated datasets

### add_sample

```python
add_sample(
    unique_id: str = None,
    sample_name: str = None,
    description: str = None,
    creation_date: str = None,
    owner_orcid: str = None,
    owner_id: int = None,
    parents: List[Dict] = [],
    children: List[Dict] = []
) -> Dict
```

Add a new sample with optional parent-child relationships.

**Parameters:**
- `unique_id` (str, optional): Unique sample identifier
- `sample_name` (str, optional): Human-readable sample name
- `description` (str, optional): Sample description
- `creation_date` (str, optional): Sample creation date
- `owner_orcid` (str, optional): Owner's ORCID
- `owner_id` (int, optional): Owner's user ID
- `parents` (List[Dict], optional): Parent samples
- `children` (List[Dict], optional): Child samples

**Returns:**
- `Dict`: Created sample object

### add_sample_to_dataset

```python
add_sample_to_dataset(dataset_id: str, sample_id: str) -> Dict
```

Link a sample to a dataset.

**Parameters:**
- `dataset_id` (str): Dataset ID
- `sample_id` (str): Sample ID

**Returns:**
- `Dict`: Information about the created link

### add_sample_metadata

```python
add_sample_metadata(sample_id: str, sample_type: str, **kwargs) -> Dict
```

Upload metadata to table and link to provided sample.

**Parameters:**
- `sample_id` (str): Sample's unique identifier
- `sample_type` (str): Type of sample metadata (e.g., 'spinbot_batch')
- `**kwargs`: Metadata fields

**Returns:**
- `Dict`: Created metadata object

### get_sample_metadata

```python
get_sample_metadata(sample_id: str, sample_type: str) -> Dict
```

Get metadata for a sample by type.

**Parameters:**
- `sample_id` (str): Sample's unique identifier
- `sample_type` (str): Type of sample metadata

**Returns:**
- `Dict`: Sample metadata object

---

## Instrument Management

### list_instruments

```python
list_instruments() -> List[Dict]
```

List all available instruments.

**Returns:**
- `List[Dict]`: Instrument objects with specifications and metadata

### get_instrument

```python
get_instrument(instrument_name: str = None, instrument_id: str = None) -> Dict
```

Get instrument information by name or ID.

**Parameters:**
- `instrument_name` (str, optional): Name of the instrument
- `instrument_id` (str, optional): Unique ID of the instrument

**Returns:**
- `Dict` or None: Instrument information if found, None otherwise

**Raises:**
- `ValueError`: If neither parameter is provided

### get_or_add_instrument

```python
get_or_add_instrument(
    instrument_name: str,
    creation_location: str = None,
    instrument_owner: str = None
) -> Dict
```

Get an existing instrument or create a new one if it doesn't exist.

**Parameters:**
- `instrument_name` (str): Name of the instrument
- `creation_location` (str, optional): Location where instrument was created
- `instrument_owner` (str, optional): Owner of the instrument

**Returns:**
- `Dict`: Instrument information (existing or newly created)

---

## Processing Workflows

### request_ingestion

```python
request_ingestion(dsid: str, file_to_upload: str = None, ingestor: str = None) -> Dict
```

Request dataset ingestion.

**Parameters:**
- `dsid` (str): Dataset ID
- `file_to_upload` (str, optional): Path to file for ingestion
- `ingestor` (str, optional): Ingestion class to use

**Returns:**
- `Dict`: Ingestion request with id and status

### ingest_dataset

```python
ingest_dataset(dsid: str, file_to_upload: str = None, ingestion_class: str = None) -> Dict
```

Request ingestion of a dataset file.

**Parameters:**
- `dsid` (str): Dataset ID
- `file_to_upload` (str, optional): Path to the file to ingest
- `ingestion_class` (str, optional): Class to use for ingestion

**Returns:**
- `Dict`: Ingestion request information

### get_ingestion_status

```python
get_ingestion_status(dsid: str, reqid: str) -> Dict
```

Get the status of an ingestion request.

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID for the ingestion

**Returns:**
- `Dict`: Status, timestamps, and processing details

### send_to_scicat

```python
send_to_scicat(
    dsid: str,
    wait_for_scicat_response: bool = False,
    overwrite_data: bool = False
) -> Dict
```

Request SciCat update for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID
- `wait_for_scicat_response` (bool): Whether to wait for completion
- `overwrite_data` (bool): Whether to overwrite existing SciCat records

**Returns:**
- `Dict`: SciCat update request information

### get_scicat_status

```python
get_scicat_status(dsid: str, reqid: str) -> Dict
```

Get the status of a SciCat request.

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID for the SciCat operation

**Returns:**
- `Dict`: SciCat sync status and timestamps

### request_google_drive_transfer

```python
request_google_drive_transfer(dsid: str) -> Dict
```

Request transfer of dataset to Google Drive.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `Dict`: Transfer request with id and status

### get_request_status

```python
get_request_status(dsid: str, reqid: str, request_type: str) -> Dict
```

Get the status of any type of request.

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID
- `request_type` (str): Type of request ('ingest' or 'scicat_update')

**Returns:**
- `Dict`: Request status information

### wait_for_request_completion

```python
wait_for_request_completion(
    dsid: str,
    reqid: str,
    request_type: str,
    sleep_interval: int = 5
) -> Dict
```

Wait for a request to complete by polling its status.

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID
- `request_type` (str): Type of request ('ingest' or 'scicat_update')
- `sleep_interval` (int): Seconds between status checks

**Returns:**
- `Dict`: Final request status information

### get_current_google_drive_info

```python
get_current_google_drive_info(dsid: str) -> Dict
```

Get current Google Drive location information for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `Dict`: Google Drive location information

### get_organized_google_drive_info

```python
get_organized_google_drive_info(dsid: str) -> List[Dict]
```

Get organized Google Drive folder information for a dataset.

**Parameters:**
- `dsid` (str): Dataset ID

**Returns:**
- `List[Dict]`: Organized Google Drive folder information

---

## Admin Functions

### update_ingestion_status

```python
update_ingestion_status(
    dsid: str,
    reqid: str,
    status: str,
    timezone: str = "America/Los_Angeles"
)
```

Update the status of a dataset ingestion request (admin use).

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID for the ingestion
- `status` (str): New status ('complete', 'in_progress', 'failed')
- `timezone` (str): Timezone for completion time

**Returns:**
- requests.Response: HTTP response from the update request

### update_scicat_upload_status

```python
update_scicat_upload_status(
    dsid: str,
    reqid: str,
    status: str,
    timezone: str = "America/Los_Angeles"
)
```

Update the status of a SciCat upload request (admin use).

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID for the SciCat upload
- `status` (str): New status ('complete', 'in_progress', 'failed')
- `timezone` (str): Timezone for completion time

**Returns:**
- requests.Response: HTTP response from the update request

### update_transfer_status

```python
update_transfer_status(
    dsid: str,
    reqid: str,
    status: str,
    timezone: str = "America/Los_Angeles"
)
```

Update the status of a dataset transfer request (admin use).

**Parameters:**
- `dsid` (str): Dataset ID
- `reqid` (str): Request ID for the transfer
- `status` (str): New status ('complete', 'in_progress', 'failed')
- `timezone` (str): Timezone for completion time

**Returns:**
- requests.Response: HTTP response from the update request

---

## Utilities

### create_file_payload

```python
@staticmethod
create_file_payload(file_to_upload: str) -> tuple
```

Create a file payload for upload.

**Parameters:**
- `file_to_upload` (str): Path to the file to upload

**Returns:**
- `tuple`: File payload tuple for requests

---

## Error Handling

All functions may raise the following exceptions:

- `requests.exceptions.HTTPError`: For HTTP errors (404, 403, 500, etc.)
- `requests.exceptions.ConnectionError`: For connection issues
- `requests.exceptions.Timeout`: For timeout issues
- `ValueError`: For invalid parameter values
- `FileNotFoundError`: For missing local files

**Example error handling:**
```python
import requests

try:
    dataset = client.get_dataset("dataset-id")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Dataset not found")
    elif e.response.status_code == 403:
        print("Access denied")
    else:
        print(f"HTTP error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Return Types

Most functions return dictionaries with the following common fields:

### Dataset Object
```python
{
    "unique_id": str,
    "dataset_name": str,
    "measurement": str,
    "public": bool,
    "owner_orcid": str,
    "project_id": str,
    "creation_time": str,
    "scientific_metadata": dict,  # if include_metadata=True
    # ... additional fields
}
```

### Sample Object
```python
{
    "unique_id": str,
    "sample_name": str,
    "description": str,
    "owner_orcid": str,
    "date_created": str,
    "datasets": List[Dict],  # associated datasets
    # ... additional fields
}
```

### Request Object
```python
{
    "id": int,
    "status": str,  # 'requested', 'started', 'completed', 'failed'
    "time_requested": str,
    "time_completed": str,  # if completed
    "error_message": str,   # if failed
    # ... additional fields
}
```