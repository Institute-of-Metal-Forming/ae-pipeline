# CLAUDE.md

Data analysis pipeline for acoustic emission (AE) measurements recorded with Vallen AE systems, built on [pytask](https://pytask-dev.readthedocs.io/). Work in progress.

Developer docs live in `docs/`: `architecture.md`, `conventions.md`, ADRs in `docs/adr/` and feature specs in `docs/specs/`. Read the relevant ones before larger changes. For end-to-end work, the user can run `/implement` (loop of the `coder` → `tester` → `reviewer` agents) or `/review-changes`.

## Environment and commands

- The toolchain comes from `devenv` (`devenv.nix`): Python 3.14, uv, just, treefmt. Run commands inside `devenv shell`. The venv lives in `.devenv/state/venv`.
- `just build [key]` runs `uv run pytask build -k "<key>"`. Filter by task or dataset id, e.g. `just build waterfall` or `just build 2026-10-14-sack-01`.
- `just clean` force-removes everything pytask produced. It asks for confirmation, so don't run it without the user's OK.
- Dependencies are managed with uv (`pyproject.toml`, `uv.lock`). Add packages with `uv add`, not pip.
- Formatting and linting: `treefmt` (ruff, ruff-format, nixfmt, taplo, yamlfmt, mdformat, just). It also runs as a pre-commit hook. Ruff settings: line length 120, rules E/F/UP/B/SIM/I, no relative imports (`ban-relative-imports = "all"`).
- Type checking: `ty` (configured in `pyproject.toml`).
- There is no test suite yet. To check a change, run the affected tasks with `just build <key>` and look at the outputs.
- Version control: the repo is colocated with Jujutsu (`.jj/`). Prefer `jj` (`jj status`, `jj diff`, `jj describe`, `jj new`) over git for local work.

## Layout

```
ae_pipeline/
  task_config.py            # paths, flags, Dataset model, DATASETS, matplotlib rcParams
  data/                     # raw input (*.pridb/*.tradb, gitignored) and derived data
    task_extract_metadata.py  -> <name>.metadata.toml (channels, rates, record length, marker labels)
    task_characterize_hits.py -> <name>.hits.parquet (per-hit features, dB signal, Welch PSD, PSD peaks)
  classify/
    task_birch_cluster.py     # WIP: clustering of hits by PSD peaks
  plots/                    # output dir PLOTS_DIR/<dataset>/... (gitignored *.png/*.pdf)
    task_plot_waterfall.py    # STFT spectrogram per channel, full run + one per marker label interval
    task_plot_edge_filter.py  # time derivative (gaussian_filter1d, order=1) of the spectrogram
    task_plot_hits.py         # one figure per hit; only runs when EACH_HIT=True
```

pytask collects `task_*.py` under `ae_pipeline/`. Paths starting with `.` or `_` are ignored (e.g. `data/_trash/`).

## Data model

- A dataset is a `*.pridb` (primary/hit data) plus a `*.tradb` (transient waveforms) with the same stem in `ae_pipeline/data/`. Both are SQLite and are read with `vallenae.io.PriDatabase` / `TraDatabase`.
- `task_config.Dataset` derives all per-dataset paths (`transient_file`, `hits_file`, `metadata_file`) and validates that both source files exist. `DATASETS` is built by globbing `DATA_DIR` at import time.
- Hits are indexed by `trai` (transient recording index). Parquet is written with brotli compression and read back with `dtype_backend="pyarrow"`.
- Signals are scaled from V to µV (`*= 1e6`). dB values are computed as `10 * np.log10(...)`.
- Marker labels in the metadata (Vallen set_type 4, without the TimeZone marker) map label to time in seconds. They drive the per-interval plots. Labels containing "Suspend" and intervals that are too short are skipped.

## Writing tasks

Follow the pattern used in every task module:

```python
for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_something(
        hits_file=ds.hits_file,        # dependencies as default args (binds loop vars)
        ds=ds,
        produces=PLOTS_DIR / ds.name / "something.png",
    ):
        ...
```

- Declare every input as a dependency argument and every output via `produces`, so pytask can track them. For a variable number of outputs, use `Annotated[Path, pytask.DirectoryNode(...), pytask.Product]` (see `task_plot_hits.py`).
- Tasks that depend on the content of an upstream product (e.g. the marker labels) use `@pytask.task(is_generator=True)` and define their subtasks inside. A generator must yield at least one task, which is why there are the `*_dummy` fallback tasks.
- Do not implement new generator tasks as they exhibit sometimes strange behavior.
- Feature flags (`EACH_HIT`, `DEBUG`) live in `task_config.py`. Gate optional tasks with `pytask.mark.skipif`.
- Close figures after saving (`plt.close(fig)`). Global matplotlib defaults (figure size in mm via `mm_to_inch`, dpi, inward ticks, font size) are set in `task_config.py`. Override them per figure only when needed.
- Axis labels follow the pattern "Quantity in unit", e.g. "Time t in s" or "Frequency in kHz".

## Gotchas

- Raw data files are large and gitignored. Never commit `*.pridb`, `*.tradb`, or generated outputs. `pytask.lock` is tracked.
- Full builds (spectrograms over continuous waveforms, one PNG per hit) are slow. Use `just build <key>` to narrow the run.
- `task_plot_waterfall.py` and `task_plot_edge_filter.py` share most of their code (label annotation, figure layout). Keep them in sync when changing one, or factor out the shared parts.
