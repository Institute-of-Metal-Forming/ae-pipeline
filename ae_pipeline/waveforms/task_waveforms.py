import io
from pathlib import Path
from typing import Annotated

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytask
import scipy.fft as fft
import soundfile as sf
from matplotlib.figure import Figure

from ae_pipeline.task_config import DATASETS

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_waveforms(
        waveform_dir: Annotated[Path, pytask.DirectoryNode(root_dir=ds.waveforms_dir, pattern="*"), pytask.Product],
        data_file=ds.data_file,
    ):
        data = pd.read_parquet(data_file)

        print(data)

        for time in data.index:
            flac_data = data.loc[time, "Data"]
            sample_rate = data.loc[time, "SampleRate"]
            sound_data, _ = sf.read(io.BytesIO(flac_data))
            waveform = pd.DataFrame(
                {
                    "time": np.arange(0, len(sound_data)) / sample_rate,
                    "signal": sound_data,
                }
            )
            waveform_fft = pd.DataFrame(
                {
                    "freq": fft.rfftfreq(len(waveform), 1.0 / sample_rate),
                    "rfft": fft.rfft(waveform.signal),
                }
            )
            waveform_fft["real"] = np.real(waveform_fft.rfft)
            waveform_fft["imag"] = np.imag(waveform_fft.rfft)
            waveform_fft["norm"] = np.sqrt(np.real(waveform_fft.rfft) ** 2 + np.imag(waveform_fft.rfft) ** 2)
            del waveform_fft["rfft"]

            waveform.to_parquet(waveform_dir / f"waveform_{time}.parquet")
            waveform_fft.to_parquet(waveform_dir / f"waveform_fft_{time}.parquet")

            fig = plot_waveform(waveform, waveform_fft)
            fig.savefig(waveform_dir / f"waveform_{time}.png", dpi=600)


def plot_waveform(waveform: pd.DataFrame, waveform_fft: pd.DataFrame) -> Figure:
    fig, axs = plt.subplots(2, 1)

    axs[0].plot(waveform.time, waveform.signal)
    axs[0].set_xlabel("Time in s")

    axs[1].stem(waveform_fft.freq, waveform_fft.norm, markerfmt=" ", basefmt=" ")
    axs[1].set_xlabel("Frequency in Hz")
    axs[1].set_xscale("log")

    return fig
