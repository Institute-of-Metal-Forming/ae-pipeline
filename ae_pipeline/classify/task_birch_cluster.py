import numpy as np
import pandas as pd
import pytask

from ae_pipeline.task_config import DATASETS

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_birch_cluster(
        hits_file=ds.hits_file,
        ds=ds,
    ):
        hits = pd.read_parquet(hits_file, dtype_backend="pyarrow")

        all_peaks = np.array(hits.peaks)
