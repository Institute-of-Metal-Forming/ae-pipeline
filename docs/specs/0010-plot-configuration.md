# 0010 Plot configuration

- **Status:** partially implemented (not yet implemented: R1 there is no `PLOT_FORMATS`, `image_produces` defaults to `["png", "pdf"]` as a mutable default argument and no task uses it; R3–R5 LaTeX is not used; R6 the TeX toolchain is not part of the devenv)
- **Module:** `ae_pipeline/task_config.py` (`PLOT_FORMATS`, `image_produces`, matplotlib defaults), `devenv.nix`

## Summary

Shared configuration of all figures: output formats, matplotlib defaults and LaTeX typesetting of all text with `siunitx` for units. Plot tasks only set what is specific to their figure.

## Inputs

None.

## Outputs

None.

## Parameters

| Name           | Value     | Meaning                                       |
| -------------- | --------- | --------------------------------------------- |
| `PLOT_FORMATS` | `["png"]` | file formats every figure is saved in (R1–R2) |

## Requirements

### Output formats

1. `task_config.py` defines `PLOT_FORMATS: list[str]`, default `["png"]`. Several formats at once are allowed, e.g. `["png", "pdf"]`. It is the only place where output formats are chosen.

2. `image_produces(base_path: Path) -> list[Path]` returns one path per entry of `PLOT_FORMATS`, `base_path.with_name(f"{base_path.name}.{fmt}")`, in that order. It appends the suffix instead of using `with_suffix`, because base names derived from labels can contain dots (e.g. `v1.5`). Every plot task declares its products with it (a `DirectoryNode` product uses a pattern that matches all formats, e.g. `*`) and saves the figure once per path. Specs name figures by their base path, e.g. `plots/<name>/waterfall`.

### Matplotlib defaults

3. All text is typeset with LaTeX: `text.usetex = True` and a preamble that loads `siunitx` with `per-mode = symbol` (units like `\unit{\kilo\hertz}`, `\unit{\micro\volt\squared\per\hertz}` render as kHz and µV²/Hz).

4. The preamble declares the unit `\dBAE`, rendered as dB with subscript AE (dB<sub>AE</sub>), using a siunitx v3 qualifier: `\DeclareSIUnit\dBAE{\decibel\of{AE}}` with `qualifier-mode = subscript` (the v3 default). Levels and level densities are written `\unit{\dBAE}` and `\unit{\dBAE\per\hertz}`.

5. Axis and colorbar labels follow "Quantity in unit" with the unit typeset by `siunitx`, e.g. `r"Frequency in \unit{\kilo\hertz}"`, `r"Time $t$ in \unit{\second}"`, `r"Power Spectral Density in \unit{\dBAE\per\hertz}"`. Other text (annotations, label texts from markers) is escaped for LaTeX where it can contain special characters (`# $ % & _ { } ~ ^ \`).

6. The TeX toolchain needed by R3–R4 (a LaTeX engine, `siunitx`, `type1cm`, `dvipng` for PNG output and the fonts) is provided by `devenv.nix`, so plots render inside `devenv shell` without a system TeX installation.

7. The global figure size, dpi, line widths, tick direction and font size stay as they are. Plot tasks do not override any global default, with the single exception of the figure size (`docs/conventions.md`, Plots).

## Open questions

None.
