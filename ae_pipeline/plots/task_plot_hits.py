import math
from pathlib import Path
from typing import Annotated

import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq
import pytask
from matplotlib.figure import Figure

import ae_pipeline.metadata
import ae_pipeline.spectral
import ae_pipeline.units
from ae_pipeline.metadata import load_metadata
from ae_pipeline.spectral import psd_frequencies
from ae_pipeline.task_config import DATASETS, EACH_HIT, PLOTS_DIR, image_produces
from ae_pipeline.units import amplitude_to_dB, hz_to_khz

MAX_POINTS = 10_000
"""Maximum number of points of the level envelope plot."""

for ds in DATASETS:

    @pytask.task(id=ds.name)
    @pytask.mark.skipif(not EACH_HIT, reason="Skipping because EACH_HIT==False")
    def task_plot_hits(
        produces: Annotated[
            Path,
            pytask.DirectoryNode(name=ds.name + "/hits", root_dir=PLOTS_DIR / ds.name / "hits", pattern="*"),
            pytask.Product,
        ],
        hits_file=ds.hits_file,
        metadata_file=ds.metadata_file,
        units_module=Path(ae_pipeline.units.__file__),
        spectral_module=Path(ae_pipeline.spectral.__file__),
        metadata_module=Path(ae_pipeline.metadata.__file__),
    ):
        metadata = load_metadata(metadata_file)
        sample_rate = metadata.general.sample_rate
        thresholds = {channel: c.threshold for channel, c in metadata.channels.items()}

        produces.mkdir(parents=True, exist_ok=True)
        for path in produces.iterdir():
            if path.is_file():
                path.unlink()

        columns = ["channel", "duration", "pretrigger", "signal", "psd", "peaks", "trai"]
        for batch in pq.ParquetFile(hits_file).iter_batches(batch_size=1_000, columns=columns):
            for hit in batch.to_pylist():
                fig = _plot_hit(
                    signal=np.array(hit["signal"]),
                    pretrigger=hit["pretrigger"],
                    duration=hit["duration"],
                    threshold=thresholds[hit["channel"]],
                    psd=np.array(hit["psd"]),
                    peaks=np.array(hit["peaks"], dtype=np.intp),
                    sample_rate=sample_rate,
                )
                for path in image_produces(produces / f"hit_{hit['trai']}"):
                    fig.savefig(path)
                plt.close(fig)


def _level_envelope(signal_dB: np.ndarray, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    """Block maximum of the level with at most MAX_POINTS blocks; times in s of the first sample of each block."""
    n = len(signal_dB)
    window = max(math.ceil(n / MAX_POINTS), 1)
    block_starts = np.arange(0, n, window)
    return block_starts / sample_rate, np.maximum.reduceat(signal_dB, block_starts)


def _plot_hit(
    signal: np.ndarray,
    pretrigger: int,
    duration: float,
    threshold: float,
    psd: np.ndarray,
    peaks: np.ndarray,
    sample_rate: float,
) -> Figure:
    """Figure of one hit: level envelope (top) and PSD with peaks (bottom)."""
    fig, axs = plt.subplots(2)

    times, level = _level_envelope(amplitude_to_dB(signal), sample_rate)
    hit_start = pretrigger / sample_rate

    axs[0].plot(times, level)
    axs[0].axvline(hit_start, color="r", linewidth=1)
    axs[0].axvline(hit_start + duration, color="r", linewidth=1)
    axs[0].axhline(amplitude_to_dB(threshold), color="r", linestyle="--", linewidth=1)
    axs[0].set_ylim(0, 100)
    axs[0].margins(x=0)
    axs[0].set_xlabel(r"Time $t$ in \unit{\second}")
    axs[0].set_ylabel(r"Intensity in \unit{\dBAE}")

    frequencies_kHz = hz_to_khz(psd_frequencies(sample_rate))
    axs[1].plot(frequencies_kHz, psd)
    axs[1].scatter(frequencies_kHz[peaks], psd[peaks], marker="+", c="r", lw=0.5)
    axs[1].set_ylim(0, None)
    axs[1].margins(x=0)
    axs[1].set_xlabel(r"Frequency in \unit{\kilo\hertz}")
    axs[1].set_ylabel(r"Power Spectral Density in \unit{\micro\volt\squared\per\hertz}")

    for p in peaks:
        axs[1].annotate(
            f"{frequencies_kHz[p]:.0f}",
            (frequencies_kHz[p], psd[p]),
            (0.3, 0.3),
            color="r",
            ha="left",
            va="baseline",
            xycoords="data",
            textcoords="offset fontsize",
            fontsize="5",
        )

    return fig
