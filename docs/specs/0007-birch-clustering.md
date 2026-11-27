# 0007 BIRCH clustering of hits

- **Status:** draft (task exists but has no products)
- **Module:** `ae_pipeline/classify/task_birch_cluster.py` (`task_birch_cluster`)

## Summary

Group the hits of a dataset into clusters by their spectral content, using the BIRCH algorithm on the PSD peaks from 0003.

## Inputs

- `Dataset.hits_file` (0003).

## Outputs

Not defined yet.

## Current state

1. One task per dataset with id `<name>` reads the hits table and converts the `peaks` column to a NumPy array. Nothing is computed or written yet.

## Open questions

These have to be answered before this spec can be implemented:

- Features: which features describe a hit? For example, the peak frequencies in kHz (a variable number per hit, so they need a fixed-length encoding such as the top-k peaks or a binned histogram), PSD band powers, or the Vallen hit features (amplitude, duration, rise time, counts).
- Algorithm: which implementation (scikit-learn `Birch` is not a dependency yet) and which parameters (`threshold`, `branching_factor`, `n_clusters`)? Should features be scaled?
- Scope: are clusters computed per dataset, per channel, or across all datasets?
- Output: a cluster label per `trai`, e.g. as a new `<name>.clusters.parquet`, plus which plots (cluster sizes over time, mean PSD per cluster)?
