import math
import re
import warnings
from pathlib import Path
from typing import Annotated

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as pds
import pyarrow.parquet as pq
import pytask
from matplotlib.cm import ScalarMappable
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

import ae_pipeline.metadata
import ae_pipeline.spectral
import ae_pipeline.units
from ae_pipeline.metadata import Metadata, label_intervals, load_metadata
from ae_pipeline.spectral import HOP, psd_frequencies, short_time_fft
from ae_pipeline.task_config import DATASETS, PLOTS_DIR, image_produces
from ae_pipeline.units import hz_to_khz, power_to_dB

COLOR_RANGE = (-60.0, 10.0)
"""Color normalization in dB(AE)/Hz."""

ANNOTATION_GAP = 1.0
"""Minimum label interval in s to be annotated in the overall figure."""

INTERVAL_GAP = 2.0
"""Minimum label interval in s to get its own figure."""

FIGURE_WIDTH = 20.0
"""Figure width in inches."""

ROW_HEIGHT = 2.4
"""Figure height per channel in inches."""

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_plot_waterfall(
        hits_file=ds.hits_file,
        metadata_file=ds.metadata_file,
        units_module=Path(ae_pipeline.units.__file__),
        spectral_module=Path(ae_pipeline.spectral.__file__),
        metadata_module=Path(ae_pipeline.metadata.__file__),
        produces=image_produces(PLOTS_DIR / ds.name / "waterfall"),
    ):
        metadata = load_metadata(metadata_file)
        last_hit_end, max_duration = _hit_extent(hits_file)
        # up to the last hit or the last label, whichever is later, so all labels are shown
        end = max(last_hit_end, *metadata.labels.values(), 0.0)

        fig, axs = _plot_waterfall(hits_file, metadata, 0.0, end, max_duration)

        for interval in label_intervals(metadata, ANNOTATION_GAP):
            match = re.fullmatch(r"(?P<time>\d+:\d+)\s(?P<msg>.*)", interval.label)
            text = (
                f"{_latex_escape(match['time'])}\n{_latex_escape(match['msg'])}"
                if match
                else _latex_escape(interval.label)
            )

            for ax in axs:
                ax.axvline(interval.start, color="r", linewidth=1)
                ax.annotate(
                    text,
                    (interval.start, 1),
                    (0.3, -3.3),
                    color="r",
                    ha="left",
                    va="top",
                    xycoords=("data", "axes fraction"),
                    textcoords="offset fontsize",
                )

        for path in produces:
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path)

        plt.close(fig)

    @pytask.task(id=ds.name)
    def task_plot_waterfall_intervals(
        produces: Annotated[
            Path,
            pytask.DirectoryNode(name=ds.name + "/waterfall", root_dir=PLOTS_DIR / ds.name / "waterfall", pattern="*"),
            pytask.Product,
        ],
        hits_file=ds.hits_file,
        metadata_file=ds.metadata_file,
        units_module=Path(ae_pipeline.units.__file__),
        spectral_module=Path(ae_pipeline.spectral.__file__),
        metadata_module=Path(ae_pipeline.metadata.__file__),
        name=ds.name,
    ):
        metadata = load_metadata(metadata_file)
        intervals = label_intervals(metadata, INTERVAL_GAP)

        file_names: dict[str, list[str]] = {}
        for interval in intervals:
            file_names.setdefault(_sanitize_file_name(interval.label), []).append(interval.label)
        clashes = [labels for labels in file_names.values() if len(labels) > 1]
        if clashes:
            raise ValueError(f"Dataset {name}: the labels {clashes} give the same waterfall file name.")

        produces.mkdir(parents=True, exist_ok=True)
        for path in produces.iterdir():
            if path.is_file():
                path.unlink()

        if not intervals:
            warnings.warn(
                f"Dataset {name}: no label interval of at least {INTERVAL_GAP} s, no per-interval waterfall plots.",
                stacklevel=2,
            )
            return

        _, max_duration = _hit_extent(hits_file)
        for interval in intervals:
            fig, _ = _plot_waterfall(hits_file, metadata, interval.start, interval.end, max_duration)
            for path in image_produces(produces / _sanitize_file_name(interval.label)):
                fig.savefig(path)
            plt.close(fig)


def _hit_extent(hits_file: Path) -> tuple[float, float]:
    """End of the last hit of any channel and the longest hit duration, in s."""
    table = pq.read_table(hits_file, columns=["time", "duration"])
    if table.num_rows == 0:
        return 0.0, 0.0
    time = table["time"].to_numpy()
    duration = table["duration"].to_numpy().astype(np.float64)
    return float(np.max(time + duration)), float(np.max(duration))


def _plot_waterfall(
    hits_file: Path, metadata: Metadata, start: float, end: float, max_duration: float
) -> tuple[Figure, list]:
    """Waterfall figure of all channels over the time range [start, end] in s."""
    channels = list(metadata.channels)
    sample_rate = metadata.general.sample_rate
    frequencies = psd_frequencies(sample_rate)
    half_bin = (frequencies[1] - frequencies[0]) / 2
    if end <= start:
        end = start + 1.0

    fig = plt.figure(figsize=(FIGURE_WIDTH, ROW_HEIGHT * max(len(channels), 1)))
    n_bins = round(FIGURE_WIDTH * fig.dpi)

    gs = GridSpec(max(len(channels), 1), 2, figure=fig, width_ratios=[1, 0.01])
    axs = [fig.add_subplot(gs[i, 0]) for i in range(len(channels))]
    cax = fig.add_subplot(gs[:, 1])

    cmap = plt.get_cmap("inferno").reversed()
    cmap = cmap.with_extremes(bad=cmap(0.0), under=cmap(0.0))
    norm = mcolors.Normalize(vmin=COLOR_RANGE[0], vmax=COLOR_RANGE[1])

    psds = _channel_psds(hits_file, channels, sample_rate, start, end, n_bins, max_duration)

    for ax, channel in zip(axs, channels, strict=True):
        if ax is not axs[0]:
            ax.sharex(axs[0])
            ax.sharey(axs[0])
        ax.set_ylabel(r"Frequency in \unit{\kilo\hertz}")
        ax.annotate(
            f"Channel {channel}",
            (0, 1),
            (1, -2),
            color="r",
            xycoords="axes fraction",
            textcoords="offset fontsize",
        )

        # frequency bin i is centered at frequencies[i]
        ax.imshow(
            power_to_dB(psds[channel].T),
            cmap=cmap,
            norm=norm,
            interpolation="none",
            origin="lower",
            aspect="auto",
            extent=(start, end, hz_to_khz(-half_bin), hz_to_khz(frequencies[-1] + half_bin)),
        )
        ax.set_xlim(start, end)
        ax.set_ylim(0.0, hz_to_khz(frequencies[-1]))

    if axs:
        axs[-1].set_xlabel(r"Time $t$ in \unit{\second}")

    fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        label=r"Power Spectral Density in \unit{\dBAE\per\hertz}",
    )

    return fig, axs


def _channel_psds(
    hits_file: Path,
    channels: list[int],
    sample_rate: float,
    start: float,
    end: float,
    n_bins: int,
    max_duration: float,
) -> dict[int, np.ndarray]:
    """Maximum STFT PSD in µV²/Hz per time bin for each channel, each of shape (n_bins, n_frequencies).

    The hits table is read in one streaming pass; row groups whose ``time`` statistics lie outside the plotted range
    are skipped by the filter.
    """
    stft = short_time_fft(sample_rate)
    n_frequencies = len(psd_frequencies(sample_rate))
    psds = {channel: np.zeros((n_bins, n_frequencies)) for channel in channels}
    bin_width = (end - start) / n_bins

    dataset = pds.dataset(hits_file, format="parquet")
    # a hit overlaps the range if time <= end and time + duration >= start; duration <= max_duration
    row_filter = (pc.field("time") <= end) & (pc.field("time") >= start - max_duration)
    columns = ["channel", "time", "duration", "pretrigger", "signal"]
    for batch in dataset.to_batches(columns=columns, filter=row_filter):
        hit_channels = batch.column("channel").to_numpy()
        times = batch.column("time").to_numpy()
        durations = batch.column("duration").to_numpy().astype(np.float64)
        pretriggers = batch.column("pretrigger").to_numpy()
        signal_column = batch.column("signal")
        offsets = signal_column.offsets.to_numpy()
        values = signal_column.values.to_numpy()

        for i in range(batch.num_rows):
            psd = psds.get(int(hit_channels[i]))
            if psd is None:
                continue
            _add_hit(
                psd,
                stft,
                values[offsets[i] : offsets[i + 1]],
                record_start=times[i] - pretriggers[i] / sample_rate,
                hit_start=max(times[i], start),
                hit_end=min(times[i] + durations[i], end),
                start=start,
                bin_width=bin_width,
            )

    return psds


def _add_hit(
    psd: np.ndarray,
    stft,
    signal: np.ndarray,
    record_start: float,
    hit_start: float,
    hit_end: float,
    start: float,
    bin_width: float,
) -> None:
    """Bin the STFT columns of one hit within [hit_start, hit_end] onto the time grid, keeping the maximum per bin."""
    if hit_end <= hit_start:
        return

    hop_time = HOP / stft.fs
    # column k is centered at record_start + k * hop_time and covers one hop around its center
    k_first = max(math.floor((hit_start - record_start) / hop_time - 0.5) + 1, stft.p_min)
    k_last = min(
        math.ceil((hit_end - record_start) / hop_time + 0.5) - 1,
        stft.p_max(max(len(signal), stft.m_num - stft.m_num_mid)) - 1,
    )
    if k_last < k_first:
        return

    columns = stft.spectrogram(signal, p0=k_first, p1=k_last + 1).T
    centers = record_start + np.arange(k_first, k_last + 1) * hop_time
    lower = np.maximum(centers - hop_time / 2, hit_start)
    upper = np.minimum(centers + hop_time / 2, hit_end)
    used = upper > lower
    if not np.any(used):
        return
    columns, lower, upper = columns[used], lower[used], upper[used]

    n_bins = psd.shape[0]
    first_bin = np.clip(np.floor((lower - start) / bin_width).astype(np.int64), 0, n_bins - 1)
    last_bin = np.clip(np.ceil((upper - start) / bin_width).astype(np.int64) - 1, 0, n_bins - 1)
    last_bin = np.maximum(last_bin, first_bin)

    # expand to (column, bin) pairs; the bins are non-decreasing, so equal bins are contiguous
    counts = last_bin - first_bin + 1
    column_index = np.repeat(np.arange(len(columns)), counts)
    bins = np.repeat(first_bin, counts) + np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    unique_bins, group_start = np.unique(bins, return_index=True)
    maxima = np.maximum.reduceat(columns[column_index], group_start, axis=0)
    psd[unique_bins] = np.maximum(psd[unique_bins], maxima)


_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "#": r"\#",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(text: str) -> str:
    """Escape the LaTeX special characters of free text."""
    return "".join(_LATEX_SPECIAL.get(c, c) for c in text)


def _sanitize_file_name(text: str) -> str:
    """File name from free text: remove ``: / \\ * ? " < > |`` and replace whitespace with ``_``."""
    return re.sub(r"\s", "_", re.sub(r'[:/\\*?"<>|]', "", text))
