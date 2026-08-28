# Instrument Model

| Field | Description | Settable |
|---|---|---|
| `instrument_id` | Unique 3-to-25-character slug used to reference the instrument | create, update |
| `instrument_name` | Human-readable display name | create, update |
| `owner` | Person or group responsible for the instrument | create, update |
| `location` | Physical location (e.g. room number or building) | create, update |
| `manufacturer` | Instrument manufacturer (e.g. `"FEI"`, `"Bruker"`) | create, update |
| `model` | Manufacturer model name or number | create, update |
| `instrument_type` | Category of instrument (e.g. `"Transmission electron microscope"`) | create, update |
| `description` | Free-text description of the instrument | create, update |
| `other_id` | External identifier (e.g. facility inventory number, RRID, DOI) | create, update |
| `other_id_source` | Source of the external identifier (e.g. `"RRID"`, `"DOI"`) | create, update |
| `unique_id` | System-assigned MFID identifier | server-assigned |
| `creation_time` | When the record was created | server-assigned |
| `modification_time` | When the record was last modified | server-assigned |

New and renamed instrument IDs must contain 3 to 25 characters. Lookup remains compatible with older IDs outside that range.

# Working with Instruments

## Creating an instrument

Instruments are shared across all projects. If an instrument with the same `instrument_id` slug already exists, `create()` returns the existing record rather than creating a duplicate.

```python
from crucible.models import Instrument

instrument = client.instruments.create(Instrument(
    instrument_id="team-i",
    instrument_name="TEAM I",
    manufacturer="FEI",
    model="Titan 80-300",
    owner="LBNL MF NCEM",
    location="72-150",
    instrument_type="Transmission electron microscope",
    description="Aberration-corrected TEM/STEM with monochromator",
    other_id="SCR_023886",
    other_id_source="RRID",
))
```

## Listing instruments

```python
instruments = client.instruments.list()
for i in instruments:
    print(i["instrument_name"], i["location"])
```

## Getting an instrument

```python
instrument = client.instruments.get("team-i")
# or by canonical MFID
instrument = client.instruments.get("0tkn2knjast3h0008nyq9zps2c")
```

Use `instrument_id=` or `instrument_mfid=` when the intended identifier type must be explicit. Display names are not identifiers and are not accepted by the general lookup. For compatibility, an MFID-shaped value supplied as `instrument_id=` is temporarily treated as an MFID and emits a deprecation warning.

## Updating an instrument

```python
client.instruments.update("0tkn2knjast3h0008nyq9zps2c", description="Updated description", location="72-200")
```

## Referencing instruments in datasets

Once registered, reference an instrument in datasets by its slug:

```python
from crucible.models import Dataset

dataset = client.datasets.create(dataset=Dataset(
    dataset_name="HAADF-STEM image of Au NPs",
    measurement="STEM imaging",
    instrument_id="team-i",
    project_id="MFP12345",
))
```
