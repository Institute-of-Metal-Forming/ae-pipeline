import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytask
import scipy.fft as fft
import soundfile as sf

from ae_pipeline.task_config import CATALOG, Dataset, Waveform, image_produces


def task_collect_waveforms(
    datasets: list[Dataset] = CATALOG["datasets"],  # type: ignore
    produces: pytask.PickleNode = CATALOG["waveforms"],  # type: ignore
):
    def yield_waveforms_for_datasets():
        for ds in datasets:
            data = pd.read_parquet(ds.data_file)
            for time in data.index:
                yield Waveform(dataset=ds, time=time)

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
            time=wf.time,
        ):
            data = pd.read_parquet(data_file)
            flac_data = data.loc[time, "Data"]
            sample_rate = data.loc[time, "SampleRate"]
            sound_data, _ = sf.read(io.BytesIO(flac_data))
            signal = pd.DataFrame(
                {
                    "time": np.arange(0, len(sound_data)) / sample_rate,
                    "signal": sound_data,
                }
            )
            signal.to_parquet(produces)

        @pytask.task(id=wf.name)
        def task_waveform_fft(
            signal_file=wf.signal_file,
            produces=wf.fft_file,
            time=wf.time,
        ):
            signal = pd.read_parquet(signal_file)
            time_steps = np.diff(signal.time.array[:2])
            assert np.all(np.positive(time_steps))
            time_step = time_steps[0]

            signal_fft = pd.DataFrame(
                {
                    "freq": fft.rfftfreq(len(signal), time_step),
                    "rfft": fft.rfft(signal.signal),
                }
            )
            signal_fft["real"] = np.real(signal_fft.rfft)
            signal_fft["imag"] = np.imag(signal_fft.rfft)
            signal_fft["magn"] = np.sqrt(np.real(signal_fft.rfft) ** 2 + np.imag(signal_fft.rfft) ** 2)
            del signal_fft["rfft"]

            signal_fft.to_parquet(produces)

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

            ax.fill_between(fft.freq, 0, fft.magn)

            for p in produces:
                fig.savefig(p)

            plt.close(fig)
