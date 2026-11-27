# CLAUDE.md

Data analysis pipeline for acoustic emission (AE) measurements recorded with Vallen AE systems, built on [pytask](https://pytask-dev.readthedocs.io/). Work in progress.

Developer docs live in `docs/`: `architecture.md` (architecture and the decisions behind it), `conventions.md` and feature specs in `docs/specs/`. Read the relevant ones before larger changes. For end-to-end work, the user can run `/implement` (loop of the `coder` → `tester` → `reviewer` agents) or `/review-changes`.

## Environment and commands

- The toolchain comes from `devenv` (`devenv.nix`): Python 3.14, uv, just, treefmt. Run commands inside `devenv shell`. The venv lives in `.devenv/state/venv`.
- `just build [key]` runs `uv run pytask build -k "<key>"`. Filter by task or dataset id, e.g. `just build waterfall` or `just build 2026-11-26-walzen1`.
- `just clean` force-removes everything pytask produced. It asks for confirmation, so don't run it without the user's OK.
- Dependencies are managed with uv (`pyproject.toml`, `uv.lock`). Add packages with `uv add`, not pip.
- Formatting and linting: `treefmt` (ruff, ruff-format, nixfmt, taplo, yamlfmt, mdformat, just). It also runs as a pre-commit hook. Ruff settings: line length 120, rules E/F/UP/B/SIM/I, no relative imports (`ban-relative-imports = "all"`).
- Type checking: `ty` (configured in `pyproject.toml`).
- Tests (pytest) live in `tests/`; the first ones come with spec 0008 (`ae_pipeline/units.py`). To check a task change, run the affected tasks with `just build <key>` and look at the outputs.
- Version control: the repo is colocated with Jujutsu (`.jj/`). Prefer `jj` (`jj status`, `jj diff`, `jj describe`, `jj new`) over git for local work.

## Layout

```
ae_pipeline/
  task_config.py            # paths, flags, Dataset model, DATASETS, PLOT_FORMATS, matplotlib rcParams (LaTeX), spec 0010
  units.py                  # unit conversions (V -> µV, µV -> dB(AE)), spec 0008
  spectral.py               # spectral settings (NPERSEG, HOP, WINDOW), Welch PSD, STFT, spec 0009
  metadata.py               # Metadata model, load_metadata, label_intervals, spec 0002
  data/                     # raw input (*.pridb/*.tradb, gitignored) and derived data
    task_extract_metadata.py  -> <name>.metadata.toml (channels with thresholds in µV, sample rate, marker labels)
    task_characterize_hits.py -> <name>.hits.parquet (per-hit features, µV waveform, Welch PSD, PSD peaks)
  classify/
    task_birch_cluster.py     # WIP: clustering of hits by PSD peaks
  plots/                    # output dir PLOTS_DIR/<dataset>/... (gitignored; formats from PLOT_FORMATS)
    task_plot_waterfall.py    # per-hit STFT spectrograms binned per channel row, full run + one per label interval (DirectoryNode)
    task_plot_hits.py         # one figure per hit; only runs when EACH_HIT=True
```

pytask collects `task_*.py` under `ae_pipeline/`. Paths starting with `.` or `_` are ignored (e.g. `data/_trash/`).

## Data model

- A dataset is a `*.pridb` (primary/hit data) plus a `*.tradb` (transient waveforms) with the same stem in `ae_pipeline/data/`. Both are SQLite and are read with `vallenae.io.PriDatabase` / `TraDatabase`.
- `task_config.Dataset` derives all per-dataset paths (`transient_file`, `hits_file`, `metadata_file`) and validates that both source files exist. `DATASETS` is built by globbing `DATA_DIR` at import time.
- Hits are indexed by `trai` (transient recording index). Parquet is written with brotli compression and read back with `dtype_backend="pyarrow"`.
- All stored data is linear in µV (µV²/Hz for PSDs); levels in dB(AE) are never stored, only computed for display. dB always means dB(AE) re 1 µV: `20 * log10` for amplitudes, `10 * log10` for power quantities. Convert only through `ae_pipeline/units.py` (`volts_to_microvolts`, `amplitude_to_dB`, `dB_to_amplitude`, `power_to_dB`), never inline. See `docs/conventions.md`.
- Marker labels in the metadata (Vallen set_type 4, without the TimeZone marker) map label to time in seconds. Read the metadata only via `ae_pipeline/metadata.py`; label intervals (skipping "Suspend" labels and too short intervals) come from `label_intervals`.
- The sample rate is one per dataset and stored only in the metadata.

## Writing tasks

Follow the pattern used in every task module:

```python
for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_something(
        hits_file=ds.hits_file,        # dependencies as default args (binds loop vars)
        ds=ds,
        spectral_module=Path(ae_pipeline.spectral.__file__),  # shared modules are dependencies too
        produces=image_produces(PLOTS_DIR / ds.name / "something"),
    ):
        ...
```

- Declare every input as a dependency argument and every output via `produces`, so pytask can track them. For a variable number of outputs, use `Annotated[Path, pytask.DirectoryNode(...), pytask.Product]` (see `task_plot_hits.py`).
- Do not implement generator tasks as they exhibit sometimes strange behavior. For a number of outputs that depends on upstream data, write them all in one task with a `DirectoryNode` product.
- pytask does not track imported modules: declare the shared modules a task uses (`units.py`, `spectral.py`, `metadata.py`) as dependencies.
- Malformed data raises `ValueError` naming the dataset; warnings name the dataset (and channel). Tasks with a `DirectoryNode` product delete old files in the directory before writing. See `docs/conventions.md`.
- Feature flags (`EACH_HIT`) live in `task_config.py`. Gate optional tasks with `pytask.mark.skipif`.
- Close figures after saving (`plt.close(fig)`). Global matplotlib defaults (figure size, dpi, ticks, fonts, LaTeX with siunitx) are set in `task_config.py`; only the figure size may be overridden. Save via `image_produces` (all `PLOT_FORMATS`).
- Axis labels follow "Quantity in unit" with siunitx units, e.g. `r"Time $t$ in \unit{\second}"`, `r"Frequency in \unit{\kilo\hertz}"`; levels in `\unit{\dBAE}` (dB with subscript AE). Annotations are red.

## Gotchas

- Raw data files are large and gitignored. Never commit `*.pridb`, `*.tradb`, or generated outputs. `pytask.lock` is tracked.
- Full builds (characterizing hundreds of thousands of hits, one PNG per hit) are slow. Use `just build <key>` to narrow the run.
