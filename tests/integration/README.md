# Integration Tests

These tests hit the live Crucible API. They require a valid API key and network access.

## Setup

```bash
crucible config init   # configure your API key
```

## Run

```bash
# all integration tests
pytest tests/integration/ -v

# single module
pytest tests/integration/test_datasets.py -v

# stop on first failure
pytest tests/integration/ -x
```

## Notes

- Tests use the `crucible-test` project — do not run against production projects
- Tests create real records; they are not cleaned up automatically
- File upload tests (`test_files.py`) require the `/files/{mfid}/ingest` API endpoint
- Some tests require admin privileges and will be skipped otherwise
