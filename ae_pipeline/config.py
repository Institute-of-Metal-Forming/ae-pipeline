from functools import cached_property
from pathlib import Path
from typing import Self

from pydantic import BaseModel, computed_field, model_validator

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


DATASETS = [Dataset(primary_file=f) for f in AA_DATA_DIR.glob("*.pridb")]
