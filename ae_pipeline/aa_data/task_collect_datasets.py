import pytask

from ae_pipeline.task_config import AA_DATA_DIR, CATALOG, Dataset


def task_collect_datasets(
    produces: pytask.PickleNode = CATALOG["datasets"],  # type: ignore
):
    datasets = [Dataset(primary_file=f) for f in AA_DATA_DIR.glob("*.pridb")]
    produces.save(datasets)
