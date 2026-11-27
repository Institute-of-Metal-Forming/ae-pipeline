import warnings
from functools import cached_property
from pathlib import Path
from typing import Self

import matplotlib as mpl
import numpy as np
from pydantic import BaseModel, computed_field, model_validator

ROOT_DIR = Path(__file__).parent

DATA_DIR = ROOT_DIR / "data"
PLOTS_DIR = ROOT_DIR / "plots"

EACH_HIT = False

PLOT_FORMATS: list[str] = ["png"]
"""File formats every figure is saved in (spec 0010 R1)."""


class Dataset(BaseModel):
    primary_file: Path

    @computed_field
    @cached_property
    def name(self) -> str:
        return self.primary_file.stem

    @computed_field
    @cached_property
    def transient_file(self) -> Path:
        return self.primary_file.with_suffix(".tradb")

    @computed_field
    @cached_property
    def hits_file(self) -> Path:
        return self.primary_file.with_suffix(".hits.parquet")

    @computed_field
    @cached_property
    def metadata_file(self) -> Path:
        return self.primary_file.with_suffix(".metadata.toml")

    @model_validator(mode="after")
    def validate_src_files_exist(self) -> Self:
        if not self.primary_file.exists():
            raise ValueError(f"The primary file {self.primary_file} does not exist.")
        if not self.transient_file.exists():
            raise ValueError(f"The corresponding transient file {self.transient_file} does not exist.")
        return self


def _discover_datasets(data_dir: Path) -> list[Dataset]:
    """One dataset per ``*.pridb`` with a ``*.tradb`` of the same stem; unpaired files are skipped with a warning."""
    datasets = []
    for primary_file in sorted(data_dir.glob("*.pridb")):
        if not primary_file.with_suffix(".tradb").exists():
            warnings.warn(
                f"Skipping {primary_file}: the corresponding transient file {primary_file.with_suffix('.tradb').name} "
                "does not exist.",
                stacklevel=2,
            )
            continue
        datasets.append(Dataset(primary_file=primary_file))

    for transient_file in sorted(data_dir.glob("*.tradb")):
        if not transient_file.with_suffix(".pridb").exists():
            warnings.warn(
                f"Skipping {transient_file}: the corresponding primary file {transient_file.with_suffix('.pridb').name} "
                "does not exist.",
                stacklevel=2,
            )

    return datasets


DATASETS = _discover_datasets(DATA_DIR)


def mm_to_inch(v):
    return np.asarray(v) / 25.4


DEFAULT_FIGSIZE = mm_to_inch([160, 120])
mpl.rcParams.update(
    {
        "figure.autolayout": True,
        "figure.dpi": 600,
        "figure.figsize": DEFAULT_FIGSIZE,
        "lines.linewidth": 1,
        "patch.linewidth": 1,
        "contour.linewidth": 1,
        "savefig.transparent": True,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "font.size": 8,
        "grid.linewidth": 0.5,
        "text.usetex": True,
        "text.latex.preamble": "\n".join(
            [
                r"\usepackage{siunitx}",
                r"\sisetup{per-mode = symbol, qualifier-mode = subscript}",
                r"\DeclareSIUnit\dBAE{\decibel\of{AE}}",
            ]
        ),
    }
)


def image_produces(base_path: Path) -> list[Path]:
    """One path per format of ``PLOT_FORMATS``, with the format appended to ``base_path`` as suffix."""
    return [base_path.with_name(f"{base_path.name}.{fmt}") for fmt in PLOT_FORMATS]
