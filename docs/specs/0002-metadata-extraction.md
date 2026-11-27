# 0002 Metadata extraction

- **Status:** partially implemented (not yet implemented: R1 the task is still named `task_plot_extract_metadata`; R2 and R5 `record_length` is still written; R2 and R6 the channel list is still `general.channels` and the `channels` table with thresholds (including the default and its warning) is missing; R7 duplicate marker texts are silently overwritten; R8 an empty tradb fails with a `NameError`; R9 and R10 are not checked; R11–R13 `ae_pipeline/metadata.py` does not exist, consumers parse the TOML themselves)
- **Module:** `ae_pipeline/data/task_extract_metadata.py` (`task_extract_metadata`), `ae_pipeline/metadata.py` (`Metadata`, `load_metadata`, `LabelInterval`, `label_intervals`)

## Summary

For each dataset, extract the acquisition settings, the detection threshold of every channel and the user-set marker labels into a small TOML file. Downstream tasks use it instead of opening the Vallen databases again. It is the only source of detection thresholds in the pipeline.

## Inputs

- `Dataset.primary_file` (`*.pridb`): channels, global info, hits (thresholds), markers.
- `Dataset.transient_file` (`*.tradb`): sample rates of all records.

## Outputs

- `Dataset.metadata_file` (`<name>.metadata.toml`).

## Parameters

| Name                | Value     | Meaning                                                                                       |
| ------------------- | --------- | --------------------------------------------------------------------------------------------- |
| `DEFAULT_THRESHOLD` | 32 dB(AE) | detection threshold of channels without hits (R6), stored as `dB_to_amplitude(32)` ≈ 39.81 µV |

## Requirements

1. The task function is named `task_extract_metadata`. There is one task per dataset with id `<name>`.

2. The output is a TOML document with exactly three tables:

   ```toml
   [general]
   clock_rate = 10000000      # int, pridb global info "TimeBase", in Hz
   sample_rate = 10000000     # sample rate of all tradb records, in Hz

   [channels.1]               # one table per channel, in pridb order
   threshold = 28.9237         # detection threshold, in µV

   [channels.2]
   threshold = 28.9237

   [labels]
   "11:19 ruhe" = 0.0         # marker text -> marker time in s
   "11:20 walze dreht" = 57.7
   ```

3. `labels` contains the markers of the pridb with `set_type == 4` (label markers) whose text does not contain `TimeZone:`. They appear in pridb order, i.e. in ascending time.

4. The label key is the marker text verbatim, including the time-of-day prefix (`HH:MM `) and Vallen's own `Resume`/`Suspend` labels. The value is the marker time in seconds from the start of the acquisition.

5. `sample_rate` is the sample rate of the tradb records, which is the same for all records of a dataset (R10). It is the only source of the sample rate in the pipeline; the hits table does not store it. The distinct sample rates are read without loading the waveforms, e.g. `SELECT DISTINCT SampleRate FROM tr_data` through `tradb.connection()`. There is no record length in the metadata, because record lengths vary between hits.

6. `channels` contains one sub-table per channel of the pridb, in pridb order, keyed by the channel number (TOML parses the key as the string `"1"`). It is the channel list of the dataset and holds all per-channel data. Currently it has one key:

   - `threshold`: the detection threshold of the channel in µV. The threshold is the one stored with the channel's hits in the pridb (Vallen field `Thr`; `vallenae` returns it in V as the hit column `threshold`, converted with `volts_to_microvolts`, 0008 R1). Channels without any hit get the default threshold `DEFAULT_THRESHOLD` = 32 dB(AE), a module-level constant of the task module given in dB(AE) and stored converted with `dB_to_amplitude` (0008 R3). In that case a warning is emitted that names the dataset and the channel, so a quiet or disconnected channel does not go unnoticed. All tasks that need a detection threshold read it from here; thresholds are never hard-coded.

   Further per-channel data is added as keys of these sub-tables, not as new top-level tables.

### Malformed datasets

A dataset is malformed if one of the following conditions holds. The task then raises a `ValueError` whose message names the dataset and the condition, and writes no output. pytask reports the task as failed and skips the tasks that depend on its product; tasks of other datasets are not affected.

07. Two or more of the markers selected by R3 have the same text. The error message lists the duplicate texts.

08. The tradb contains no records, so `sample_rate` cannot be determined. Unlike a missing tradb (0001 R4), this is not skipped during discovery, because detecting it requires opening the database.

09. The hits of one channel have more than one distinct threshold, so R6 cannot assign a single threshold to it. The error message lists the channel and its thresholds.

10. The tradb records have more than one distinct sample rate. The error message lists the sample rates.

### Reading the metadata

11. `ae_pipeline/metadata.py` defines a pydantic model `Metadata` of the TOML document of R2 (`general.clock_rate`, `general.sample_rate`, `channels` as a mapping from channel number (int) to a model with `threshold`, `labels` as an ordered mapping from text to time) and `load_metadata(path) -> Metadata`. All consumers read the metadata through it; no task parses the TOML itself. Changing the document (R2) and the model is one change.

12. `label_intervals(metadata, min_length) -> list[LabelInterval]` returns the intervals between consecutive labels, `LabelInterval(label, start, end)` with `start = label.time` and `end = next.time`, for every pair of consecutive labels with `end - start >= min_length` and `"Suspend"` not in the label text. The last label starts no interval. This is the only definition of label intervals in the pipeline (used by 0004 R5 and R6). It is covered by pytest tests in `tests/test_metadata.py` (minimum length, `Suspend` labels, last label, fewer than two labels).

13. Tasks that use `ae_pipeline/metadata.py` declare it as a dependency (`docs/conventions.md`, Tasks).

## Open questions

None.
