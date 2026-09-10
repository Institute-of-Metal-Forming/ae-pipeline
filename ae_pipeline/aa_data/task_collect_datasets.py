from pathlib import Path
from typing import Annotated

import pytask

from ae_pipeline.task_config import AA_DATA_DIR, CATALOG, Dataset


def task_collect_datasets(
    primary_files: Annotated[list[Path], pytask.DirectoryNode(root_dir=AA_DATA_DIR, pattern="*.pridb")],
    produces: pytask.PickleNode = CATALOG["datasets"],  # type: ignore
):
    datasets = [Dataset(primary_file=f) for f in primary_files]
    produces.save(datasets)
