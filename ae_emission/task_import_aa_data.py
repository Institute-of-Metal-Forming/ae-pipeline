import subprocess

import pandas as pd
import pytask

from ae_emission.config import DATASETS

primary_data_files = list()


for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_import_aa_data(
        primary_file=ds.primary_file,
        transient_file=ds.transient_file,
        produces=ds.data_file,
    ):

        ae_data = pd.read_sql_table("ae_data", f"sqlite:///{primary_file}")
        tr_data = pd.read_sql_table("tr_data", f"sqlite:///{transient_file}")

        data = (
            ae_data[["Time", "Amp", "Thr", "RiseT", "Counts"]]
            .set_index("Time", drop=True)
            .join(
                tr_data[["Time", "Samples", "SampleRate", "DataFormat", "Data"]].set_index("Time", drop=True),
                how="right",
            )
        )

        data.to_parquet(produces)

    @pytask.task(id=ds.name)
    def task_describe_dataset(
        data_file=ds.data_file,
        produces=ds.data_file.with_suffix(".txt"),
    ):
        out = produces.open(mode="w")
        subprocess.run(["nail", "describe", str(data_file)], stdout=out)
        out.close()
