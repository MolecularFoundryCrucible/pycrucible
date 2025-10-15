# PycrucibleClient

A Python client library for the Crucible API - the Molecular Foundry data lakehouse containing experimental synthesis and characterization data, along with information about users, projects, and instruments.

## Features

- **Dataset Management**: Create, update, list, and retrieve datasets with metadata
- **File Operations**: Upload, download, and manage dataset files and thumbnails
- **Scientific Metadata**: Store and retrieve experimental parameters and instrument settings
- **Sample Tracking**: Manage samples with hierarchical relationships and type-specific metadata
- **Instrument Integration**: Register and manage scientific instruments
- **Project Organization**: Create and manage research projects with user collaboration
- **Processing Workflows**: Request data ingestion, SciCat synchronization, and Google Drive transfers
- **Access Control**: Manage permissions and user access to datasets and resources

## Installation

```bash
pip install pycrucible
```

## Quick Start

```python
from pycrucible import CrucibleClient

# Initialize the client
client = CrucibleClient(
    api_url="https://your-crucible-api.com",
    api_key="your-api-key"
)

# List your datasets
datasets = client.list_datasets()

# Get a specific dataset with metadata
dataset = client.get_dataset("dataset-id", include_metadata=True)

# Upload a file
client.upload_dataset("dataset-id", "path/to/file.dat")

# Create a new dataset
new_dataset = client.create_dataset(
    dataset_name="My Experiment",
    measurement="XRD",
    public=False,
    scientific_metadata={
        "temperature": 298.15,
        "voltage": 200,
        "sample_preparation": "standard protocol"
    },
    keywords=["crystallography", "materials"]
)
```

## Authentication

1. **Get an API Key**: Visit your Crucible instance and navigate to `/user_apikey` to generate your personal API key
2. **Set Environment Variable** (optional):
   ```bash
   export CRUCIBLE_API_KEY="your-api-key-here"
   ```

## Core Concepts

### Datasets
Central data containers that hold experimental results, metadata, and associated files. Each dataset can contain:
- Scientific metadata (experimental parameters)
- Associated files (data files, analysis results)
- Thumbnails (visual previews)
- Keywords for discovery
- Sample associations

### Samples
Physical materials that datasets are derived from. Samples support:
- Hierarchical parent-child relationships
- Type-specific metadata schemas
- Multi-dataset associations

### Projects
Organizational units for research collaboration:
- Group related datasets and samples
- Manage team member access
- Track research progress

### Instruments
Scientific equipment used to generate data:
- Store instrument specifications
- Associate with datasets for provenance
- Enable instrument-based access control

## Main Functions

### Dataset Operations
- `list_datasets()` - List accessible datasets with filtering
- `get_dataset(dsid)` - Retrieve specific dataset details
- `create_dataset()` - Create new dataset with metadata
- `upload_dataset()` - Upload files to datasets
- `download_dataset()` - Download dataset files

### Metadata Management
- `get_scientific_metadata(dsid)` - Get experimental parameters
- `update_scientific_metadata(dsid, metadata)` - Set scientific metadata
- `add_dataset_keyword(dsid, keyword)` - Tag datasets for discovery

### Sample Management
- `list_samples()` - List accessible samples
- `add_sample()` - Create new sample records
- `add_sample_to_dataset()` - Link samples to datasets
- `add_sample_metadata()` - Store sample-specific metadata

### Processing Workflows
- `request_ingestion(dsid)` - Process uploaded files
- `send_to_scicat(dsid)` - Sync to SciCat catalog
- `request_google_drive_transfer(dsid)` - Transfer to Google Drive
- `wait_for_request_completion()` - Monitor processing status

## Documentation

For complete documentation, tutorials, and API reference, visit: [PycrucibleClient Documentation](https://your-username.github.io/pycrucible/)

## Examples

### Working with Scientific Metadata
```python
# Add experimental parameters
metadata = {
    "temperature": 77,  # Kelvin
    "pressure": 1e-6,   # Torr
    "voltage": 200,     # kV
    "instrument_settings": {
        "magnification": "100k",
        "spot_size": 3
    }
}
client.update_scientific_metadata("dataset-id", metadata)
```

### Sample Tracking
```python
# Create a parent sample
parent = client.add_sample(
    sample_name="Bulk Material XYZ",
    description="Starting material for experiment"
)

# Create child samples
child = client.add_sample(
    sample_name="Prepared Section 1",
    description="TEM sample preparation",
    parents=[parent]
)

# Link sample to dataset
client.add_sample_to_dataset("dataset-id", child['unique_id'])
```

### Processing Pipeline
```python
# Upload and process data
client.upload_dataset("dataset-id", "data.hdf5")
ingest_req = client.request_ingestion("dataset-id", ingestor="hdf5_processor")

# Wait for processing
result = client.wait_for_request_completion(
    "dataset-id",
    ingest_req['id'],
    "ingest"
)

# Sync to SciCat when complete
if result['status'] == 'completed':
    client.send_to_scicat("dataset-id")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the BSD License - see the LICENSE file for details.