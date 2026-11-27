import numpy as np
import pandas as pd
import pytask

from ae_pipeline.task_config import DATASETS

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_birch_cluster(
        hits_file=ds.hits_file,
    ):
        hits = pd.read_parquet(hits_file, columns=["peaks"], dtype_backend="pyarrow")

        _all_peaks = np.array(hits.peaks)
