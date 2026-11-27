import math
import warnings
from pathlib import Path

import pytask
import tomli_w
import vallenae

import ae_pipeline.metadata
import ae_pipeline.units
from ae_pipeline.metadata import Channel, General, Metadata
from ae_pipeline.task_config import DATASETS
from ae_pipeline.units import dB_to_amplitude

DEFAULT_THRESHOLD = 32.0
"""Detection threshold in dB(AE) of channels without hits."""

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_extract_metadata(
        primary_file=ds.primary_file,
        transient_file=ds.transient_file,
        units_module=Path(ae_pipeline.units.__file__),
        metadata_module=Path(ae_pipeline.metadata.__file__),
        produces=ds.metadata_file,
    ):
        name = primary_file.stem

        pridb: vallenae.io.PriDatabase
        with vallenae.io.PriDatabase(str(primary_file)) as pridb:
            channels = sorted(pridb.channel())
            globalinfo = pridb.globalinfo()
            markers = pridb.read_markers(show_progress=False)
            # view_ae_data returns Thr in µV
            channel_thresholds = [
                (int(channel), float(threshold))
                for channel, threshold in pridb.connection()
                .execute("SELECT DISTINCT Chan, Thr FROM view_ae_data WHERE SetType = 2")
                .fetchall()
            ]

        tradb: vallenae.io.TraDatabase
        with vallenae.io.TraDatabase(str(transient_file)) as tradb:
            sample_rates = sorted(
                int(r[0]) for r in tradb.connection().execute("SELECT DISTINCT SampleRate FROM tr_data").fetchall()
            )

        labels = _labels(name, markers)
        sample_rate = _sample_rate(name, sample_rates)
        thresholds = _thresholds(name, channels, channel_thresholds)

        metadata = Metadata(
            general=General(clock_rate=int(globalinfo["TimeBase"]), sample_rate=sample_rate),
            channels={channel: Channel(threshold=thresholds[channel]) for channel in channels},
            labels=labels,
        )

        produces.write_text(tomli_w.dumps(metadata.model_dump(mode="json")))


def _labels(name: str, markers) -> dict[str, float]:
    """Label markers (set_type 4) without the TimeZone marker, in pridb order: text -> time in s."""
    markers = markers[markers.set_type == 4]
    markers = markers[~markers.data.str.contains("TimeZone:", na=False)]
    texts = [str(text) for text in markers.data]

    duplicates = sorted({text for text in texts if texts.count(text) > 1})
    if duplicates:
        raise ValueError(f"Dataset {name} is malformed: duplicate marker texts {duplicates}.")

    return {text: float(time) for text, time in zip(texts, markers.time, strict=True)}


def _sample_rate(name: str, sample_rates: list[int]) -> int:
    """The single sample rate of all tradb records."""
    if not sample_rates:
        raise ValueError(f"Dataset {name} is malformed: the tradb contains no records, so the sample rate is unknown.")
    if len(sample_rates) > 1:
        raise ValueError(f"Dataset {name} is malformed: the tradb records have several sample rates {sample_rates}.")
    return sample_rates[0]


def _thresholds(name: str, channels: list[int], channel_thresholds: list[tuple[int, float]]) -> dict[int, float]:
    """Detection threshold in µV per channel from the distinct (channel, threshold in µV) pairs of the hits.

    Channels without hits get the default threshold.
    """
    thresholds = {}
    for channel in channels:
        values = sorted({t for c, t in channel_thresholds if c == channel and t is not None and not math.isnan(t)})

        if not values:
            warnings.warn(
                f"Dataset {name}: channel {channel} has no hits, using the default threshold of "
                f"{DEFAULT_THRESHOLD} dB(AE).",
                stacklevel=2,
            )
            thresholds[channel] = float(dB_to_amplitude(DEFAULT_THRESHOLD))
        elif len(values) > 1:
            raise ValueError(
                f"Dataset {name} is malformed: the hits of channel {channel} have several thresholds {values} µV."
            )
        else:
            thresholds[channel] = values[0]

    return thresholds
