import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytask
import scipy.fft as fft
import scipy.signal as sgn
import soundfile as sf

from ae_pipeline.task_config import CATALOG, Dataset, Waveform, image_produces


def db_max(a):
    return 10 * np.log10(a / np.max(a))


@pytask.task(after="task_import_aa_data")  # to prevent running before data files exist, currently no way
def task_collect_waveforms(
    datasets: list[Dataset] = CATALOG["datasets"],  # type: ignore
    produces: pytask.PickleNode = CATALOG["waveforms"],  # type: ignore
):
    def yield_waveforms_for_datasets():
        for ds in datasets:
            data = pd.read_parquet(ds.data_file)
            for time in data.index:
                yield Waveform(dataset=ds, time=time, sample_rate=data.loc[time, "SampleRate"])

    produces.save(list(yield_waveforms_for_datasets()))


@pytask.task(is_generator=True)
def task_gen_waveforms(
    waveforms: list[Waveform] = CATALOG["waveforms"],  # type: ignore
):
    for wf in waveforms:

        @pytask.task(id=wf.name)
        def task_waveform_decode(
            data_file=wf.dataset.data_file,
            produces=wf.signal_file,
            wf=wf,
        ):
            data = pd.read_parquet(data_file)
            flac_data = data.loc[wf.time, "Data"]
            sound_data, _ = sf.read(io.BytesIO(flac_data))
            signal = pd.DataFrame(
                {
                    "time": np.arange(0, len(sound_data)) / wf.sample_rate,
                    "signal": sound_data,
                }
            )
            signal.to_parquet(produces)

        @pytask.task(id=wf.name)
        def task_waveform_fft(
            signal_file=wf.signal_file,
            produces=wf.fft_file,
            wf=wf,
        ):
            signal = pd.read_parquet(signal_file)
            time_step = 1.0 / wf.sample_rate

            freq = fft.rfftfreq(len(signal), time_step)
            rfft = fft.rfft(signal.signal)

            signal_fft = pd.DataFrame(
                {
                    "freq": freq,
                    "real": np.real(rfft),
                    "imag": np.imag(rfft),
                    "magn": np.abs(rfft),
                }
            )

            signal_fft.to_parquet(produces)

        @pytask.task(id=wf.name)
        def task_waveform_psd(
            signal_file=wf.signal_file,
            produces=wf.psd_file,
            wf=wf,
        ):
            signal = pd.read_parquet(signal_file)
            target_freq = 1e3
            welch = sgn.welch(
                signal.signal.array, wf.sample_rate, window="hann", nperseg=int(10.0 / target_freq * wf.sample_rate)
            )

            signal_psd = pd.DataFrame(
                {
                    "freq": welch[0],
                    "psd": welch[1],
                    "log_psd": np.log(welch[1]),
                    "psd_db": db_max(welch[1]),
                }
            )

            signal_psd.to_parquet(produces)

        @pytask.task(id=wf.name)
        def task_waveform_plot(
            signal_file=wf.signal_file,
            produces=image_produces(wf.signal_file),
        ):
            signal = pd.read_parquet(signal_file)
            fig, ax = plt.subplots()
            ax.set_xlabel("Time in s")
            ax.set_ylabel("Signal Intensity")

            ax.plot(signal.time, signal.signal)

            for p in produces:
                fig.savefig(p)

            plt.close(fig)

        @pytask.task(id=wf.name)
        def task_waveform_fft_plot(
            fft_file=wf.fft_file,
            produces=image_produces(wf.fft_file),
        ):
            fft = pd.read_parquet(fft_file)
            fig, ax = plt.subplots()
            ax.set_xlabel("Frequency in Hz")
            ax.set_xscale("log")
            ax.set_ylabel("Component Intensity")
            ax.set_yscale("log")

            ax.plot(fft.freq, fft.magn)

            for p in produces:
                fig.savefig(p)

            plt.close(fig)

        @pytask.task(id=wf.name)
        def task_waveform_psd_plot(
            psd_file=wf.psd_file,
            produces=image_produces(wf.psd_file),
        ):
            psd = pd.read_parquet(psd_file)
            fig, ax = plt.subplots()
            ax.set_xlabel("Frequency in Hz")
            ax.set_xscale("log")
            ax.set_ylabel("Power Spectral Density in dB")

            ax.plot(psd.freq, psd.psd_db)

            peaks, _ = sgn.find_peaks(psd.psd_db.array, prominence=10)
            ax.scatter(psd.freq[peaks], psd.psd_db[peaks], marker="x", color="r")

            for p in produces:
                fig.savefig(p)

            plt.close(fig)
