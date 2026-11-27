# 0004 Waterfall plots

- **Status:** implemented
- **Module:** `ae_pipeline/plots/task_plot_waterfall.py` (`task_plot_waterfall`, `task_plot_waterfall_intervals`)

## Summary

Waterfall plots of the hit spectrograms of all channels, one row per channel stacked in one figure, so the channels can be compared visually on a shared time and frequency axis. The waveform of each hit is taken from the hits table, a short-time Fourier transform (STFT) gives its spectrogram, and the part within the time span of the hit is binned onto a time grid with about one bin per pixel. Time without hits is empty. One figure covers the whole acquisition and is annotated with the marker labels; a second task draws one figure per sufficiently long label interval.

## Inputs

- `Dataset.hits_file` (0003): `time`, `duration`, `channel`, `pretrigger`, `signal` (waveform in µV).
- `Dataset.metadata_file` (0002): channels, sample rate and marker labels.

The tradb is not read.

## Outputs

- `plots/<name>/waterfall`: whole acquisition, one file per format of `PLOT_FORMATS` (0010 R1–R2).
- Directory `plots/<name>/waterfall/` with one `<label>.<fmt>` per qualifying label interval (R6) and format, declared as a `pytask.DirectoryNode` product.

## Parameters

| Name             | Value                                   | Meaning                                                           |
| ---------------- | --------------------------------------- | ----------------------------------------------------------------- |
| `COLOR_RANGE`    | −60 … 10 dB(AE)/Hz                      | fixed color normalization                                         |
| color map        | `inferno`, reversed                     | high power is dark                                                |
| `ANNOTATION_GAP` | 1.0 s                                   | minimum label interval to be annotated in the overall figure (R5) |
| `INTERVAL_GAP`   | 2.0 s                                   | minimum label interval to get its own figure (R6)                 |
| figure size      | 20.0 in × (2.4 in × number of channels) | the only allowed override of a global default (0010 R7)           |

The spectral settings (window, segment length, hop) are those of 0009, the same as for the hit PSDs of 0003.

## Requirements

### Figure (shared by all waterfall figures)

1. The figure has one row per channel in the `channels` table of the metadata (0002 R6), in that order (ascending channel number), and a common colorbar on the right. All rows share the time axis, the frequency axis and the color normalization, so the channels can be compared directly. A channel without hits is drawn entirely as a gap (R2). Apart from the figure size, the global matplotlib defaults apply (0010 R7).

2. Each row is one image on a time grid of `N` equal bins over the plotted time range, with `N = round(figure width in inches × figure dpi)`, i.e. about one bin per pixel. The images of all channels are computed together:

   - For each hit of the channel whose span `[time, time + duration]` overlaps the plotted time range, the spectrogram of its `signal` is computed with `short_time_fft(sample_rate).spectrogram(signal)` (0009 R3), in µV²/Hz at the frequencies `psd_frequencies(sample_rate)` (0009 R1). `sample_rate` comes from the metadata (0002 R5).
   - The record starts at `time - pretrigger / sample_rate`. STFT column `k` is centered at `record start + k * HOP / sample_rate` and covers one hop around its center.
   - Only the part of each column within the hit span (the actual duration of the hit, not its pretrigger or the samples after the hit end) and within the plotted time range is used.
   - Each time bin holds, per frequency, the maximum PSD of all used column parts that overlap the bin, so short hits stay visible and overlapping hits do not hide each other.
   - Bins without any hit have no power density at any frequency, i.e. a PSD of 0 (−∞ dB(AE)/Hz). They are drawn in the color of the lower end of the color range.
   - The image shows `power_to_dB(...)` (0008 R4) in dB(AE)/Hz, unchanged and not clipped. The detection threshold plays no role.

   The hits table is read in a single streaming pass (e.g. with `pyarrow.dataset`), batch by batch, reading only the needed columns and the row groups whose `time` statistics overlap the plotted range (0003 R5); each hit is added to the image of its channel. The whole table is never loaded at once.

   Each image is placed so that frequency bin `i` is centered at its frequency `psd_frequencies(sample_rate)[i]`, i.e. the image extent reaches half a bin below 0 and above the Nyquist frequency; the y limits stay 0 … Nyquist frequency.

3. Axes: x is `r"Time $t$ in \unit{\second}"` from acquisition start, labelled only on the bottom row; y is `r"Frequency in \unit{\kilo\hertz}"` from 0 to the Nyquist frequency (converted with `hz_to_khz`, 0008 R5), labelled on every row (0010 R5). The overall figure spans from 0 to the end of the last hit of any channel or the time of the last label, whichever is later, so labels after the last hit are shown too; per-interval figures span the range given in R7. Each row is annotated with `Channel <n>` in red in its top-left corner.

4. The colorbar is labelled `r"Power Spectral Density in \unit{\dBAE\per\hertz}"`. Its range is `COLOR_RANGE`.

### Overall figure

5. `task_plot_waterfall` (id `<name>`) plots the whole acquisition. For each label interval from `label_intervals(metadata, ANNOTATION_GAP)` (0002 R12), a red vertical line is drawn at its start in every row, annotated with the label text (escaped for LaTeX, 0010 R5). A label of the form `HH:MM text` is shown on two lines (`HH:MM` / `text`).

### Per-interval figures

6. `task_plot_waterfall_intervals` (id `<name>`) draws one figure per label interval from `label_intervals(metadata, INTERVAL_GAP)` (0002 R12), all in one task. It is not a generator task; its products are the files in the `DirectoryNode` `plots/<name>/waterfall/` (pattern `*`). It deletes all existing files in the directory before writing (`docs/conventions.md`, Tasks).
7. Each per-interval figure covers exactly its label interval `[start, end]` and has no label annotations. Intervals without any hit get a figure too, drawn entirely as gaps, so that every interval is documented.
8. If there is no qualifying interval, the task writes no file (the directory is left empty; old files are deleted first, R6) and emits a warning naming the dataset.
9. The file name of a per-interval figure is its label text sanitized according to the file name rule in `docs/conventions.md` (Package layout), e.g. `11:19 ruhe` → `waterfall/1119_ruhe.png`. Two labels that sanitize to the same name are an error (`ValueError` naming the dataset and the labels).

### Dependencies

10. Both tasks declare `ae_pipeline/units.py`, `ae_pipeline/spectral.py` and `ae_pipeline/metadata.py` as dependencies (`docs/conventions.md`, Tasks).

## Open questions

None.
