from pathlib import Path
from typing import Annotated

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytask

from ae_pipeline.task_config import DATASETS, PLOTS_DIR

THRESHOLD = 32

for ds in DATASETS:

    @pytask.task(id=ds.name, is_generator=True)
    def task_plot_hits(
        produces: Annotated[
            Path,
            pytask.DirectoryNode(name=ds.name + "/hits", root_dir=PLOTS_DIR / ds.name / "hits", pattern="*.png"),
            pytask.Product,
        ],
        hits_file=ds.hits_file,
        ds=ds,
    ):
        df = pd.read_parquet(hits_file, dtype_backend="pyarrow")

        for trai in df.index:
            fig, axs = plt.subplots(2, figsize=(6.4, 4.8))

            axs[0].set_xlabel("Time t in s")
            axs[0].set_ylabel("Intensity in dB_AE")
            axs[0].margins(x=0)

            axs[1].set_xlabel("Frequency in kHz")
            axs[1].set_ylabel("Power Spectral Density in (µV)²/Hz")
            axs[1].margins(x=0)

            sample_rate = df.sample_rate[trai]
            signal = np.array(df.signal_dB[trai])
            times = np.arange(len(signal), dtype="float64") / sample_rate

            axs[0].stem(times, signal, markerfmt="", basefmt="")
            axs[0].set_ylim(0, 100)
            axs[0].axhline(THRESHOLD, color="r", linestyle="--", linewidth=1)

            nfft = df.nfft[trai]
            freqs = np.fft.rfftfreq(nfft, d=1 / sample_rate) * 1e-3
            psd = np.array(df.psd[trai])
            peaks = np.array(df.peaks[trai])

            axs[1].plot(freqs, psd)
            axs[1].scatter(freqs[peaks], psd[peaks], marker="+", c="r", lw=0.5)
            axs[1].set_ylim(0, None)

            for p in df.peaks[trai]:
                axs[1].annotate(
                    f"{freqs[p]:.0f}",
                    (freqs[p], psd[p]),
                    (0.3, 0.3),
                    color="r",
                    ha="left",
                    va="baseline",
                    xycoords="data",
                    textcoords="offset fontsize",
                    fontsize="5",
                )

            fig.savefig(produces / f"hit_{trai}.png")

            plt.close(fig)
