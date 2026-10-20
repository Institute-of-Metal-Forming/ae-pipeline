import matplotlib.pyplot as plt
import numpy as np
import pytask
import vallenae
from scipy.signal import find_peaks, welch

from ae_pipeline.task_config import DATASETS, PLOTS_DIR

THRESHOLD = 32

for ds in DATASETS:

    @pytask.task(id=ds.name, is_generator=True)
    def task_gen_plot_hits(
        primary_file=ds.primary_file,
        ds=ds,
    ):
        with vallenae.io.PriDatabase(str(primary_file.resolve())) as pridb:
            for hit in pridb.iread_hits():

                @pytask.task(id=f"{ds.name}/{hit.trai}")
                def task_plot_hit(
                    transient_file=ds.transient_file,
                    trai=hit.trai,
                    produces=[PLOTS_DIR / ds.name / "hits" / f"hit_{hit.trai}.{suffix}" for suffix in ["png"]],
                ):
                    tradb: vallenae.io.TraDatabase
                    with vallenae.io.TraDatabase(str(transient_file)) as tradb:
                        fig, axs = plt.subplots(2, figsize=(6.4, 4.8))

                        axs[0].set_xlabel("Time t in s")
                        axs[0].set_ylabel("Intensity in dB_AE")
                        axs[0].margins(x=0)

                        axs[1].set_xlabel("Frequency in kHz")
                        axs[1].set_ylabel("Power Spectral Density in (µV)²/Hz")
                        axs[1].margins(x=0)

                        signal, sample_rate = tradb.read_wave(trai, time_axis=False)
                        signal *= 1e6
                        signal_dB = 10 * np.log(np.abs(signal))

                        times = np.arange(len(signal), dtype="float64") / sample_rate
                        signal_dB[signal_dB < THRESHOLD] = np.nan

                        axs[0].stem(times, signal_dB, markerfmt="", basefmt="")
                        axs[0].set_ylim(THRESHOLD, 100)

                        freqs, psd = welch(signal, sample_rate, nperseg=2048, noverlap=1024)
                        freqs *= 1e-3
                        peaks, _ = find_peaks(psd / np.max(psd), prominence=0.2)

                        axs[1].plot(freqs, psd)
                        axs[1].scatter(freqs[peaks], psd[peaks], marker="+", c="r", lw=0.5)
                        axs[1].set_ylim(0, None)

                        for p in peaks:
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

                    for p in produces:
                        fig.savefig(p)

                    plt.close(fig)
