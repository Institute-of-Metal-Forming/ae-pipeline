# 0005 Edge filter plots

- **Status:** withdrawn (done: the module is deleted)
- **Module:** `ae_pipeline/plots/task_plot_edge_filter.py` (to be removed)

## Summary

The edge filter plots (smoothed time derivative of the STFT spectrogram of the continuous waveforms) are no longer part of the pipeline.

## Requirements

1. The module `ae_pipeline/plots/task_plot_edge_filter.py` is deleted, so pytask no longer collects any edge filter task.
2. No other module depends on it. Code that only existed to be shared with it is not kept for that reason.
3. Existing products `ae_pipeline/plots/<name>/edge_filter*.png` are obsolete and can be deleted. They are gitignored, so this only affects local working copies.

## Open questions

None.
