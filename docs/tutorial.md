# Tutorial: Complete Workflow

This tutorial walks through a complete workflow using PycrucibleClient, from setting up a research project to publishing data to external catalogs.

## Overview

We'll demonstrate a typical research workflow:

1. **Project Setup** - Create a project and add collaborators
2. **Sample Management** - Register samples with metadata
3. **Data Collection** - Create datasets and upload experimental data
4. **Metadata Management** - Add scientific parameters and keywords
5. **Data Processing** - Request automated data processing
6. **Publication** - Sync data to external catalogs

## Prerequisites

- PycrucibleClient installed and configured ([Getting Started](getting-started.md))
- Valid API key and access to a Crucible instance
- Sample data files to work with

## Step 1: Project Setup

First, let's create a research project and set up the team.

```python
from pycrucible import CrucibleClient

# Initialize client
client = CrucibleClient(
    api_url="https://your-crucible-instance.com",
    api_key="your-api-key"
)

# Create a new research project
project_info = {
    "project_id": "materials-study-2024",
    "project_name": "Advanced Materials Characterization Study",
    "organization": "Molecular Foundry",
    "project_lead_email": "researcher@lbl.gov",
    "description": "Comprehensive study of novel 2D materials",
    "status": "active"
}

project = client.add_project(project_info)
print(f"Created project: {project['project_id']}")

# List existing users (admin access required)
# users = client.list_users()
```

## Step 2: Instrument Registration

Register the instruments we'll use for data collection.

```python
# Get or create instrument
instrument = client.get_or_add_instrument(
    instrument_name="Raman Spectrometer Alpha300R",
    creation_location="Building 2, Room 101",
    instrument_owner="Materials Science Group"
)

print(f"Instrument registered: {instrument['instrument_name']}")
```

## Step 3: Sample Management

Create and organize our sample hierarchy.

```python
# Create a parent sample (bulk material)
bulk_sample = client.add_sample(
    unique_id="bulk-material-001",
    sample_name="Bulk MoS2 Crystal",
    description="High-quality bulk molybdenum disulfide crystal",
    owner_orcid="0000-0000-0000-0000"
)

print(f"Created bulk sample: {bulk_sample['unique_id']}")

# Create prepared samples from the bulk material
prepared_samples = []
for i in range(3):
    sample = client.add_sample(
        unique_id=f"prepared-sample-{i+1:03d}",
        sample_name=f"MoS2 Exfoliated Sample {i+1}",
        description=f"Mechanically exfoliated sample #{i+1} for Raman analysis",
        owner_orcid="0000-0000-0000-0000",
        parents=[bulk_sample]
    )
    prepared_samples.append(sample)
    print(f"Created prepared sample: {sample['unique_id']}")

# Add sample-specific metadata
sample_metadata = {
    "thickness_nm": 5.2,
    "preparation_method": "mechanical_exfoliation",
    "substrate": "SiO2/Si",
    "preparation_date": "2024-01-15",
    "storage_conditions": "dry nitrogen atmosphere"
}

client.add_sample_metadata(
    prepared_samples[0]['unique_id'],
    "material_sample",
    **sample_metadata
)
```

## Step 4: Dataset Creation and File Upload

Create datasets for our experimental data and upload files.

```python
import os
from datetime import datetime

# Create a dataset for Raman spectroscopy
dataset = client.create_dataset(
    dataset_name="MoS2 Raman Spectroscopy Temperature Series",
    unique_id=f"raman-temp-series-{datetime.now().strftime('%Y%m%d')}",
    measurement="Raman Spectroscopy",
    public=False,
    project_id=project['project_id'],
    instrument_name=instrument['instrument_name'],
    session_name="Temperature Dependence Study",
    data_format="ASCII",
    scientific_metadata={
        "laser_wavelength_nm": 532,
        "laser_power_mw": 0.5,
        "integration_time_s": 10,
        "spectral_range_cm1": [100, 1000],
        "temperature_range_k": [77, 400],
        "temperature_steps": 8,
        "objective": "100x",
        "grating": "1800 grooves/mm"
    },
    keywords=["raman", "spectroscopy", "2d-materials", "mos2", "temperature"]
)

print(f"Created dataset: {dataset['unique_id']}")

# Link our prepared sample to the dataset
client.add_sample_to_dataset(
    dataset['unique_id'],
    prepared_samples[0]['unique_id']
)

# Simulate uploading data files
# In practice, you would have real data files
example_files = [
    "raman_77K.txt",
    "raman_150K.txt",
    "raman_200K.txt",
    "raman_250K.txt",
    "raman_300K.txt",
    "raman_350K.txt",
    "raman_400K.txt"
]

# Upload main data file
print("Uploading data files...")
# client.upload_dataset(dataset['unique_id'], "raman_temperature_series.zip")

# Add associated files metadata (for files uploaded separately)
for filename in example_files:
    if os.path.exists(filename):  # Only if file exists
        client.add_associated_file(
            dataset['unique_id'],
            filename,
            filename=f"temperature_series/{filename}"
        )
```

## Step 5: Adding Thumbnails and Visualization

Add visual previews to help with data discovery.

```python
# Add thumbnail (if you have a plot image)
# client.add_thumbnail(
#     dataset['unique_id'],
#     "raman_overview_plot.png",
#     thumbnail_name="Temperature Series Overview"
# )

# Update metadata with analysis results
analysis_metadata = {
    "peak_positions_cm1": {
        "E2g": 383.2,
        "A1g": 408.5
    },
    "temperature_coefficients": {
        "E2g_cm1_per_K": -0.0132,
        "A1g_cm1_per_K": -0.0089
    },
    "analysis_software": "custom_python_analysis",
    "analysis_date": datetime.now().isoformat(),
    "notes": "Clear temperature dependence observed in both modes"
}

# Update the scientific metadata
current_metadata = client.get_scientific_metadata(dataset['unique_id'])
current_metadata.update(analysis_metadata)

client.update_scientific_metadata(dataset['unique_id'], current_metadata)
```

## Step 6: Data Processing Pipeline

Request automated data processing and monitor progress.

```python
# Request data ingestion/processing
ingest_request = client.request_ingestion(
    dataset['unique_id'],
    file_to_upload="api-uploads/raman_temperature_series.zip",
    ingestor="raman_spectroscopy_processor"
)

print(f"Ingestion requested: {ingest_request['id']}")

# Monitor processing progress
print("Waiting for data processing...")
final_status = client.wait_for_request_completion(
    dataset['unique_id'],
    ingest_request['id'],
    'ingest',
    sleep_interval=10
)

print(f"Processing completed with status: {final_status['status']}")

# If processing succeeded, the data is now available for analysis
if final_status['status'] == 'completed':
    print("✅ Data processing completed successfully")

    # Get updated dataset information
    updated_dataset = client.get_dataset(dataset['unique_id'], include_metadata=True)
    print(f"Dataset now contains {len(updated_dataset.get('associated_files', []))} associated files")
else:
    print(f"❌ Processing failed: {final_status.get('error_message', 'Unknown error')}")
```

## Step 7: External Catalog Synchronization

Sync the dataset to external data catalogs for broader discovery.

```python
# Send to SciCat data catalog
print("Syncing to SciCat catalog...")
scicat_request = client.send_to_scicat(
    dataset['unique_id'],
    wait_for_scicat_response=True,
    overwrite_data=False
)

print(f"SciCat sync status: {scicat_request['status']}")

# Request Google Drive transfer for collaboration
print("Requesting Google Drive transfer...")
drive_request = client.request_google_drive_transfer(dataset['unique_id'])
print(f"Drive transfer requested: {drive_request['id']}")

# Monitor the transfer
drive_status = client.wait_for_request_completion(
    dataset['unique_id'],
    drive_request['id'],
    'google_drive_transfer'
)

print(f"Drive transfer completed: {drive_status['status']}")
```

## Step 8: Data Discovery and Access

Demonstrate how others can discover and access your data.

```python
# Search for datasets by keyword
discovered_datasets = client.list_datasets(keyword="raman")
print(f"Found {len(discovered_datasets)} Raman datasets")

# Search by metadata
temperature_studies = client.list_datasets(
    measurement="Raman Spectroscopy",
    laser_wavelength_nm=532
)
print(f"Found {len(temperature_studies)} datasets with 532nm laser")

# Get dataset access information (admin only)
# access_groups = client.get_dataset_access_groups(dataset['unique_id'])
# print(f"Dataset accessible to: {access_groups}")

# Download data for analysis
print("Downloading dataset for local analysis...")
# client.download_dataset(
#     dataset['unique_id'],
#     output_path="./analysis/downloaded_data.zip"
# )
```

## Step 9: Advanced Sample Relationships

Demonstrate complex sample hierarchies for multi-step processing.

```python
# Create processed samples from our experiments
processed_sample = client.add_sample(
    unique_id="processed-sample-001",
    sample_name="Post-Heating MoS2 Sample",
    description="Sample after 400K heating cycle",
    owner_orcid="0000-0000-0000-0000",
    parents=[prepared_samples[0]]
)

# Add processing metadata
processing_metadata = {
    "max_temperature_k": 400,
    "heating_rate_k_per_min": 5,
    "atmosphere": "vacuum",
    "post_treatment_analysis": "AFM, Raman",
    "structural_changes": "Minor edge reconstruction observed"
}

client.add_sample_metadata(
    processed_sample['unique_id'],
    "processed_sample",
    **processing_metadata
)

# Create follow-up dataset
followup_dataset = client.create_dataset(
    dataset_name="Post-Heating Analysis",
    measurement="AFM + Raman",
    project_id=project['project_id'],
    scientific_metadata={
        "analysis_type": "post_processing_characterization",
        "techniques": ["AFM", "Raman"],
        "reference_dataset": dataset['unique_id']
    },
    keywords=["followup", "thermal-treatment", "characterization"]
)

# Link processed sample to new dataset
client.add_sample_to_dataset(
    followup_dataset['unique_id'],
    processed_sample['unique_id']
)

print(f"Created followup dataset: {followup_dataset['unique_id']}")
```

## Step 10: Quality Control and Validation

Verify data integrity and completeness.

```python
# Verify dataset completeness
def verify_dataset(dataset_id):
    """Check dataset has required components"""
    dataset = client.get_dataset(dataset_id, include_metadata=True)

    checks = {
        "has_scientific_metadata": bool(dataset.get('scientific_metadata')),
        "has_keywords": len(client.get_dataset_keywords(dataset_id)) > 0,
        "has_associated_files": len(client.get_associated_files(dataset_id)) > 0,
        "has_samples": len(client.list_samples(dataset_id=dataset_id)) > 0
    }

    print(f"Dataset {dataset_id} validation:")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")

    return all(checks.values())

# Verify our main dataset
is_complete = verify_dataset(dataset['unique_id'])
print(f"\nDataset validation: {'PASSED' if is_complete else 'FAILED'}")

# List all datasets in our project
project_datasets = client.list_datasets(project_id=project['project_id'])
print(f"\nProject contains {len(project_datasets)} datasets")
```

## Summary

Congratulations! You've completed a full research data workflow:

1. ✅ **Project created** with team collaboration setup
2. ✅ **Instruments registered** for data provenance
3. ✅ **Sample hierarchy established** with preparation tracking
4. ✅ **Datasets created** with comprehensive metadata
5. ✅ **Files uploaded** and organized
6. ✅ **Data processed** through automated pipelines
7. ✅ **External catalogs synced** for broader discovery
8. ✅ **Access controls** managed for team collaboration
9. ✅ **Quality validation** performed

## Best Practices Demonstrated

- **Rich Metadata**: Always include comprehensive scientific metadata
- **Sample Tracking**: Maintain clear sample provenance and relationships
- **Keywords**: Use consistent, discoverable keywords
- **File Organization**: Organize associated files logically
- **Processing Pipelines**: Leverage automated processing for consistency
- **External Integration**: Sync to catalogs for broader impact
- **Quality Control**: Validate datasets before publication

## Next Steps

- **Explore [Examples](examples.md)** for specific use cases
- **Review [API Reference](api-reference.md)** for complete function documentation
- **Adapt this workflow** to your specific research domain
- **Integrate with your existing tools** and analysis pipelines

## Advanced Topics

For more advanced usage patterns:

- **Batch Operations**: Process multiple datasets efficiently
- **Custom Metadata Schemas**: Define domain-specific metadata structures
- **Workflow Automation**: Build automated data processing pipelines
- **Access Management**: Implement fine-grained permission controls
- **Integration**: Connect with LIMS, ELN, and other research tools