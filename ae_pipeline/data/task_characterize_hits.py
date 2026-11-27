from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytask
import scipy.signal as sig
import vallenae

import ae_pipeline.metadata
import ae_pipeline.spectral
import ae_pipeline.units
from ae_pipeline.metadata import load_metadata
from ae_pipeline.spectral import welch_psd
from ae_pipeline.task_config import DATASETS
from ae_pipeline.units import volts_to_microvolts

PEAK_PROMINENCE = 0.2
"""Minimum prominence of a PSD peak relative to the PSD maximum."""

_BATCH_HITS = 5_000
"""Maximum number of hits read from the tradb at once."""

_ROW_GROUP_SAMPLES = 100_000_000
"""Approximate maximum number of waveform samples per parquet row group (bounds memory and list offsets)."""

_SCHEMA = pa.schema(
    [
        ("time", pa.float64()),
        ("channel", pa.uint8()),
        ("amplitude", pa.float32()),
        ("duration", pa.float32()),
        ("rise_time", pa.float32()),
        ("counts", pa.uint32()),
        ("pretrigger", pa.uint32()),
        ("signal", pa.list_(pa.float32())),
        ("psd", pa.list_(pa.float32())),
        ("peaks", pa.list_(pa.uint16())),
        ("trai", pa.uint32()),
    ]
)

for ds in DATASETS:

    @pytask.task(id=ds.name)
    def task_characterize_hits(
        primary_file=ds.primary_file,
        transient_file=ds.transient_file,
        metadata_file=ds.metadata_file,
        units_module=Path(ae_pipeline.units.__file__),
        spectral_module=Path(ae_pipeline.spectral.__file__),
        metadata_module=Path(ae_pipeline.metadata.__file__),
        produces=ds.hits_file,
    ):
        name = primary_file.stem
        sample_rate = load_metadata(metadata_file).general.sample_rate

        pridb: vallenae.io.PriDatabase
        with vallenae.io.PriDatabase(str(primary_file)) as pridb:
            hits = _read_hits(pridb)

        # written to a temporary file first, so a failing task leaves no output
        tmp_file = produces.with_name(f".{produces.name}.tmp")
        try:
            tradb: vallenae.io.TraDatabase
            with vallenae.io.TraDatabase(str(transient_file)) as tradb:
                _check_records_exist(name, hits, tradb)
                _write_hits(tmp_file, hits, tradb, sample_rate)
            tmp_file.replace(produces)
        finally:
            tmp_file.unlink(missing_ok=True)


def _read_hits(pridb: vallenae.io.PriDatabase) -> pd.DataFrame:
    """The pridb hits with a transient record, indexed by trai, amplitude in µV."""
    hits = pridb.read_hits(show_progress=False)
    # hits without a transient record have no trai (0 in vallenae)
    hits = hits[hits.trai.fillna(0) > 0]
    return pd.DataFrame(
        {
            "time": hits.time.to_numpy(np.float64),
            "channel": hits.channel.to_numpy(np.uint8),
            "amplitude": volts_to_microvolts(hits.amplitude.to_numpy(np.float64)).astype(np.float32),
            "duration": hits.duration.to_numpy(np.float32),
            "rise_time": hits.rise_time.to_numpy(np.float32),
            "counts": hits.counts.to_numpy(np.uint32),
        },
        index=pd.Index(hits.trai.to_numpy(np.uint32), name="trai"),
    )


def _check_records_exist(name: str, hits: pd.DataFrame, tradb: vallenae.io.TraDatabase) -> None:
    """Raise if a hit refers to a trai without a tradb record (malformed dataset, 0003 R9)."""
    trais = {int(r[0]) for r in tradb.connection().execute("SELECT TRAI FROM tr_data").fetchall()}
    missing = sorted(set(hits.index.tolist()) - trais)
    if missing:
        raise ValueError(
            f"Dataset {name} is malformed: {len(missing)} hits refer to trais without a tradb record, "
            f"e.g. {missing[:10]}."
        )


def _write_hits(path: Path, hits: pd.DataFrame, tradb: vallenae.io.TraDatabase, sample_rate: float) -> None:
    """Characterize the hits batch-wise and write them as parquet, one row group per ~_ROW_GROUP_SAMPLES samples."""
    writer: pq.ParquetWriter | None = None
    rows: list[pd.DataFrame] = []
    n_samples = 0

    def flush():
        nonlocal writer, rows, n_samples
        table = pa.Table.from_pandas(pd.concat(rows), schema=_SCHEMA, preserve_index=True)
        if writer is None:
            writer = pq.ParquetWriter(path, table.schema, compression="brotli")
        writer.write_table(table)
        rows, n_samples = [], 0

    try:
        for start in range(0, len(hits), _BATCH_HITS):
            batch = _characterize(hits.iloc[start : start + _BATCH_HITS], tradb, sample_rate)
            rows.append(batch)
            n_samples += int(batch.signal.map(len).sum())
            if n_samples >= _ROW_GROUP_SAMPLES:
                flush()
        if rows or writer is None:
            if not rows:
                rows.append(_characterize(hits, tradb, sample_rate))
            flush()
    finally:
        if writer is not None:
            writer.close()


def _characterize(hits: pd.DataFrame, tradb: vallenae.io.TraDatabase, sample_rate: float) -> pd.DataFrame:
    """Add pretrigger, signal (µV), PSD and PSD peaks to a batch of hits."""
    records = {record.trai: record for record in tradb.iread(trai=hits.index.tolist())} if len(hits) else {}

    pretriggers, signals, psds, peaks = [], [], [], []
    for trai in hits.index:
        record = records[trai]
        signal = volts_to_microvolts(np.asarray(record.data, dtype=np.float64))
        psd = welch_psd(signal, sample_rate)

        psd_max = np.max(psd)
        if psd_max > 0:
            psd_peaks, _ = sig.find_peaks(psd / psd_max, prominence=PEAK_PROMINENCE)
        else:
            psd_peaks = np.array([], dtype=np.intp)

        pretriggers.append(record.pretrigger)
        signals.append(signal.astype(np.float32))
        psds.append(psd.astype(np.float32))
        peaks.append(psd_peaks.astype(np.uint16))

    result = hits.copy()
    result["pretrigger"] = np.asarray(pretriggers, dtype=np.uint32)
    result["signal"] = pd.Series(signals, index=hits.index, dtype=object)
    result["psd"] = pd.Series(psds, index=hits.index, dtype=object)
    result["peaks"] = pd.Series(peaks, index=hits.index, dtype=object)
    return result
