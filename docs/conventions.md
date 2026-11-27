# Conventions

Coding conventions for ae-pipeline. Rules enforced by tooling are configured in `pyproject.toml` (ruff) and `devenv.nix` (treefmt); this file records them together with the rules no tool enforces.

## Package layout

- All pipeline code lives in the `ae_pipeline` package, with one subpackage per stage (`data`, `classify`, `plots`; see `docs/architecture.md`).
- Task modules are named `task_<verb>_<object>.py` and contain the tasks of one step; pytask collects only `task_*.py` files.
- Shared configuration (paths, flags, `Dataset`, matplotlib defaults) goes in `ae_pipeline/task_config.py`. Step-specific parameters are upper-case module-level constants in the task module.
- Private helpers within a task module start with `_`. Files and directories starting with `.` or `_` are ignored by pytask.
- Products are written next to their stage: derived data to `ae_pipeline/data/` (paths from `Dataset`), figures to `ae_pipeline/plots/<dataset>/`. Raw data and products are gitignored.

## Tasks

- Create one task per dataset by looping over `DATASETS` and using `@pytask.task(id=ds.name)`.
- Declare every file that is read as a dependency argument and every file that is written via `produces` (a `DirectoryNode` product for a variable number of files). Pass loop variables as default arguments so each task binds its own values.
- Do not add new generator tasks (`is_generator=True`).
- Gate optional or slow tasks with a flag from `task_config.py` and `pytask.mark.skipif`.
- Never write into the raw `*.pridb` / `*.tradb` files.

## Units and signal processing

- Waveforms are converted from V to µV right after reading (`signal *= 1e6`).
- Levels in dB use `10 * np.log10(...)` for power quantities (PSD, spectrogram).
- Frequencies are plotted in kHz and times in s.

## Plots

- Use the global matplotlib defaults from `task_config.py`; override per figure only when needed.
- Axis labels follow "Quantity in unit", e.g. "Time t in s", "Frequency in kHz".
- Close every figure after saving (`plt.close(fig)`).

## Tests

- There is no test suite yet. Changes are verified by building the affected tasks on a real dataset (`uv run pytask build -k <key>`) and inspecting the products.
- Unit tests go in `tests/` (pytest, not collected by pytask), named `test_<module>.py`. They test helper and processing functions with small synthetic inputs (e.g. a sine with known frequency) created in `tmp_path` or in memory, never with the real data files.

## Code style

- Absolute imports only, e.g. `from ae_pipeline.task_config import ...`. Relative imports are banned (ruff `flake8-tidy-imports`).
- Line length 120. Ruff rule sets: E, F, UP, B, SIM, I.
- Public APIs are fully typed.

## Dependencies

- Add dependencies only via `uv add` / `uv add --dev`; never edit `uv.lock` by hand.
- Preferred version constraint is the compatible release operator: `~=1.1` or `~=0.1.1`.

## Commits

- Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) standard.
- Currently there are no scopes allowed.
