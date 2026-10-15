import numpy as np
import pytask
import tomli_w
import vallenae

from ae_pipeline.task_config import DATASETS

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_plot_extract_metadata(
        primary_file=ds.primary_file,
        transient_file=ds.transient_file,
        produces=ds.metadata_file,
    ):
        pridb: vallenae.io.PriDatabase
        with vallenae.io.PriDatabase(str(primary_file)) as pridb:
            channels = pridb.channel()
            globalinfo = pridb.globalinfo()
            markers = pridb.read_markers(show_progress=False)
            markers = markers[(markers.set_type == 4) & np.logical_not(markers.data.str.contains("TimeZone:"))]

        with vallenae.io.TraDatabase(str(transient_file)) as tradb:
            record_length = 0

            for record in tradb.iread():
                record_length = record.samples
                break

        metadata = {
            "general": {
                "channels": list(channels),
                "clock_rate": int(globalinfo["TimeBase"]),
                "record_length": record_length,
            },
            "labels": {f"{m.time:.2f}": str(m.data) for m in markers.itertuples()},
        }

        text = tomli_w.dumps(metadata)
        produces.write_text(text)
