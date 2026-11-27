# 0001 Dataset discovery

- **Status:** implemented
- **Module:** `ae_pipeline/task_config.py` (`Dataset`, `DATASETS`)

## Summary

Every task is created once per dataset. A dataset is a pair of Vallen files with the same stem in `ae_pipeline/data/`. This spec defines how datasets are discovered and which paths are derived from them.

## Inputs

- `ae_pipeline/data/<name>.pridb`: Vallen primary database (SQLite).
- `ae_pipeline/data/<name>.tradb`: Vallen transient recording database (SQLite).

## Requirements

1. `DATASETS` contains one `Dataset` for every file matching `ae_pipeline/data/*.pridb` (not recursive) that has a corresponding `.tradb` (R4). The order is unspecified.

2. `Dataset.name` is the stem of the primary file, e.g. `2026-11-26-walzen1`. It is the task id used by all per-dataset tasks and the name of the dataset's plot directory.

3. The derived paths are siblings of the primary file:

   | Property         | Path                          |
   | ---------------- | ----------------------------- |
   | `transient_file` | `<name>.tradb`                |
   | `hits_file`      | `<name>.hits.parquet` (0003)  |
   | `metadata_file`  | `<name>.metadata.toml` (0002) |

4. A `.pridb` without a corresponding `.tradb` is skipped during discovery: it is not added to `DATASETS`, so no tasks are created for it, and task collection continues for all other datasets. A warning naming the skipped `.pridb` file is emitted.

5. Constructing a `Dataset` directly still validates its inputs: it raises a `ValueError` if the primary file or the corresponding transient file does not exist.

6. A `.tradb` without a corresponding `.pridb` is also skipped with a warning.

7. Files and directories starting with `.` or `_` (e.g. `ae_pipeline/data/_trash/`) are not part of the pipeline. Since R1 only globs the top level of `ae_pipeline/data/`, datasets inside such directories are not discovered.

8. `task_config.py` defines no unused flags or settings. The flag `DEBUG` is removed; `EACH_HIT` (0006) is the only feature flag.

## Open questions

None.
