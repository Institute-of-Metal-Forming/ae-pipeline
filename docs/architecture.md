# Architecture

ae-pipeline processes acoustic emission (AE) measurements recorded with Vallen AE systems. It is a [pytask](https://pytask-dev.readthedocs.io/) project: every processing step is a task with declared dependencies and products, and pytask rebuilds only what is out of date. Architectural decisions are recorded in this file, together with their rationale.

## Inputs

A dataset is a pair of Vallen files with the same stem in `ae_pipeline/data/`:

- `<name>.pridb`: primary data (hits with features such as amplitude, duration, rise time and counts; markers/labels; channel and global info).
- `<name>.tradb`: transient recordings (waveforms per hit, indexed by `trai`).

Both are SQLite databases read through `vallenae.io`. `ae_pipeline/task_config.py` discovers all datasets at import time (`DATASETS`) and derives every per-dataset path from the `Dataset` model, so tasks never build paths by hand.

## Stages

Tasks are grouped by stage into subpackages. Each stage consumes the products of the previous ones:

1. **Data (`ae_pipeline/data/`):** extract derived data from the raw files.
   - `<name>.metadata.toml`: channels with their detection thresholds, clock and sample rates, and marker labels (label → time in s).
   - `<name>.hits.parquet`: one row per hit (indexed by `trai`) with the Vallen hit features plus the µV waveform, Welch PSD and PSD peak indices.
2. **Classify (`ae_pipeline/classify/`):** group hits by their features, e.g. BIRCH clustering on PSD peaks (work in progress).
3. **Plots (`ae_pipeline/plots/`):** figures under `ae_pipeline/plots/<name>/`, e.g. waterfall plots of the per-hit STFT spectrograms, overall and per marker-label interval, and optional per-hit figures.

```
product          <- dependencies
metadata.toml    <- pridb, tradb
hits.parquet     <- pridb, tradb, metadata.toml (sample rate)
waterfall plots  <- hits.parquet, metadata.toml (channels, sample rate, labels)
hit plots        <- hits.parquet, metadata.toml (sample rate, thresholds)
classify         <- hits.parquet
```

## Configuration

Global settings live in `ae_pipeline/task_config.py`: directories, feature flags (e.g. `EACH_HIT` for the slow per-hit plots), the `Dataset` model, plot output formats and matplotlib defaults. Settings shared by several steps but not global (spectral settings) live in their library module (`spectral.py`). Processing parameters specific to one step (e.g. the peak prominence, plot ranges) are module-level constants in the task module that uses them. Detection thresholds are data, not parameters: they come from the metadata (spec 0002 R6).

## Decisions

Architectural decisions with their rationale, newest last. Add new decisions here instead of creating separate decision records.

- **pytask as build system.** Every processing step is a task with declared dependencies and products, so only outdated products are rebuilt after changing code or adding data.
- **One hits file per dataset.** All hits of a dataset, including their waveforms in µV and the data derived from them (PSD, peaks), are stored in a single `<name>.hits.parquet` instead of one file per hit. Downstream steps read one table per dataset and never open the tradb.
- **No generator tasks.** Tasks with `is_generator=True` behave unreliably in pytask and need dummy tasks when they generate nothing. Tasks with a data-dependent number of outputs write all of them in one task with a `DirectoryNode` product instead (hit plots 0006, per-interval waterfall plots 0004).
- **Linear storage, central conversions.** Products store linear quantities only (µV, µV²/Hz); dB(AE) levels are computed where they are shown. Storing levels loses the sign of the waveform and doubles the size, and the dB(AE) definition lives in one module (`ae_pipeline/units.py`) instead of being repeated in every task.
- **Shared library modules.** Logic used by several tasks lives in plain modules in `ae_pipeline/` (not collected by pytask): `units.py` (0008), `spectral.py` (0009) and `metadata.py` (0002 R11–R13). This keeps one definition of the dB(AE) conversion, the spectral settings (so the hit PSDs and the waterfall spectrograms stay comparable) and the metadata schema and label intervals. pytask does not track imported modules, so tasks declare these files as dependencies.
- **One sample rate per dataset.** All transient records of a dataset have the same sample rate; a dataset with several is malformed (0002 R10). The sample rate is stored once in the metadata and not per hit, and record lengths in samples are proportional to durations.
- **Central plot configuration.** Output formats (`PLOT_FORMATS`, several at once), LaTeX typesetting with `siunitx` units and all other matplotlib defaults are set in `task_config.py` (0010). Tasks override only the figure size. The TeX toolchain comes from devenv.
