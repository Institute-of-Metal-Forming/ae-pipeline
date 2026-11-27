from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ae_pipeline.data.task_characterize_hits import (
    _characterize,
    _check_records_exist,
    _read_hits,
    _write_hits,
)
from ae_pipeline.spectral import NPERSEG, psd_frequencies

SAMPLE_RATE = 10_000_000


class _FakePriDatabase:
    def __init__(self, hits: pd.DataFrame):
        self._hits = hits

    def read_hits(self, **kwargs) -> pd.DataFrame:
        return self._hits


class _FakeConnection:
    def __init__(self, trais: list[int]):
        self._trais = trais

    def execute(self, query: str):
        assert "TRAI" in query
        return SimpleNamespace(fetchall=lambda: [(t,) for t in self._trais])


class _FakeTraDatabase:
    def __init__(self, records: dict[int, tuple[np.ndarray, int]]):
        self._records = records

    def connection(self):
        return _FakeConnection(list(self._records))

    def iread(self, trai: list[int]):
        for t in trai:
            data, pretrigger = self._records[t]
            yield SimpleNamespace(trai=t, data=data, pretrigger=pretrigger)


def _pridb_hits() -> pd.DataFrame:
    """Hits as returned by ``PriDatabase.read_hits`` (values in V and s)."""
    return pd.DataFrame(
        {
            "time": [0.1, 0.2, 0.3, 0.4],
            "channel": pd.array([2, 1, 1, 3], dtype="Int64"),
            "amplitude": [1e-4, 2e-4, 3e-4, 4e-4],
            "duration": [1e-3, 2e-3, 3e-3, 4e-3],
            "rise_time": [1e-5, 2e-5, 3e-5, 4e-5],
            "counts": pd.array([1, 2, 70_000, 4], dtype="Int64"),
            "threshold": [28.9e-6] * 4,
            "trai": pd.array([1, 0, 2, pd.NA], dtype="Int64"),
        }
    )


def _sine(frequency: float, n: int, amplitude: float = 1e-4) -> np.ndarray:
    return amplitude * np.sin(2 * np.pi * frequency * np.arange(n) / SAMPLE_RATE)


# --- 0003 R2, R3 ---


def test_read_hits_skips_hits_without_trai_and_converts():
    hits = _read_hits(_FakePriDatabase(_pridb_hits()))

    assert hits.index.name == "trai"
    assert hits.index.dtype == np.uint32
    assert hits.index.tolist() == [1, 2]  # pridb order, trai 0 and NA skipped
    assert hits.time.dtype == np.float64
    assert hits.channel.dtype == np.uint8
    assert hits.counts.dtype == np.uint32
    assert hits.counts.tolist() == [1, 70_000]
    for column in ["amplitude", "duration", "rise_time"]:
        assert hits[column].dtype == np.float32
    np.testing.assert_allclose(hits.amplitude, [100.0, 300.0], rtol=1e-6)  # µV
    np.testing.assert_allclose(hits.duration, [1e-3, 3e-3], rtol=1e-6)


# --- 0003 R9 ---


def test_check_records_exist_raises_for_missing_trai():
    hits = pd.DataFrame({"time": [0.1, 0.2]}, index=pd.Index(np.array([1, 7], dtype=np.uint32), name="trai"))
    tradb = _FakeTraDatabase({1: (np.zeros(10), 0)})
    with pytest.raises(ValueError, match=r"ds.*\[7\]"):
        _check_records_exist("ds", hits, tradb)


def test_check_records_exist_passes():
    hits = pd.DataFrame({"time": [0.1]}, index=pd.Index(np.array([1], dtype=np.uint32), name="trai"))
    _check_records_exist("ds", hits, _FakeTraDatabase({1: (np.zeros(10), 0), 2: (np.zeros(10), 0)}))


# --- 0003 R4 ---


def test_characterize_signal_psd_peaks():
    hits = _read_hits(_FakePriDatabase(_pridb_hits()))
    tradb = _FakeTraDatabase(
        {
            1: (_sine(250_000.0, 20 * NPERSEG), 1000),
            2: (_sine(1_000_000.0, NPERSEG // 4), 229),  # shorter than a segment
        }
    )
    result = _characterize(hits, tradb, SAMPLE_RATE)
    f = psd_frequencies(SAMPLE_RATE)

    assert result.pretrigger.tolist() == [1000, 229]
    assert len(result.signal.iloc[0]) == 20 * NPERSEG
    assert len(result.signal.iloc[1]) == NPERSEG // 4  # original record length kept
    assert result.signal.iloc[0].dtype == np.float32
    np.testing.assert_allclose(np.max(result.signal.iloc[0]), 100.0, rtol=1e-3)  # µV

    for psd, peaks, frequency in zip(result.psd, result.peaks, [250_000.0, 1_000_000.0], strict=True):
        assert psd.dtype == np.float32
        assert psd.shape == (NPERSEG // 2 + 1,)
        assert peaks.dtype == np.uint16
        assert np.all(np.diff(peaks.astype(int)) > 0)
        assert abs(f[np.argmax(psd)] - frequency) <= f[1]
        assert np.argmax(psd) in peaks


def test_characterize_zero_signal_has_no_peaks():
    hits = _read_hits(_FakePriDatabase(_pridb_hits())).iloc[:1]
    result = _characterize(hits, _FakeTraDatabase({1: (np.zeros(NPERSEG), 0)}), SAMPLE_RATE)
    assert np.all(result.psd.iloc[0] == 0)
    assert len(result.peaks.iloc[0]) == 0


# --- 0003 R2–R5: written file ---


def test_write_hits_roundtrip(tmp_path: Path):
    hits = _read_hits(_FakePriDatabase(_pridb_hits()))
    tradb = _FakeTraDatabase({1: (_sine(250_000.0, 3000), 1000), 2: (_sine(500_000.0, 5000), 1000)})
    path = tmp_path / "x.hits.parquet"
    _write_hits(path, hits, tradb, SAMPLE_RATE)

    df = pd.read_parquet(path, dtype_backend="pyarrow")
    assert df.index.name == "trai"
    assert str(df.index.dtype) == "uint32[pyarrow]"
    assert df.index.tolist() == [1, 2]
    assert list(df.columns) == [
        "time",
        "channel",
        "amplitude",
        "duration",
        "rise_time",
        "counts",
        "pretrigger",
        "signal",
        "psd",
        "peaks",
    ]
    assert str(df.time.dtype) == "double[pyarrow]"
    assert str(df.amplitude.dtype) == "float[pyarrow]"
    assert str(df.signal.dtype) == "list<element: float>[pyarrow]"
    assert str(df.peaks.dtype) == "list<element: uint16>[pyarrow]"
    assert len(np.array(df.signal.iloc[1])) == 5000
