# Linking Resources

Crucible supports links between datasets and between datasets and samples. Links let you represent relationships like:

- A processed dataset derived from a raw dataset (dataset → dataset)
- A sample that a dataset was measured from (dataset ↔ sample)
- A sample synthesized from another sample (sample → sample)

---

## Dataset ↔ Sample links

```python
# Link a dataset to a sample
client.samples.link_dataset(sample_mfid=sample_mfid, dataset_mfid=dataset_mfid)

# Or equivalently from the dataset side
client.datasets.link_sample(dataset_mfid=dataset_mfid, sample_mfid=sample_mfid)

# Remove a link
client.samples.unlink_dataset(sample_mfid=sample_mfid, dataset_mfid=dataset_mfid)
```

List the readable resources on either side of the relationship through the canonical collection filters:

```python
datasets = client.datasets.list(sample_mfid=sample_mfid)
samples = client.samples.list(dataset_mfid=dataset_mfid)
```

These methods use cursor pagination and return only related resources the caller may read. The older nested relationship reads remain an API compatibility surface but are not used by current Nano methods.

---

## Dataset → Dataset (parent-child)

Use parent-child links to represent processing pipelines:

```python
# Establish raw → processed relationship
client.datasets.link(
    parent_mfid=raw_dataset_mfid,
    child_mfid=processed_dataset_mfid,
)

# Remove it
client.datasets.unlink(
    parent_mfid=raw_dataset_mfid,
    child_mfid=processed_dataset_mfid,
)

# Navigate
parents = client.datasets.list_parents(processed_dataset_mfid)
children = client.datasets.list_children(raw_dataset_mfid)
```

---

## Sample → Sample (parent-child)

```python
# Establish provenance: boule → wafer
client.samples.link(
    parent_mfid=boule_sample_mfid,
    child_mfid=wafer_sample_mfid,
)

# Remove it
client.samples.unlink(
    parent_mfid=boule_sample_mfid,
    child_mfid=wafer_sample_mfid,
)

# Navigate
parents = client.samples.list_parents(wafer_sample_mfid)
children = client.samples.list_children(boule_sample_mfid)
```

---

## Generic link/unlink (auto-detects types)

If you have two IDs and don't want to look up their types first:

```python
# Works for dataset-sample, dataset-dataset, or sample-sample pairs
client.link(dataset_mfid, sample_mfid)
client.unlink(dataset_mfid, sample_mfid)
```

---

## Viewing all links for a resource

```python
# Returns immediate links for any resource MFID
links = client.get_links(dataset_mfid)
```

---

## Graph traversal

For a visual or programmatic view of the full relationship graph:

```python
# First-degree connections
graph = client.graphs.get(dataset_mfid)

# Full connected component
graph = client.graphs.get(dataset_mfid, recursive=True)

# All resources in a project
graph = client.graphs.project("MFP12345")

# As a networkx DiGraph
G = client.graphs.get(dataset_mfid, recursive=True, as_networkx=True)
```

Relationship lists and graphs are authorized views. An inaccessible starting resource returns 403, while readable graphs omit resources the caller cannot access and any edges connected to them. A smaller graph therefore does not imply that records or relationships were deleted.

---

## CLI

```bash
# Link any two resources (type auto-detected)
crucible link -p PARENT_MFID -c CHILD_MFID

# Unlink
crucible unlink MFID_A MFID_B

# View the graph for a resource
crucible tree RESOURCE_MFID
```
