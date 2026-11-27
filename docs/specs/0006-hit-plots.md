# 0006 Hit plots

- **Status:** partially implemented (not yet implemented: R2 the threshold line uses the hard-coded `THRESHOLD = 32` instead of the channel threshold, the level is read from the stored `signal_dB` instead of computed from `signal`, the level is always reduced to 1000 points by reshaping instead of the block maximum with variable window, the hit start and end lines are missing, the sample rate and frequencies come from the hits table, and the labels are not typeset with LaTeX; R3 outputs do not use `PLOT_FORMATS` and old files are not deleted; R4 the figure size is overridden with `figsize=(6.4, 4.8)`; R5 the shared modules are not declared as dependencies)
- **Module:** `ae_pipeline/plots/task_plot_hits.py` (`task_plot_hits`)

## Summary

One figure per hit, showing the envelope of its waveform level and its PSD with the detected peaks. The task is optional because it produces one file per hit and is slow.

## Inputs

- `Dataset.hits_file` (0003): `signal`, `pretrigger`, `duration`, `channel`, `psd`, `peaks`.
- `Dataset.metadata_file` (0002): sample rate and detection threshold per channel.
- Flag `EACH_HIT` in `ae_pipeline/task_config.py`.

## Outputs

- Directory `ae_pipeline/plots/<name>/hits/` with one `hit_<trai>.<fmt>` per row of the hits table and format of `PLOT_FORMATS` (0010 R1). It is declared as a `pytask.DirectoryNode` product with pattern `*`.

## Parameters

| Name         | Value | Meaning                                                  |
| ------------ | ----- | -------------------------------------------------------- |
| `MAX_POINTS` | 10000 | maximum number of points of the level envelope plot (R2) |

The sample rate is the same for all hits of a dataset (0002 R5, R10), so the number of samples of a record is proportional to its duration.

## Requirements

1. One task per dataset with id `<name>`. It is skipped (`pytask.mark.skipif`) unless `EACH_HIT` is `True`.
2. Each figure has two rows:
   1. **Level:** the level of the waveform, `signal_dB = amplitude_to_dB(signal)` (0008 R2), computed in the task (it is not stored in the hits table). Its envelope is a block maximum (moving maximum with non-overlapping windows). With `n = len(signal_dB)`, the window size is `w = ceil(n / MAX_POINTS)` samples, so it varies with the record length and the plot has at most `MAX_POINTS` points. The signal is split into consecutive blocks of `w` samples (the last block may be shorter), and each block gives its maximum, e.g. `np.maximum.reduceat(signal_dB, np.arange(0, n, w))`. Records with at most `MAX_POINTS` samples are plotted unchanged (`w = 1`). Each point is plotted at the time of the first sample of its block, `np.arange(0, n, w) / sample_rate`, i.e. the time axis starts at the start of the transient record (t = 0), including the pretrigger.
      - Two vertical lines mark the hit: its start (threshold crossing) at `pretrigger / sample_rate` and its end at `pretrigger / sample_rate + duration`.
      - A red dashed horizontal line marks the detection threshold of the hit's channel, `amplitude_to_dB(channels.<n>.threshold)` from the metadata (0002 R6, stored in µV).
      - y-axis `r"Intensity in \unit{\dBAE}"`, limits 0 … 100. x-axis `r"Time $t$ in \unit{\second}"` (0010 R5).
   2. **Spectrum:** `psd` against frequency `psd_frequencies(sample_rate)` (0009 R1) in kHz. x-axis `r"Frequency in \unit{\kilo\hertz}"`, y-axis `r"Power Spectral Density in \unit{\micro\volt\squared\per\hertz}"`, lower limit 0. Each entry of `peaks` is marked with a red `+` and annotated with its frequency in kHz (rounded to an integer).
3. The figure for the hit with index `trai` is saved as `hit_<trai>` in every format of `PLOT_FORMATS` and closed afterwards. Before writing, the task deletes all existing files in `plots/<name>/hits/` (`docs/conventions.md`, Tasks), so figures of hits that no longer exist do not remain.
4. The figures use the global matplotlib defaults from `task_config.py` (0010), including the figure size; the task does not override any of them.
5. The task declares `ae_pipeline/units.py`, `ae_pipeline/spectral.py` and `ae_pipeline/metadata.py` as dependencies (`docs/conventions.md`, Tasks).

## Open questions

None.
