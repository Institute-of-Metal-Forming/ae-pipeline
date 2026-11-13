import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pytask
import vallenae
from scipy.signal import find_peaks, welch

from ae_pipeline.task_config import DATA_DIR, DATASETS, PLOTS_DIR

THRESHOLD = 32
NPERSEG = 2048

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_characterize_hits(
        primary_file=ds.primary_file,
        transient_file=ds.transient_file,
        ds=ds,
        produces=ds.hits_file,
    ):
        with vallenae.io.PriDatabase(str(primary_file.resolve())) as pridb:
            hits = pridb.read_hits(show_progress=False)

            result: pd.DataFrame = hits[
                ["time", "channel", "amplitude", "duration", "rise_time", "counts", "trai"]
            ].set_index("trai")
            signal_dB_series = {}
            psd_series = {}
            peaks_series = {}
            result.index = result.index.astype("uint16")
            result["counts"] = result.counts.astype("uint16")
            result["channel"] = result.channel.astype("uint8")
            result["nfft"] = pd.Series(None, dtype="uint16[pyarrow]")
            result["sample_rate"] = pd.Series(None, dtype="uint64[pyarrow]")

            with vallenae.io.TraDatabase(str(transient_file)) as tradb:
                for trai in result.index:
                    signal, sample_rate = tradb.read_wave(trai, time_axis=False)
                    signal *= 1e6
                    signal_dB = 10 * np.log(np.abs(signal))
                    signal_dB_series[trai] = signal_dB
                    result.at[trai, "sample_rate"] = sample_rate

                    _, psd = welch(signal, sample_rate, nperseg=NPERSEG, noverlap=NPERSEG // 2)
                    peaks, _ = find_peaks(psd / np.max(psd), prominence=0.2)
                    result.at[trai, "nfft"] = NPERSEG
                    psd_series[trai] = psd
                    peaks_series[trai] = peaks.astype("uint16")

        result["signal_dB"] = signal_dB_series
        result["psd"] = psd_series
        result["peaks"] = peaks_series

        result.to_parquet(produces, compression="brotli")
