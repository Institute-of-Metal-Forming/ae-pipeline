import tomllib

import matplotlib.colorizer as mcolorizer
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytask
import vallenae
from matplotlib.transforms import blended_transform_factory
from scipy.signal import ShortTimeFFT

from ae_pipeline.task_config import DATASETS, PLOTS_DIR

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_plot_waterfall(
        transient_file=ds.transient_file,
        metadata_file=ds.metadata_file,
        produces=[PLOTS_DIR / ds.name / f"waterfall.{suffix}" for suffix in ["png"]],
    ):
        metadata = tomllib.loads(metadata_file.read_text())

        tradb: vallenae.io.TraDatabase
        with vallenae.io.TraDatabase(str(transient_file)) as tradb:
            channels = tradb.channel()

            fig, axs = plt.subplots(nrows=len(channels), figsize=(20.0, 2.4 * len(channels)))
            norm = mcolors.Normalize(vmin=-500.0, vmax=0.0)
            colorizer = mcolorizer.Colorizer(cmap="viridis", norm=norm)

            for i, channel in enumerate(channels):
                axs[i].set_title(f"Channel {channel}")

                signal, sample_rate = tradb.read_continuous_wave(
                    channel=channel,
                    time_start=None,
                    time_stop=None,
                    time_axis=False,
                    show_progress=False,
                )
                signal *= 1e3

                stft = ShortTimeFFT.from_window(
                    "hann",
                    sample_rate,
                    nperseg=sample_rate // 10,
                    noverlap=sample_rate // 20,
                    scale_to="magnitude",
                )

                spectro = stft.spectrogram(signal)
                spectro_dB = 10 * np.log(spectro)
                print(spectro_dB, np.min(spectro_dB), np.max(spectro_dB))

                img = axs[i].imshow(
                    spectro_dB,
                    origin="lower",
                    interpolation=None,
                    aspect="auto",
                    colorizer=colorizer,
                    extent=stft.extent(len(signal), "tf", False),
                )

                label_transform = blended_transform_factory(axs[i].transData, axs[i].transAxes)

                for time, label in metadata["labels"].items():
                    time = float(time)
                    axs[i].axvline(time, color="r", linewidth=1)
                    axs[i].annotate(
                        label,
                        (time, 1),
                        (0.1, -0.1),
                        color="r",
                        ha="left",
                        va="baseline",
                        xycoords=("data", "axes fraction"),
                        textcoords="offset fontsize",
                    )

        fig.colorbar(img, ax=axs)

        for p in produces:
            fig.savefig(p)
