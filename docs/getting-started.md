# Getting Started

This guide will help you install and set up PycrucibleClient to start working with the Crucible API.

## Installation

### Requirements

- Python 3.8 or higher
- pip package manager

### Install from PyPI

```bash
pip install pycrucible
```

### Install from Source

```bash
git clone https://github.com/your-username/pycrucible.git
cd pycrucible
pip install -e .
```

### Development Installation

For development work:

```bash
git clone https://github.com/your-username/pycrucible.git
cd pycrucible
pip install -e ".[dev]"
```

This installs additional development dependencies like pytest, black, and mypy.

## Authentication

To use PycrucibleClient, you need an API key from your Crucible instance.

### Getting Your API Key

1. Navigate to your Crucible instance in a web browser
2. Log in with your ORCID credentials
3. Visit `/user_apikey` to generate your personal API key
4. Copy the generated API key

### Setting Up Authentication

#### Method 1: Direct Initialization

```python
from pycrucible import CrucibleClient

client = CrucibleClient(
    api_url="https://your-crucible-instance.com",
    api_key="your-api-key-here"
)
```

#### Method 2: Environment Variables

Set environment variables:

```bash
export CRUCIBLE_API_URL="https://your-crucible-instance.com"
export CRUCIBLE_API_KEY="your-api-key-here"
```

Then initialize without parameters:

```python
import os
from pycrucible import CrucibleClient

client = CrucibleClient(
    api_url=os.getenv("CRUCIBLE_API_URL"),
    api_key=os.getenv("CRUCIBLE_API_KEY")
)
```

#### Method 3: Interactive Setup (Jupyter Notebooks)

For secure input in Jupyter notebooks:

```python
from pycrucible import CrucibleClient, SecureInput

# This creates an interactive widget for secure API key entry
api_key_input = SecureInput("Enter your Crucible API key:")
# Enter your key in the widget that appears

client = CrucibleClient(
    api_url="https://your-crucible-instance.com",
    api_key=api_key_input.secret
)
```

## Verifying Your Setup

Test your connection and authentication:

```python
# Test basic connectivity
try:
    account_info = client._request('get', '/account')
    print(f"Connected as: {account_info['access_group_name']}")
    print("✅ Authentication successful!")
except Exception as e:
    print(f"❌ Authentication failed: {e}")

# List your accessible datasets
datasets = client.list_datasets()
print(f"You have access to {len(datasets)} datasets")
```

## Basic Usage

Here are some basic operations to get you started:

### List Datasets

```python
# Get all datasets you have access to
datasets = client.list_datasets()

# Filter by keyword
science_datasets = client.list_datasets(keyword="spectroscopy")

# Filter by metadata
room_temp_datasets = client.list_datasets(temperature=298.15)
```

### Get Dataset Details

```python
# Get basic dataset information
dataset = client.get_dataset("your-dataset-id")

# Get dataset with scientific metadata included
dataset_with_metadata = client.get_dataset(
    "your-dataset-id",
    include_metadata=True
)
```

### Work with Scientific Metadata

```python
# Get existing metadata
metadata = client.get_scientific_metadata("dataset-id")

# Add or update metadata
new_metadata = {
    "temperature": 77,  # Kelvin
    "pressure": 1e-6,   # Torr
    "instrument_settings": {
        "voltage": 200,
        "magnification": "50k"
    }
}
client.update_scientific_metadata("dataset-id", new_metadata)
```

### Upload and Download Files

```python
# Upload a file to a dataset
client.upload_dataset("dataset-id", "path/to/your/file.dat")

# Download a dataset file
client.download_dataset(
    "dataset-id",
    file_name="data.hdf5",
    output_path="./downloads/data.hdf5"
)
```

## Common Patterns

### Create a Complete Dataset

```python
# Create dataset with full metadata
dataset = client.create_dataset(
    dataset_name="My Experiment",
    measurement="X-ray Diffraction",
    public=False,
    owner_orcid="0000-0000-0000-0000",
    project_id="my-project-2024",
    instrument_name="Bruker D8",
    scientific_metadata={
        "sample_temperature": 298.15,
        "scan_range": "10-80 degrees",
        "step_size": 0.02,
        "count_time": 1.0
    },
    keywords=["crystallography", "materials", "xrd"]
)

print(f"Created dataset: {dataset['unique_id']}")
```

### Process Data Pipeline

```python
# Upload data file
client.upload_dataset(dataset['unique_id'], "xrd_pattern.xy")

# Request data processing
ingest_req = client.request_ingestion(
    dataset['unique_id'],
    ingestor="xrd_processor"
)

# Wait for processing to complete
result = client.wait_for_request_completion(
    dataset['unique_id'],
    ingest_req['id'],
    'ingest'
)

# Sync to SciCat catalog
if result['status'] == 'completed':
    scicat_req = client.send_to_scicat(dataset['unique_id'])
    print(f"SciCat sync requested: {scicat_req['id']}")
```

## Error Handling

```python
import requests

try:
    dataset = client.get_dataset("nonexistent-id")
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

## Configuration Tips

### Performance

```python
# For batch operations, reuse the client instance
client = CrucibleClient(api_url=url, api_key=key)

# Process multiple datasets
for dataset_id in dataset_ids:
    metadata = client.get_scientific_metadata(dataset_id)
    # Process metadata...
```

### Timeouts

```python
# The client uses requests internally
# You can modify timeout behavior by accessing the session
client._request('get', '/datasets', timeout=30)
```

## Next Steps

Now that you have PycrucibleClient set up:

1. **Follow the [Tutorial](tutorial.md)** for a comprehensive walkthrough
2. **Explore [Examples](examples.md)** for common use cases
3. **Check the [API Reference](api-reference.md)** for complete function documentation

## Troubleshooting

### Common Issues

**"Invalid API key"**
- Verify your API key is correct
- Check that your API key hasn't expired
- Ensure you're using the correct Crucible instance URL

**"Dataset not found"**
- Verify the dataset ID is correct
- Check that you have permission to access the dataset
- Ensure the dataset exists and hasn't been deleted

**"Connection refused"**
- Verify the API URL is correct and accessible
- Check your network connection
- Ensure the Crucible instance is running

### Getting Help

- Check the [Examples](examples.md) page for similar use cases
- Review the [API Reference](api-reference.md) for function details
- Report issues on the GitHub repository