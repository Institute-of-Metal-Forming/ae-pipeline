# 0003 Hit characterization

- **Status:** partially implemented (not yet implemented: R2 `trai` is still `uint16` and hits without a transient record are not skipped; R3 `amplitude` is still in V, float columns are float64 and `counts` is uint16; R9 is not checked; R4 the `pretrigger` and `signal` columns are missing, `signal_dB`, `sample_rate` and `nfft` are still stored, and the PSD does not use `ae_pipeline/spectral.py` (short records are not zero-padded); R6 the unused `THRESHOLD` constant and `ds` argument still exist and `PEAK_PROMINENCE` is hard-coded; R7 conversions are inline instead of using `ae_pipeline/units.py`; R8 the shared modules are not declared as dependencies)
- **Module:** `ae_pipeline/data/task_characterize_hits.py` (`task_characterize_hits`)

## Summary

For each dataset, collect all hits in one table with their Vallen hit features, their waveform in µV, the Welch power spectral density (PSD) of their waveform, and the prominent PSD peaks. Downstream tasks (waterfall plots 0004, hit plots 0006, clustering 0007) read this table only; none of them opens the tradb.

## Inputs

- `Dataset.primary_file` (`*.pridb`): hits.
- `Dataset.transient_file` (`*.tradb`): transient waveform and pretrigger per hit.
- `Dataset.metadata_file` (0002): sample rate.

## Outputs

- `Dataset.hits_file` (`<name>.hits.parquet`), brotli-compressed.

## Parameters

| Name              | Value | Meaning                                        |
| ----------------- | ----- | ---------------------------------------------- |
| `PEAK_PROMINENCE` | 0.2   | minimum prominence relative to the PSD maximum |

The spectral settings (segment length, hop, window) are those of 0009.

## Requirements

1. One task per dataset with id `<name>`.

2. The table has one row per hit in the pridb that has a transient record, indexed by `trai` (transient recording index, dtype `uint32`). Hits without a transient record (no `trai`) are skipped. The row order is pridb order.

3. Columns copied from the pridb hits. `amplitude` is converted from V to µV with `volts_to_microvolts` (0008 R1):

   | Column      | dtype   | Unit                      |
   | ----------- | ------- | ------------------------- |
   | `time`      | float64 | s since acquisition start |
   | `channel`   | uint8   | –                         |
   | `amplitude` | float32 | µV                        |
   | `duration`  | float32 | s                         |
   | `rise_time` | float32 | s                         |
   | `counts`    | uint32  | –                         |

4. For every hit, the waveform with the hit's `trai` is read from the tradb and converted from V to µV with `volts_to_microvolts`. The following columns are derived from it:

   | Column       | dtype           | Content                                                                                                           |
   | ------------ | --------------- | ----------------------------------------------------------------------------------------------------------------- |
   | `pretrigger` | uint32          | number of samples in the transient record before the hit start (threshold crossing)                               |
   | `signal`     | list of float32 | waveform in µV, the whole transient record including the pretrigger                                               |
   | `psd`        | list of float32 | `welch_psd(signal, sample_rate)` (0009 R2) in µV²/Hz, at the frequencies `psd_frequencies(sample_rate)` (0009 R1) |
   | `peaks`      | list of uint16  | indices into `psd` of the peaks of `psd / max(psd)` with prominence ≥ `PEAK_PROMINENCE`, ascending                |

   `pretrigger` is the pretrigger of the tradb record (Vallen field `Pretrigger`; `vallenae` returns it as the column `pretrigger` of `TraDatabase.read`; `read_wave` does not return it).

   Floating point columns follow `docs/conventions.md` (Units): float32, except `time` (float64). For `signal` this is lossless in practice for the 16-bit ADC samples. The PSD and peaks are computed in float64 (0009 R2) before the cast.

   `sample_rate` is the dataset's sample rate (0002 R5); it is not stored per hit. Records shorter than a segment are zero-padded for the PSD by `welch_psd` (0009 R2); `signal` keeps the original record length.

5. The file can be read back with `pd.read_parquet(..., dtype_backend="pyarrow")`. Consumers convert the list columns with `np.array(...)`.

6. The module defines no unused parameters: the task takes only `primary_file`, `transient_file`, `metadata_file`, the shared module dependencies (R8) and `produces` as arguments, and the only module-level parameter is `PEAK_PROMINENCE`.

7. All data is stored linear in µV (µV²/Hz for `psd`); no level in dB(AE) is stored (`docs/conventions.md`, Units). All conversions use the functions of `ae_pipeline/units.py` (0008).

8. The task declares `ae_pipeline/units.py` and `ae_pipeline/spectral.py` as dependencies (`docs/conventions.md`, Tasks).

### Malformed datasets

9. A hit of the pridb has a `trai` for which the tradb has no record. The dataset is malformed (`docs/conventions.md`, Tasks): the task raises a `ValueError` naming the dataset and listing the missing `trai`s (or their count and the first few), and writes no output. Hits without any `trai` are not affected; they are skipped (R2).

## Open questions

None.
