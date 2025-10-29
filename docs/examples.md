# Examples

This page provides practical examples for common PycrucibleClient use cases.

## Table of Contents

- [Basic Operations](#basic-operations)
- [Scientific Workflows](#scientific-workflows)
- [File Management](#file-management)
- [Sample Tracking](#sample-tracking)
- [Data Processing](#data-processing)
- [Collaboration & Access](#collaboration--access)
- [Batch Operations](#batch-operations)
- [Integration Patterns](#integration-patterns)

## Basic Operations

### Initialize Client and Test Connection

```python
from pycrucible import CrucibleClient
import os

# Initialize client
client = CrucibleClient(
    api_url=os.getenv("CRUCIBLE_API_URL"),
    api_key=os.getenv("CRUCIBLE_API_KEY")
)

# Test connection
try:
    datasets = client.list_datasets()
    print(f"✅ Connected! You have access to {len(datasets)} datasets")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### List and Filter Datasets

```python
# Get all your datasets
all_datasets = client.list_datasets()

# Filter by keyword
spectroscopy_data = client.list_datasets(keyword="spectroscopy")

# Filter by measurement type
xrd_datasets = client.list_datasets(measurement="X-ray Diffraction")

# Filter by owner
my_datasets = client.list_datasets(owner_orcid="0000-0000-0000-0000")

# Complex filtering with metadata
room_temp_data = client.list_datasets(
    keyword="raman",
    temperature=298.15
)

print(f"Found {len(room_temp_data)} room temperature Raman datasets")
```

### Search and Discover Data

```python
# Search across multiple criteria
def search_datasets(client, **criteria):
    """Advanced dataset search with multiple criteria"""
    results = []

    # Get base list
    datasets = client.list_datasets()

    for dataset in datasets:
        match = True

        # Check metadata if available
        if any(k in ['temperature', 'pressure', 'voltage'] for k in criteria.keys()):
            try:
                metadata = client.get_scientific_metadata(dataset['unique_id'])
                for key, value in criteria.items():
                    if key in metadata and metadata[key] != value:
                        match = False
                        break
            except:
                match = False

        # Check keywords
        if 'keyword' in criteria:
            try:
                keywords = client.get_dataset_keywords(dataset['unique_id'])
                keyword_list = [kw['keyword'] for kw in keywords]
                if criteria['keyword'] not in keyword_list:
                    match = False
            except:
                match = False

        if match:
            results.append(dataset)

    return results

# Example searches
low_temp_data = search_datasets(client, temperature=77)
semiconductor_data = search_datasets(client, keyword="semiconductor")
```

## Scientific Workflows

### Materials Science: XRD Analysis

```python
def create_xrd_dataset(client, sample_id, file_path, conditions):
    """Create XRD dataset with proper metadata"""

    # Create dataset
    dataset = client.create_dataset(
        dataset_name=f"XRD Analysis - {conditions['sample_name']}",
        measurement="X-ray Diffraction",
        instrument_name="Bruker D8 Advance",
        data_format="ASCII",
        scientific_metadata={
            "scan_range_deg": conditions.get("scan_range", [10, 80]),
            "step_size_deg": conditions.get("step_size", 0.02),
            "count_time_s": conditions.get("count_time", 1.0),
            "voltage_kv": conditions.get("voltage", 40),
            "current_ma": conditions.get("current", 40),
            "wavelength_angstrom": 1.5406,  # Cu K-alpha
            "sample_temperature_k": conditions.get("temperature", 298.15),
            "atmosphere": conditions.get("atmosphere", "air")
        },
        keywords=["xrd", "crystallography", "materials", conditions.get("material_type")]
    )

    # Link sample
    if sample_id:
        client.add_sample_to_dataset(dataset['unique_id'], sample_id)

    # Upload data
    if file_path and os.path.exists(file_path):
        client.upload_dataset(dataset['unique_id'], file_path)

        # Request processing
        ingest_req = client.request_ingestion(
            dataset['unique_id'],
            ingestor="xrd_processor"
        )
        print(f"XRD processing requested: {ingest_req['id']}")

    return dataset

# Example usage
conditions = {
    "sample_name": "LaFeO3 Thin Film",
    "scan_range": [20, 80],
    "step_size": 0.01,
    "material_type": "perovskite"
}

xrd_dataset = create_xrd_dataset(
    client,
    sample_id="sample-001",
    file_path="xrd_data.xy",
    conditions=conditions
)
```

### Biology: Microscopy Data

```python
def create_microscopy_dataset(client, sample_id, image_files, microscopy_params):
    """Create microscopy dataset with image files"""

    dataset = client.create_dataset(
        dataset_name=f"Microscopy - {microscopy_params['technique']}",
        measurement=microscopy_params['technique'],
        instrument_name=microscopy_params.get('instrument', 'Unknown'),
        scientific_metadata={
            "magnification": microscopy_params.get("magnification"),
            "voltage_kv": microscopy_params.get("voltage"),
            "spot_size": microscopy_params.get("spot_size"),
            "working_distance_mm": microscopy_params.get("working_distance"),
            "detector": microscopy_params.get("detector"),
            "imaging_mode": microscopy_params.get("mode", "BF"),
            "pixel_size_nm": microscopy_params.get("pixel_size"),
            "acquisition_time_s": microscopy_params.get("acq_time")
        },
        keywords=["microscopy", microscopy_params['technique'].lower(), "imaging"]
    )

    # Link sample
    if sample_id:
        client.add_sample_to_dataset(dataset['unique_id'], sample_id)

    # Upload images and create thumbnails
    for i, image_file in enumerate(image_files):
        if os.path.exists(image_file):
            if i == 0:
                # First image as main file
                client.upload_dataset(dataset['unique_id'], image_file)
                # Create thumbnail
                client.add_thumbnail(
                    dataset['unique_id'],
                    image_file,
                    thumbnail_name="Representative Image"
                )
            else:
                # Additional images as associated files
                client.add_associated_file(dataset['unique_id'], image_file)

    return dataset

# Example usage
microscopy_params = {
    "technique": "TEM",
    "instrument": "JEOL 2100F",
    "magnification": "200k",
    "voltage": 200,
    "spot_size": 3,
    "mode": "HRTEM"
}

tem_dataset = create_microscopy_dataset(
    client,
    sample_id="bio-sample-001",
    image_files=["tem_001.tif", "tem_002.tif", "tem_003.tif"],
    microscopy_params=microscopy_params
)
```

## File Management

### Organize Large Datasets

```python
def organize_large_dataset(client, dataset_id, data_directory):
    """Organize and upload files from a directory structure"""

    import os
    from pathlib import Path

    data_path = Path(data_directory)

    # Find main data file (largest file)
    all_files = list(data_path.rglob("*"))
    data_files = [f for f in all_files if f.is_file()]

    if not data_files:
        print("No files found in directory")
        return

    # Sort by size to find main file
    data_files.sort(key=lambda x: x.stat().st_size, reverse=True)
    main_file = data_files[0]

    print(f"Uploading main file: {main_file.name}")
    client.upload_dataset(dataset_id, str(main_file))

    # Add other files as associated files
    for file_path in data_files[1:]:
        if file_path.stat().st_size > 100 * 1024 * 1024:  # > 100MB
            print(f"Large file detected: {file_path.name} - adding as associated file")

        client.add_associated_file(
            dataset_id,
            str(file_path),
            filename=str(file_path.relative_to(data_path))
        )

    # Create thumbnails for image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}
    for file_path in data_files[:5]:  # First 5 images
        if file_path.suffix.lower() in image_extensions:
            try:
                client.add_thumbnail(
                    dataset_id,
                    str(file_path),
                    thumbnail_name=f"Preview: {file_path.name}"
                )
                print(f"Added thumbnail: {file_path.name}")
            except Exception as e:
                print(f"Failed to add thumbnail for {file_path.name}: {e}")

# Example usage
organize_large_dataset(client, "dataset-001", "/path/to/experiment/data/")
```

### Download and Organize Local Files

```python
def download_project_data(client, project_id, output_dir):
    """Download all datasets from a project"""

    import os
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get project datasets
    datasets = client.list_datasets(project_id=project_id)

    for dataset in datasets:
        dataset_id = dataset['unique_id']
        dataset_name = dataset.get('dataset_name', dataset_id)

        # Create dataset directory
        dataset_dir = output_path / dataset_name.replace('/', '_')
        dataset_dir.mkdir(exist_ok=True)

        print(f"Downloading dataset: {dataset_name}")

        # Download main file
        try:
            client.download_dataset(
                dataset_id,
                output_path=str(dataset_dir / "main_data")
            )
        except Exception as e:
            print(f"Could not download main file: {e}")

        # Download metadata
        try:
            metadata = client.get_scientific_metadata(dataset_id)
            with open(dataset_dir / "metadata.json", 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Could not download metadata: {e}")

        # Get associated files info
        try:
            assoc_files = client.get_associated_files(dataset_id)
            with open(dataset_dir / "file_list.txt", 'w') as f:
                for file_info in assoc_files:
                    f.write(f"{file_info['filename']} ({file_info['size']} bytes)\n")
        except Exception as e:
            print(f"Could not get file list: {e}")

# Example usage
download_project_data(client, "my-project-2024", "./downloaded_data/")
```

## Sample Tracking

### Complex Sample Hierarchies

```python
def create_sample_preparation_chain(client, bulk_sample_info, preparation_steps):
    """Create a chain of sample preparations"""

    # Create bulk sample
    bulk_sample = client.add_sample(
        unique_id=bulk_sample_info['id'],
        sample_name=bulk_sample_info['name'],
        description=bulk_sample_info['description'],
        owner_orcid=bulk_sample_info['owner']
    )

    current_parent = bulk_sample
    sample_chain = [bulk_sample]

    # Create preparation steps
    for i, step in enumerate(preparation_steps):
        prepared_sample = client.add_sample(
            unique_id=f"{bulk_sample_info['id']}-prep-{i+1}",
            sample_name=f"{step['name']} - Step {i+1}",
            description=step['description'],
            owner_orcid=bulk_sample_info['owner'],
            parents=[current_parent]
        )

        # Add preparation metadata
        client.add_sample_metadata(
            prepared_sample['unique_id'],
            "preparation_step",
            step_number=i+1,
            method=step['method'],
            conditions=step['conditions'],
            date=step.get('date'),
            notes=step.get('notes', '')
        )

        sample_chain.append(prepared_sample)
        current_parent = prepared_sample

    return sample_chain

# Example usage
bulk_info = {
    'id': 'bulk-silicon-001',
    'name': 'Silicon Wafer',
    'description': 'High-purity silicon wafer for device fabrication',
    'owner': '0000-0000-0000-0000'
}

prep_steps = [
    {
        'name': 'Cleaned Silicon',
        'description': 'RCA cleaned silicon surface',
        'method': 'RCA cleaning',
        'conditions': {'temperature': 80, 'duration_min': 15},
        'date': '2024-01-15'
    },
    {
        'name': 'Oxidized Silicon',
        'description': 'Thermal oxide grown on cleaned silicon',
        'method': 'thermal_oxidation',
        'conditions': {'temperature': 1100, 'time_hours': 2, 'atmosphere': 'dry_O2'},
        'date': '2024-01-16'
    },
    {
        'name': 'Patterned Silicon',
        'description': 'Photolithographically patterned oxide',
        'method': 'photolithography',
        'conditions': {'resist': 'SPR220', 'exposure_dose': 150},
        'date': '2024-01-17'
    }
]

sample_chain = create_sample_preparation_chain(client, bulk_info, prep_steps)
print(f"Created sample chain with {len(sample_chain)} samples")
```

### Multi-Sample Experiments

```python
def create_multi_sample_experiment(client, experiment_name, sample_ids, shared_conditions):
    """Create dataset linking multiple samples"""

    # Create experiment dataset
    dataset = client.create_dataset(
        dataset_name=experiment_name,
        measurement=shared_conditions['measurement'],
        instrument_name=shared_conditions.get('instrument'),
        scientific_metadata=shared_conditions,
        keywords=['multi-sample', 'comparison', shared_conditions['measurement'].lower()]
    )

    # Link all samples to dataset
    for sample_id in sample_ids:
        client.add_sample_to_dataset(dataset['unique_id'], sample_id)
        print(f"Linked sample {sample_id} to dataset")

    # Add comparative analysis metadata
    comparison_metadata = {
        'experiment_type': 'multi_sample_comparison',
        'sample_count': len(sample_ids),
        'sample_ids': sample_ids,
        'analysis_goal': shared_conditions.get('goal', 'comparative_analysis')
    }

    current_metadata = client.get_scientific_metadata(dataset['unique_id'])
    current_metadata.update(comparison_metadata)
    client.update_scientific_metadata(dataset['unique_id'], current_metadata)

    return dataset

# Example usage
sample_list = ['sample-001', 'sample-002', 'sample-003', 'sample-004']
conditions = {
    'measurement': 'UV-Vis Spectroscopy',
    'instrument': 'Agilent Cary 5000',
    'wavelength_range_nm': [200, 800],
    'scan_rate': 'medium',
    'goal': 'bandgap_determination'
}

comparison_dataset = create_multi_sample_experiment(
    client,
    "Bandgap Comparison Study",
    sample_list,
    conditions
)
```

## Data Processing

### Automated Processing Pipeline

```python
def process_dataset_pipeline(client, dataset_id, processing_steps):
    """Run a multi-step processing pipeline"""

    results = {}

    for step_name, step_config in processing_steps.items():
        print(f"Starting {step_name}...")

        # Request processing
        if step_config['type'] == 'ingest':
            req = client.request_ingestion(
                dataset_id,
                ingestor=step_config['processor']
            )
        elif step_config['type'] == 'scicat':
            req = client.send_to_scicat(dataset_id)
        elif step_config['type'] == 'transfer':
            req = client.request_google_drive_transfer(dataset_id)

        # Wait for completion if requested
        if step_config.get('wait', False):
            final_status = client.wait_for_request_completion(
                dataset_id,
                req['id'],
                step_config['type'],
                sleep_interval=step_config.get('poll_interval', 10)
            )
            results[step_name] = final_status

            if final_status['status'] != 'completed':
                print(f"❌ {step_name} failed: {final_status.get('error_message')}")
                break
            else:
                print(f"✅ {step_name} completed successfully")
        else:
            results[step_name] = req

    return results

# Example pipeline configuration
pipeline_config = {
    'ingest_data': {
        'type': 'ingest',
        'processor': 'spectroscopy_processor',
        'wait': True,
        'poll_interval': 15
    },
    'sync_scicat': {
        'type': 'scicat',
        'wait': True,
        'poll_interval': 30
    },
    'backup_drive': {
        'type': 'transfer',
        'wait': False
    }
}

# Run pipeline
pipeline_results = process_dataset_pipeline(
    client,
    "dataset-001",
    pipeline_config
)
```

### Batch Processing Multiple Datasets

```python
def batch_process_datasets(client, dataset_ids, processor_name):
    """Process multiple datasets in batch"""

    requests = []

    # Submit all processing requests
    for dataset_id in dataset_ids:
        try:
            req = client.request_ingestion(dataset_id, ingestor=processor_name)
            requests.append({
                'dataset_id': dataset_id,
                'request_id': req['id'],
                'status': 'submitted'
            })
            print(f"Submitted processing for {dataset_id}: {req['id']}")
        except Exception as e:
            print(f"Failed to submit {dataset_id}: {e}")
            requests.append({
                'dataset_id': dataset_id,
                'request_id': None,
                'status': 'failed',
                'error': str(e)
            })

    # Monitor all requests
    completed = 0
    while completed < len([r for r in requests if r['request_id']]):
        time.sleep(30)  # Check every 30 seconds

        for req_info in requests:
            if req_info['status'] == 'submitted':
                try:
                    status = client.get_ingestion_status(
                        req_info['dataset_id'],
                        req_info['request_id']
                    )

                    if status['status'] in ['completed', 'failed']:
                        req_info['status'] = status['status']
                        req_info['final_status'] = status
                        completed += 1
                        print(f"Dataset {req_info['dataset_id']}: {status['status']}")

                except Exception as e:
                    print(f"Error checking status for {req_info['dataset_id']}: {e}")

    # Summary
    successful = len([r for r in requests if r['status'] == 'completed'])
    failed = len([r for r in requests if r['status'] == 'failed'])

    print(f"\nBatch processing complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")

    return requests

# Example usage
dataset_list = ["dataset-001", "dataset-002", "dataset-003"]
batch_results = batch_process_datasets(client, dataset_list, "general_processor")
```

## Collaboration & Access

### Project Team Management

```python
def setup_project_collaboration(client, project_id, team_members, datasets_to_share):
    """Set up collaboration for a project"""

    # Get project info
    project = client.get_project(project_id)
    print(f"Setting up collaboration for: {project['project_name']}")

    # Add team members (admin function)
    # for member_orcid in team_members:
    #     try:
    #         client.add_user_to_access_group(member_orcid, project_id)
    #         print(f"Added {member_orcid} to project")
    #     except Exception as e:
    #         print(f"Could not add {member_orcid}: {e}")

    # Share specific datasets with project team
    for dataset_id in datasets_to_share:
        try:
            # Update dataset to include project
            dataset = client.get_dataset(dataset_id)
            if dataset.get('project_id') != project_id:
                # Would need dataset update endpoint
                print(f"Dataset {dataset_id} should be linked to project {project_id}")
        except Exception as e:
            print(f"Could not update dataset {dataset_id}: {e}")

    # Create collaboration summary dataset
    collab_dataset = client.create_dataset(
        dataset_name=f"Collaboration Summary - {project['project_name']}",
        project_id=project_id,
        measurement="Project Overview",
        scientific_metadata={
            'project_type': 'collaboration',
            'team_size': len(team_members),
            'shared_datasets': len(datasets_to_share),
            'collaboration_start': datetime.now().isoformat()
        },
        keywords=['collaboration', 'project-summary', 'team']
    )

    return collab_dataset

# Example usage
team_orcids = [
    "0000-0000-0000-0001",
    "0000-0000-0000-0002",
    "0000-0000-0000-0003"
]

shared_datasets = ["dataset-001", "dataset-002", "dataset-003"]

collab_summary = setup_project_collaboration(
    client,
    "collaboration-project-2024",
    team_orcids,
    shared_datasets
)
```

## Batch Operations

### Create Multiple Similar Datasets

```python
def create_dataset_series(client, base_name, conditions_list, shared_metadata):
    """Create multiple datasets with varying conditions"""

    created_datasets = []

    for i, conditions in enumerate(conditions_list):
        # Merge shared metadata with specific conditions
        full_metadata = {**shared_metadata, **conditions}

        dataset = client.create_dataset(
            dataset_name=f"{base_name} - Condition {i+1}",
            unique_id=f"{base_name.lower().replace(' ', '-')}-{i+1:03d}",
            measurement=shared_metadata['measurement'],
            scientific_metadata=full_metadata,
            keywords=shared_metadata.get('keywords', []) + [f"series-{i+1}"]
        )

        created_datasets.append(dataset)
        print(f"Created dataset {i+1}/{len(conditions_list)}: {dataset['unique_id']}")

    return created_datasets

# Example: Temperature series
shared_conditions = {
    'measurement': 'Raman Spectroscopy',
    'laser_wavelength_nm': 532,
    'laser_power_mw': 1.0,
    'integration_time_s': 10,
    'keywords': ['raman', 'temperature-series']
}

temperature_conditions = [
    {'temperature_k': 77, 'sample_state': 'cryogenic'},
    {'temperature_k': 150, 'sample_state': 'cold'},
    {'temperature_k': 200, 'sample_state': 'cool'},
    {'temperature_k': 250, 'sample_state': 'intermediate'},
    {'temperature_k': 300, 'sample_state': 'room_temperature'},
    {'temperature_k': 350, 'sample_state': 'warm'},
    {'temperature_k': 400, 'sample_state': 'hot'}
]

temp_series = create_dataset_series(
    client,
    "MoS2 Temperature Study",
    temperature_conditions,
    shared_conditions
)
```

## Integration Patterns

### Integration with Analysis Tools

```python
def integrate_with_analysis_pipeline(client, dataset_id, analysis_functions):
    """Download data, analyze, and upload results"""

    import tempfile
    import json
    from pathlib import Path

    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)

        # Download dataset
        print("Downloading data...")
        client.download_dataset(dataset_id, output_path=str(work_dir / "raw_data"))

        # Get metadata for analysis context
        metadata = client.get_scientific_metadata(dataset_id)

        # Run analysis functions
        analysis_results = {}
        for analysis_name, analysis_func in analysis_functions.items():
            print(f"Running {analysis_name}...")
            try:
                result = analysis_func(work_dir / "raw_data", metadata)
                analysis_results[analysis_name] = result

                # Save result file if generated
                if isinstance(result, dict) and 'file_path' in result:
                    result_file = Path(result['file_path'])
                    if result_file.exists():
                        client.add_associated_file(
                            dataset_id,
                            str(result_file),
                            filename=f"analysis_results/{analysis_name}_{result_file.name}"
                        )
            except Exception as e:
                print(f"Analysis {analysis_name} failed: {e}")
                analysis_results[analysis_name] = {'error': str(e)}

        # Update metadata with analysis results
        metadata['analysis_results'] = analysis_results
        metadata['analysis_date'] = datetime.now().isoformat()

        client.update_scientific_metadata(dataset_id, metadata)

        print("Analysis complete and results uploaded")
        return analysis_results

# Example analysis functions
def peak_analysis(data_file, metadata):
    """Example peak finding analysis"""
    # Placeholder for actual analysis
    return {
        'peaks_found': [100, 200, 300],
        'peak_intensities': [0.8, 1.0, 0.6],
        'analysis_method': 'scipy.signal.find_peaks'
    }

def background_subtraction(data_file, metadata):
    """Example background subtraction"""
    # Placeholder for actual analysis
    return {
        'background_method': 'polynomial_fit',
        'background_order': 3,
        'file_path': '/tmp/background_subtracted.dat'
    }

# Run integrated analysis
analysis_pipeline = {
    'peak_analysis': peak_analysis,
    'background_subtraction': background_subtraction
}

results = integrate_with_analysis_pipeline(
    client,
    "dataset-001",
    analysis_pipeline
)
```

### Custom Reporting

```python
def generate_project_report(client, project_id, output_file):
    """Generate comprehensive project report"""

    import json
    from datetime import datetime

    # Get project info
    project = client.get_project(project_id)
    datasets = client.list_datasets(project_id=project_id)

    # Collect statistics
    stats = {
        'project_info': project,
        'total_datasets': len(datasets),
        'measurements': {},
        'keywords': {},
        'date_range': {'earliest': None, 'latest': None}
    }

    # Analyze datasets
    for dataset in datasets:
        # Count measurements
        measurement = dataset.get('measurement', 'Unknown')
        stats['measurements'][measurement] = stats['measurements'].get(measurement, 0) + 1

        # Count keywords
        try:
            keywords = client.get_dataset_keywords(dataset['unique_id'])
            for kw in keywords:
                keyword = kw['keyword']
                stats['keywords'][keyword] = stats['keywords'].get(keyword, 0) + 1
        except:
            pass

        # Track date range
        creation_time = dataset.get('creation_time')
        if creation_time:
            if not stats['date_range']['earliest'] or creation_time < stats['date_range']['earliest']:
                stats['date_range']['earliest'] = creation_time
            if not stats['date_range']['latest'] or creation_time > stats['date_range']['latest']:
                stats['date_range']['latest'] = creation_time

    # Generate report
    report = {
        'report_generated': datetime.now().isoformat(),
        'project_summary': {
            'name': project['project_name'],
            'id': project['project_id'],
            'lead': project.get('project_lead_email', 'Unknown'),
            'description': project.get('description', '')
        },
        'statistics': stats,
        'top_measurements': sorted(stats['measurements'].items(), key=lambda x: x[1], reverse=True)[:5],
        'top_keywords': sorted(stats['keywords'].items(), key=lambda x: x[1], reverse=True)[:10],
        'dataset_list': [
            {
                'id': ds['unique_id'],
                'name': ds.get('dataset_name', 'Unnamed'),
                'measurement': ds.get('measurement', 'Unknown'),
                'creation_time': ds.get('creation_time')
            }
            for ds in datasets
        ]
    }

    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to {output_file}")
    print(f"Project: {report['project_summary']['name']}")
    print(f"Total datasets: {stats['total_datasets']}")
    print(f"Top measurement: {report['top_measurements'][0] if report['top_measurements'] else 'None'}")

    return report

# Generate report
project_report = generate_project_report(
    client,
    "my-project-2024",
    "project_report.json"
)
```

These examples demonstrate practical patterns for using PycrucibleClient in real research workflows. Adapt them to your specific domain and requirements!