# Architecture

ae-pipeline processes acoustic emission (AE) measurements recorded with Vallen AE systems. It is a [pytask](https://pytask-dev.readthedocs.io/) project: every processing step is a task with declared dependencies and products, and pytask rebuilds only what is out of date. Decisions behind the architecture are recorded in `docs/adr/`.

## Inputs

A dataset is a pair of Vallen files with the same stem in `ae_pipeline/data/`:

- `<name>.pridb`: primary data (hits with features such as amplitude, duration, rise time and counts; markers/labels; channel and global info).
- `<name>.tradb`: transient recordings (waveforms per hit, indexed by `trai`, and continuous waveforms).

Both are SQLite databases read through `vallenae.io`. `ae_pipeline/task_config.py` discovers all datasets at import time (`DATASETS`) and derives every per-dataset path from the `Dataset` model, so tasks never build paths by hand.

## Stages

Tasks are grouped by stage into subpackages. Each stage consumes the products of the previous ones:

1. **Data (`ae_pipeline/data/`):** extract derived data from the raw files.
   - `<name>.metadata.toml`: channels, clock and sample rates, record length, and marker labels (label → time in s).
   - `<name>.hits.parquet`: one row per hit (indexed by `trai`) with the Vallen hit features plus the dB signal, Welch PSD and PSD peak indices.
2. **Classify (`ae_pipeline/classify/`):** group hits by their features, e.g. BIRCH clustering on PSD peaks (work in progress).
3. **Plots (`ae_pipeline/plots/`):** figures under `ae_pipeline/plots/<name>/`, e.g. spectrograms (waterfall) and their time derivative (edge filter) of the continuous waveforms, overall and per marker-label interval, and optional per-hit figures.

```
pridb + tradb ──┬─> metadata.toml ──> waterfall / edge filter plots (label lines, per-interval plots)
                └─> hits.parquet ───┬─> hit plots
                                    └─> classify
tradb (continuous waveforms) ───────> waterfall / edge filter plots
```

## Configuration

Global settings live in `ae_pipeline/task_config.py`: directories, feature flags (e.g. `EACH_HIT` for the slow per-hit plots), the `Dataset` model and matplotlib defaults. Processing parameters specific to one step (thresholds, FFT segment lengths) are module-level constants in the task module that uses them.
