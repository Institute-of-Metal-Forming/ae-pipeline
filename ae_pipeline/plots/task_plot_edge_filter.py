import itertools
import re
import tomllib
from pathlib import Path
from warnings import warn

import matplotlib.colorizer as mcolorizer
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytask
import vallenae
from matplotlib.gridspec import GridSpec
from scipy.ndimage import gaussian_filter1d
from scipy.signal import ShortTimeFFT

from ae_pipeline.task_config import DATASETS, PLOTS_DIR

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_plot_edge_filter(
        transient_file=ds.transient_file,
        metadata_file=ds.metadata_file,
        produces=[PLOTS_DIR / ds.name / f"edge_filter.{suffix}" for suffix in ["png"]],
    ):
        fig, axs = _plot_edge_filter(transient_file, None, None)

        metadata = tomllib.loads(metadata_file.read_text())
        for (label, time), (_, time2) in itertools.pairwise(metadata["labels"].items()):
            if time2 - time < 1.0:
                continue

            if "Suspend" in label:
                continue

            match = re.fullmatch(r"(?P<time>\d+:\d+)\s(?P<msg>.*)", label)

            if match:
                label = f"{match['time']}\n{match['msg']}"

            for ax in axs:
                ax.axvline(time, color="r", linewidth=1)
                ax.annotate(
                    label,
                    (time, 1),
                    (0.3, -3.3),
                    color="r",
                    ha="left",
                    va="top",
                    xycoords=("data", "axes fraction"),
                    textcoords="offset fontsize",
                )

        for p in produces:
            fig.savefig(p)

        plt.close(fig)

    @pytask.task(id=ds.name, is_generator=True)
    def task_gen_plot_label_edge_filter(
        metadata_file=ds.metadata_file,
        ds=ds,
    ):
        metadata = tomllib.loads(metadata_file.read_text())

        if len(metadata["labels"]) <= 2:
            warn(f"Skipping generation of tasks for {ds.name} since count of labels is 2 or less.", stacklevel=2)

            @pytask.task()
            def plot_label_edge_filter_dummy():
                pass

            return

        for (label1, time1), (_, time2) in itertools.pairwise(metadata["labels"].items()):
            if time2 - time1 < 2.0:
                continue

            if "Suspend" in label1:
                continue

            @pytask.task(id=f"{ds.name}/{label1}")
            def task_plot_label_edge_filter(
                transient_file=ds.transient_file,
                times=(time1, time2),
                produces=[
                    PLOTS_DIR / ds.name / f"edge_filter_{label1.replace(' ', '_')}.{suffix}" for suffix in ["png"]
                ],
            ):
                fig, _ = _plot_edge_filter(transient_file, times[0], times[0] + 8.0)

                for p in produces:
                    fig.savefig(p)

                plt.close(fig)


def _plot_edge_filter(transient_file: Path, start: float | None, end: float | None):
    tradb: vallenae.io.TraDatabase
    with vallenae.io.TraDatabase(str(transient_file)) as tradb:
        channels = tradb.channel()

        fig = plt.figure(figsize=(20.0, 2.4 * len(channels)), layout="constrained")

        gs = GridSpec(len(channels), 2, figure=fig, hspace=0.05, wspace=0.05, width_ratios=[1, 0.01])
        axs = [fig.add_subplot(gs[i, 0]) for i in range(len(channels))]
        cax = fig.add_subplot(gs[:, 1])

        for ax in axs[1:]:
            ax.sharex(axs[0])
            ax.sharey(axs[0])
            ax.set_ylabel("Frequency in kHz")

        axs[-1].set_xlabel("Time t in s")

        norm = mcolors.Normalize(vmin=-1.0, vmax=1.0)
        colorizer = mcolorizer.Colorizer(cmap="RdBu", norm=norm)

        for i, channel in enumerate(channels):
            axs[i].annotate(
                f"Channel {channel}",
                (0, 1),
                (1, -2),
                color="r",
                xycoords="axes fraction",
                textcoords="offset fontsize",
            )

            signal, sample_rate = tradb.read_continuous_wave(
                channel=channel,
                time_start=start,
                time_stop=end,
                time_axis=False,
                show_progress=False,
            )
            signal *= 1e6

            stft = ShortTimeFFT.from_window(
                "hann",
                sample_rate,
                nperseg=2048,
                noverlap=1024,
                scale_to="psd",
            )

            spectro = stft.spectrogram(signal)
            spectro_dB = 10 * np.log(spectro)

            diff_filtered = gaussian_filter1d(
                spectro_dB,
                5,
                axis=1,
                order=1,
            )

            extent = list(stft.extent(len(signal), "tf", False))
            extent = (*extent[:3], extent[3] / 1e3)

            img = axs[i].imshow(
                diff_filtered,
                colorizer=colorizer,
                interpolation="none",
                origin="lower",
                aspect="auto",
                extent=extent,
            )

    fig.colorbar(
        img,
        cax=cax,
        label="Power Spectral Density in dB from 1 (µV)²/Hz",
    )

    return fig, axs
