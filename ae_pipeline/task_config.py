from functools import cached_property
from pathlib import Path
from typing import Self

import matplotlib as mpl
import numpy as np
from pydantic import BaseModel, computed_field, model_validator
from pytask import DataCatalog

ROOT_DIR = Path(__file__).parent

AA_DATA_DIR = ROOT_DIR / "aa_data"
DATA_DIR = ROOT_DIR / "data"
WAVEFORMS_DIR = ROOT_DIR / "waveforms"


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
    def data_file(self) -> Path:
        return DATA_DIR / self.primary_file.with_suffix(".parquet").relative_to(AA_DATA_DIR)

    @computed_field
    @cached_property
    def waveforms_dir(self) -> Path:
        return WAVEFORMS_DIR / self.name

    @model_validator(mode="after")
    def validate_src_files_exist(self) -> Self:
        if not self.primary_file.exists():
            raise ValueError("The given primary file does not exist.")
        if not self.transient_file.exists():
            raise ValueError("The corresponding transient file does not exist.")
        return self


class Waveform(BaseModel):
    dataset: Dataset
    time: int

    @computed_field
    @cached_property
    def name(self) -> str:
        return f"{self.dataset.name}/{self.time}"

    @computed_field
    @cached_property
    def dir(self) -> Path:
        return self.dataset.waveforms_dir / str(self.time)

    @computed_field
    @cached_property
    def signal_file(self) -> Path:
        return self.dir / "signal.parquet"

    @computed_field
    @cached_property
    def fft_file(self) -> Path:
        return self.dir / "fft.parquet"


CATALOG = DataCatalog(name="ae-pipeline")


def mm_to_inch(v):
    return np.asarray(v) / 25.4


DEFAULT_FIGSIZE = mm_to_inch([160, 120])
mpl.rcParams.update(
    {
        "figure.constrained_layout.use": True,
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
    }
)


def image_produces(base_path: Path, formats=["png", "pdf"]) -> list[Path]:
    return [base_path.with_suffix(f".{f}") for f in formats]
