import io
from pathlib import Path
from typing import Annotated

import numpy as np
import pandas as pd
import pytask
import soundfile as sf
import sqlalchemy.types as st

from ae_pipeline.task_config import AA_DATA_DIR

SAMPLING_RATE = 100_000
FREQUENCIES = [1, 10, 100, 1_000, 10_000]
INTENSITIES = [1, 0.5, 0.2, 0.1, 0.05]


@pytask.mark.try_first
def task_create_test_data(
    primary_file: Annotated[Path, pytask.Product] = AA_DATA_DIR / "test.pridb",
    transient_file: Annotated[Path, pytask.Product] = AA_DATA_DIR / "test.tradb",
):

    times = np.linspace(0, 2, SAMPLING_RATE * 2)
    signal = np.zeros_like(times)

    for f, i in zip(FREQUENCIES, INTENSITIES, strict=True):
        signal += i * np.sin(2 * np.pi * f * times)

    signal *= -((times - 1.0) ** 2) + 1
    signal /= signal.max()

    ae_data = pd.DataFrame(
        {
            "SetID": [1],
            "SetType": [2],
            "Time": [1024],
            "Chan": [1],
            "Status": [0],
            "ParamID": [2],
            "Thr": [66],
            "Amp": [1000],
            "RiseT": [1.0],
            "Dur": [2.0],
            "Eny": [1000],
            "SS": [None],
            "RMS": [None],
            "Counts": [500],
            "TRAI": [None],
            "PCTD": [None],
            "PCTA": [None],
        }
    )

    flac_io = io.BytesIO()
    sf.write(flac_io, signal, 44100, format="flac")
    flac_io.seek(0)
    flac_data = flac_io.read()
    flac_io.close()

    tr_data = pd.DataFrame(
        {
            "SetID": [1],
            "Time": [1024],
            "TRAI": [1],
            "Status": [0],
            "ParamID": [2],
            "Chan": [1],
            "Thr": [66],
            "SampleRate": [SAMPLING_RATE],
            "Samples": [len(times)],
            "DataFormat": [2],
            "Data": [flac_data],
        }
    )

    primary_file.unlink(missing_ok=True)
    transient_file.unlink(missing_ok=True)
    ae_data.to_sql("ae_data", f"sqlite:///{primary_file}")
    tr_data.to_sql("tr_data", f"sqlite:///{transient_file}", dtype={"Data": st.BLOB})
