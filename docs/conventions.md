# Conventions

Coding conventions for ae-pipeline. Rules enforced by tooling are configured in `pyproject.toml` (ruff) and `devenv.nix` (treefmt); this file records them together with the rules no tool enforces.

## Package layout

- All pipeline code lives in the `ae_pipeline` package, with one subpackage per stage (`data`, `classify`, `plots`; see `docs/architecture.md`).
- Task modules are named `task_<verb>_<object>.py` and contain the tasks of one step; pytask collects only `task_*.py` files.
- The task function name equals the module name, e.g. `task_characterize_hits` in `task_characterize_hits.py`. If a module defines several tasks, the module name is their common prefix and each task appends a suffix, e.g. `task_plot_waterfall` and `task_plot_waterfall_intervals` in `task_plot_waterfall.py`.
- Shared configuration (paths, flags, `Dataset`, plot formats, matplotlib defaults) goes in `ae_pipeline/task_config.py`. Step-specific parameters are upper-case module-level constants in the task module.
- Code shared between tasks lives in library modules directly in `ae_pipeline/` whose names do not start with `task_`: `units.py` (unit conversions, spec 0008), `spectral.py` (spectral settings and functions, 0009), `metadata.py` (metadata model and label intervals, 0002). Use them instead of reimplementing their content in a task.
- Private helpers within a task module start with `_`. Files and directories starting with `.` or `_` are ignored by pytask.
- Products are written next to their stage: derived data to `ae_pipeline/data/` (paths from `Dataset`), figures to `ae_pipeline/plots/<dataset>/`. Raw data and products are gitignored.
- File names derived from free text (e.g. marker labels) are sanitized: remove the characters `: / \ * ? " < > |` and replace whitespace with `_`, e.g. `11:19 ruhe` → `1119_ruhe`. Task ids keep the original text.

## Tasks

- Create one task per dataset by looping over `DATASETS` and using `@pytask.task(id=ds.name)`. Task ids are `<name>` for a per-dataset task and `<name>/<sub>` if a task is created per sub-item of a dataset.
- Declare every file that is read as a dependency argument and every file that is written via `produces` (a `DirectoryNode` product for a variable number of files). Pass loop variables as default arguments so each task binds its own values.
- pytask only tracks the task module itself, not the modules it imports. A task that uses a shared library module (`units.py`, `spectral.py`, `metadata.py`) declares that module's file as a dependency, e.g. `spectral_module=Path(ae_pipeline.spectral.__file__)`, so changes to it rebuild the products.
- Do not use generator tasks (`is_generator=True`). For a number of outputs that depends on upstream data, write all of them in one task with a `DirectoryNode` product. Such a task deletes all existing files in its directory before writing, so files of removed items (e.g. a renamed label) do not remain as stale products.
- Malformed input data (a condition a spec lists as malformed, e.g. duplicate marker texts) makes the task raise a `ValueError` whose message names the dataset and the condition. The task writes no output; tasks of other datasets are not affected. Do not skip or repair malformed data silently.
- Warnings (`warnings.warn`) are for conditions the pipeline can handle but the user should notice, e.g. a channel without hits. The message names the dataset, and the channel where relevant.
- Gate optional or slow tasks with a flag from `task_config.py` and `pytask.mark.skipif`.
- Never write into the raw `*.pridb` / `*.tradb` files.

## Units and signal processing

- All stored data is linear: voltages (waveforms, amplitudes, thresholds) in µV, power quantities in µV² or µV²/Hz. Values read from the Vallen databases (in V) are converted to µV right after reading. Levels in dB(AE) are never stored; they are computed only where they are shown, e.g. in plots.

- All unit conversions go through the central functions in `ae_pipeline/units.py` (spec 0008): `volts_to_microvolts`, `amplitude_to_dB`, `dB_to_amplitude`, `power_to_dB`. Do not write `1e6` factors or `log10` levels inline.
- All unit conversions go through the central functions in `ae_pipeline/units.py` (spec 0008): `volts_to_microvolts`, `amplitude_to_dB`, `dB_to_amplitude`, `power_to_dB`, `hz_to_khz`. Do not write `1e6` or `1e3` factors or `log10` levels inline.

- dB always means dB(AE), the AE domain standard: a level relative to 1 µV. Signals are in µV (see above), so the reference value is 1.

  - Amplitudes (voltages `u`, e.g. waveform samples, hit amplitudes, thresholds): `L = 20 * np.log10(np.abs(u) / 1)` in dB(AE) (`amplitude_to_dB`).
  - Power quantities (`P` in µV², PSD and spectrogram in µV²/Hz): `L = 10 * np.log10(P / 1)` in dB(AE), or dB(AE)/Hz for densities (`power_to_dB`). This gives the same scale as the amplitude formula.
  - In docs and plain text, write the unit as `dB(AE)`, never as plain `dB`. In plot labels it is typeset as dB with subscript AE, `\unit{\dBAE}` (see Plots). In variable names, the suffix `_dB` stands for dB(AE). Stored columns and metadata keys have no `_dB` variants.

- Detection thresholds are per channel and come from the dataset (`channels.<n>.threshold` in the metadata, spec 0002 R6), in µV. Never hard-code a threshold; the only exception is the default of 32 dB(AE) for channels without hits, defined in the metadata extraction. The threshold only governs the detection of a hit and of its end; it is not a lower bound for values within a hit, so data is never clipped to it.

- Frequencies are plotted in kHz and times in s.

- Spectral settings (segment length, hop, window) come from `ae_pipeline/spectral.py` (spec 0009); no task defines its own.

- Stored floating point data is float32, except absolute times (`time` in the hits table), which are float64: at 519 s, float32 resolves only about 61 µs (about 610 samples at 10 MHz). Computations run in float64; values are cast to float32 only when stored. TOML floats (metadata) are always 64-bit and not affected. Integer columns use the smallest unsigned type that holds the full range the source format allows, not just the values of the current data; if that range is unknown, use uint32.

## Plots

- Use the global matplotlib defaults from `task_config.py` (spec 0010). The only default a task may override is the figure size.
- Save every figure with `image_produces(base_path)`, once per format of `PLOT_FORMATS` (default `["png"]`, several at once allowed). Never hard-code a file format.
- All text is typeset with LaTeX. Units are written with `siunitx` (`\unit{...}`, `\qty{...}{...}`), e.g. `\unit{\kilo\hertz}`, `\unit{\micro\volt\squared\per\hertz}`, `\unit{\dBAE\per\hertz}`. Free text from the data (marker labels) is escaped for LaTeX.
- Axis labels follow "Quantity in unit", e.g. `r"Time $t$ in \unit{\second}"`, `r"Frequency in \unit{\kilo\hertz}"`.
- Annotations (marker labels, threshold lines, peaks, channel names) are red.
- Close every figure after saving (`plt.close(fig)`).

## Tests

- The test suite is small (the first tests come with spec 0008). Tasks are verified by building the affected tasks on a real dataset (`uv run pytask build -k <key>`) and inspecting the products.
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
