import io
import subprocess
from functools import lru_cache

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytask
import soundfile as sf

from ae_pipeline.task_config import CATALOG, DEBUG, Dataset


@pytask.task(is_generator=True)
def task_gen_import_aa_data(
    datasets: list[Dataset] = CATALOG["datasets"],  # type: ignore
):
    for ds in datasets:

        @pytask.task(id=ds.name)
        def task_import_aa_data(
            primary_file=ds.primary_file,
            transient_file=ds.transient_file,
            produces=ds.data_file,
        ):
            ae_globalinfo = pd.read_sql_table("ae_globalinfo", f"sqlite:///{primary_file}", index_col="Key")
            ae_params = pd.read_sql_table("ae_params", f"sqlite:///{primary_file}", index_col="Chan")

            ae_data = pd.read_sql_table(
                "ae_data",
                f"sqlite:///{primary_file}",
                index_col="SetID",
                columns=["Time", "SetType", "Chan", "TRAI"],
                dtype_backend="numpy_nullable",
            )

            view_tr_data = pd.read_sql_table(
                "view_tr_data",
                f"sqlite:///{transient_file}",
                index_col="TRAI",
                columns=["Samples", "SampleRate", "Data", "TR_mV"],
            )

            clock_rate = int(ae_globalinfo.loc["TimeBase", "Value"])
            sample_rate = int(view_tr_data["SampleRate"].iloc[0])
            sample_clock_rate = clock_rate // sample_rate
            channel_count = len(ae_params) - 1
            set_length = int(view_tr_data["Samples"].iat[0])

            if DEBUG:
                assert np.all(sample_rate == view_tr_data["SampleRate"]), "sample rates must be all equal"
                assert np.all(set_length == view_tr_data["Samples"]), "set lengths must be all equal"

            view_tr_data.drop(["SampleRate", "Samples"], axis="columns")

            trai_map = ae_data[ae_data["SetType"] == 2].pivot(
                index="Time",
                columns="Chan",
                values="TRAI",
            )
            clocks_per_set = np.arange(0, set_length) * sample_clock_rate

            schema = pa.schema(
                [pa.field("clock", pa.int64()), pa.field("time", pa.float32())]
                + [pa.field(f"chan{i + 1}", pa.float32()) for i in range(channel_count)]
            )
            parquet_file = pq.ParquetWriter(produces, schema=schema)

            def get_sound_series(chan: int):
                trai = trai_map.loc[clock, chan]
                if trai < 1:
                    return pa.nulls(set_length, type=pa.float64())
                flac_data = view_tr_data.loc[trai, "Data"]
                sound_data, _ = sf.read(io.BytesIO(flac_data), dtype="float32")
                return pa.array(sound_data * view_tr_data.loc[trai, "TR_mV"])

            for clock in trai_map.index:
                clocks = clock + clocks_per_set
                batch = pa.record_batch(
                    [clocks, clocks / clock_rate] + [get_sound_series(chan) for chan in trai_map.columns],
                    schema=schema,
                )
                parquet_file.write_batch(batch)

            parquet_file.close()

        @pytask.task(id=ds.name)
        def task_describe_dataset(
            data_file=ds.data_file,
            produces=ds.data_file.with_suffix(".txt"),
        ):
            out = produces.open(mode="w")
            subprocess.run(["nail", "describe", str(data_file)], stdout=out)
            out.close()
