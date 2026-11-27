# 0007 BIRCH clustering of hits

- **Status:** draft (task exists but has no products)
- **Module:** `ae_pipeline/classify/task_birch_cluster.py` (`task_birch_cluster`)

## Summary

Group the hits of a dataset into clusters by their spectral content, using the BIRCH algorithm on the PSD peaks from 0003.

## Inputs

- `Dataset.hits_file` (0003).

## Outputs

- a pickle file storing the state of the trained clusterer for later prediction usage
- several plots visualizing the clusters (see below)
- a summary file describing the overall result:
  - number of clusters
  - rating of the quality of separation

## Clustering procedure

- Use BIRCH clusterer of `scikit-learn` as it is scalable and provides a `predict` method to classify new hits depending on the already trained clusters.
- Cluster per dataset.

### Features

- Do *not* use any absolute signal strength/energy related features as they are misleading due to unpredictable signal damping between the source and the senors.
- Pre-cluster the present peaks over the whole dataset before defining the peak feature set to count peaks in several samples that are close as a single one.
- Apply feature normalization.

Integral/summary features:

- Time of arrival
- Duration
- RiseT / Duration
- Temporal centroid of signal strength / Duration

Frequency features:

- Peak frequencies
- Relative height (normed on the max peak height)

## Plots to generate

### Cluster rate over time

- plot with one line per cluster, distinguished by color
- y axis shows rate of hits that belong to a cluster per time unit

### Scatter plot

- a plot matrix of scatters of pairwise features
- cluster label distinguished by color

### Violin plots

- violin plot of cluster counts
- one plot per feature
- one violin per cluster

### Histograms

- histograms of cluster counts over the feature value
- one plot per feature
- bars are stacked

## Background information

- the data stems from acoustic measurements on rolling plants
- some clusters are expected to contain hits of only a short period of time (e.g. because of positioning of the rolls), some more distributed (e.g. because of roll rotation or rolled samples)
- The signal damping between the source and the sensor may be quite high due to bad coupling (e.g. in bearings) and also unreliable, so the information content in this is limited
- multiple hits on different channels may stem from the same source event with some time offset, their connection is omitted for now but shall be regarded in a sperate clustering procedure

## Open questions

These have to be answered before this spec can be implemented:

- Features: which features describe a hit? For example, the peak frequencies in kHz (a variable number per hit, so they need a fixed-length encoding such as the top-k peaks or a binned histogram), PSD band powers, or the Vallen hit features (amplitude, duration, rise time, counts).
- Algorithm: which implementation (scikit-learn `Birch` is not a dependency yet) and which parameters (`threshold`, `branching_factor`, `n_clusters`)? Should features be scaled?
- Scope: are clusters computed per dataset, per channel, or across all datasets?
- Output: a cluster label per `trai`, e.g. as a new `<name>.clusters.parquet`, plus which plots (cluster sizes over time, mean PSD per cluster)?
