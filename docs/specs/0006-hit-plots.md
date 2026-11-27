# 0006 Hit plots

- **Status:** implemented
- **Module:** `ae_pipeline/plots/task_plot_hits.py` (`task_plot_hits`)

## Summary

One figure per hit, showing the full waveform (downsampled), its level envelope, and its PSD with the detected peaks. The task is optional because it produces one file per hit and is slow.

## Inputs

- `Dataset.hits_file` (0003): `signal`, `pretrigger`, `duration`, `channel`, `psd`, `peaks`.
- `Dataset.metadata_file` (0002): sample rate and detection threshold per channel.
- Flag `EACH_HIT` in `ae_pipeline/task_config.py`.

## Outputs

- Directory `ae_pipeline/plots/<name>/hits/` with one `hit_<trai>.<fmt>` per row of the hits table and format of `PLOT_FORMATS` (0010 R1). It is declared as a `pytask.DirectoryNode` product with pattern `*`.

## Parameters

| Name         | Value  | Meaning                                                                |
| ------------ | ------ | ---------------------------------------------------------------------- |
| `MAX_POINTS` | 10000  | maximum number of points of each downsampled waveform plot (R2, R3)    |
| `ROW_HEIGHT` | 80 mm  | height of each row in the figure (R2, R3)                              |

The sample rate is the same for all hits of a dataset (0002 R5, R10), so the number of samples of a record is proportional to its duration. Time is relative to the first threshold crossing (t = 0 at hit start). The x-axis uses µs for short signals (≤ 1 ms) or ms for longer signals, with an appropriate unit prefix.

## Requirements

1. One task per dataset with id `<name>`. It is skipped (`pytask.mark.skipif`) unless `EACH_HIT` is `True`.
2. Each figure has three rows:
   1. **Waveform:** the full signal in µV, downsampled to at most `MAX_POINTS` points using FFT-based resampling. With `n = len(signal)`, if `n > MAX_POINTS`, the signal is resampled to `MAX_POINTS` points using a frequency-domain approach (zeroing high-frequency components after FFT).
   2. **Level:** the level of the waveform, `signal_dB = amplitude_to_dB(signal)` (0008 R2), computed in the task (it is not stored in the hits table). Its envelope is a block maximum (moving maximum with non-overlapping windows) applied to the original signal before downsampling. With `n = len(signal_dB)`, if `n > MAX_POINTS`, the window size is `w = ceil(n / MAX_POINTS)` samples, and the signal is split into consecutive blocks of `w` samples (the last block may be shorter), with each block giving its maximum, e.g. `np.maximum.reduceat(signal_dB, np.arange(0, n, w))`. Each point is plotted at the time of the first sample of its block, `(np.arange(0, n, w) - pretrigger) / sample_rate`, so t = 0 at the hit start.
   3. **Spectrum:** `psd` against frequency `hz_to_khz(psd_frequencies(sample_rate))` (0008 R5, 0009 R1) in kHz.
   
   For rows 1 and 2:
   - Two vertical lines mark the hit: its start (threshold crossing) at t = 0 and its end at `duration / sample_rate`.
   - A red dashed horizontal line marks the detection threshold of the hit's channel, `amplitude_to_dB(channels.<n>.threshold)` from the metadata (0002 R6, stored in µV).
   - y-axis `r"Intensity in \unit{\dBAE}"`, limits 0 … 100 for row 2; y-axis `r"Amplitude in \unit{\micro\volt}"` for row 1. x-axis `r"Time $t$ in \unit{\micro\second}"` or `r"Time $t$ in \unit{\milli\second}"` depending on signal length (0010 R5).
   
   For row 3:
   - x-axis `r"Frequency in \unit{\kilo\hertz}"`, y-axis `r"Power Spectral Density in \unit{\micro\volt\squared\per\hertz}"`, lower limit 0. Each entry of `peaks` is marked with a red `+` and annotated with its frequency in kHz (rounded to an integer). The peak markers and annotations have their own style (thin marker lines, small font); this is intended and allowed besides 0010 R7.

## Open questions

None.
