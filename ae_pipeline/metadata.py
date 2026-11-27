"""Model of the metadata document (spec 0002 R11–R12) and the label intervals derived from it."""

import itertools
import tomllib
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict


class General(BaseModel):
    """Acquisition settings of a dataset."""

    model_config = ConfigDict(extra="forbid")

    clock_rate: int
    """pridb time base in Hz."""

    sample_rate: int
    """Sample rate of all tradb records in Hz."""


class Channel(BaseModel):
    """Per-channel data of a dataset."""

    model_config = ConfigDict(extra="forbid")

    threshold: float
    """Detection threshold in µV."""


class Metadata(BaseModel):
    """The metadata TOML document of a dataset (0002 R2)."""

    model_config = ConfigDict(extra="forbid")

    general: General
    channels: dict[int, Channel]
    """Channel number -> channel data, in pridb order."""

    labels: dict[str, float]
    """Marker text -> marker time in s, in ascending time."""


def load_metadata(path: Path) -> Metadata:
    """Read and validate a ``<name>.metadata.toml`` file."""
    return Metadata.model_validate(tomllib.loads(Path(path).read_text()))


class LabelInterval(NamedTuple):
    """Time interval between a marker label and the next one, in s."""

    label: str
    start: float
    end: float


def label_intervals(metadata: Metadata, min_length: float) -> list[LabelInterval]:
    """Intervals between consecutive labels that are at least ``min_length`` s long and not ``Suspend`` labels.

    The last label starts no interval.
    """
    return [
        LabelInterval(label, start, end)
        for (label, start), (_, end) in itertools.pairwise(metadata.labels.items())
        if end - start >= min_length and "Suspend" not in label
    ]
