# Downloading Data

## Download a dataset

`client.datasets.download()` saves the API record as `record.json` and downloads the dataset's associated files:

```python
# Download everything into a local directory
dataset_mfid = "0tkn2knjast3h0008nyq9zps2c"
client.datasets.download(dataset_mfid, output_dir="./downloads")
```

This creates `./downloads/0tkn2knjast3h0008nyq9zps2c/record.json` plus all files.

### Filtering files

```python
# Download only .dat files
client.datasets.download(dataset_mfid, output_dir="./downloads", include=["*.dat"])

# Download everything except thumbnails
client.datasets.download(dataset_mfid, output_dir="./downloads", exclude=["*.png"])
```

### Overwriting existing files

By default, files that already exist locally are replaced. Set `overwrite_existing=False` to keep them:

```python
client.datasets.download(
    dataset_mfid,
    output_dir="./downloads",
    overwrite_existing=False,
)
```

## Download a sample record

For samples, `client.samples.download()` saves the API record as `record.json`:

```python
sample_mfid = "0td7evvtg5wb90005k1j97ak94"
client.samples.download(sample_mfid, output_dir="./downloads")
```

## Get pre-signed download URLs

If you need temporary signed download URLs for a script, request the mapping of file MFIDs to URLs:

```python
links = client.datasets.get_download_links(dataset_mfid)
for file_mfid, url in links.items():
    print(file_mfid, url)
```

Signed URLs grant temporary access. Avoid logging or sharing them beyond their intended recipient.

## CLI

```bash
# Download a dataset or sample by ID (type auto-detected)
crucible download DATASET_MFID

# Specify output directory
crucible download DATASET_MFID --output-dir ./my-data

# Filter by filename pattern
crucible download DATASET_MFID --include "*.dm4"

# Skip downloading files (record.json only)
crucible download DATASET_MFID --no-files

# Keep existing files instead of replacing them
crucible download DATASET_MFID --no-overwrite

# List files without downloading
crucible dataset list-files DATASET_MFID
```

## Caching

The CLI caches downloaded files so repeated downloads don't re-fetch from the server. Manage the cache with:

```bash
crucible cache show                        # view cache size and top files
crucible cache clear --older-than 30       # remove entries not accessed in 30 days
crucible cache clear --dataset DATASET_MFID  # remove a specific dataset
crucible cache clear -y                    # wipe the entire cache
```
