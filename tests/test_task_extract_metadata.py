import numpy as np
import pandas as pd
import pytest

from ae_pipeline.data.task_extract_metadata import DEFAULT_THRESHOLD, _labels, _sample_rate, _thresholds


def _markers(rows: list[tuple[float, int, str]]) -> pd.DataFrame:
    """Markers as returned by ``PriDatabase.read_markers``: time, set_type, data."""
    time, set_type, data = zip(*rows, strict=True) if rows else ((), (), ())
    return pd.DataFrame(
        {"time": list(time), "set_type": pd.array(list(set_type), dtype="Int64"), "data": list(data)},
    )


def _pairs(channel: list[int], threshold_uV: list[float]) -> list[tuple[int, float]]:
    """Distinct (channel, threshold in µV) pairs as returned by the ``view_ae_data`` query."""
    return list(zip(channel, threshold_uV, strict=True))


# --- 0002 R3, R4: labels ---


def test_labels_selects_set_type_4_without_timezone():
    markers = _markers(
        [
            (0.0, 6, ""),
            (0.0, 4, "13:38 Resume"),
            (0.0, 5, "2026-11-26 13:38:20"),
            (0.0, 4, "TimeZone: +01:00 (W. Europe Standard Time)"),
            (95.18, 4, "13:39 P2"),
            (519.36, 4, "13:47 Suspend"),
        ]
    )
    labels = _labels("ds", markers)
    assert list(labels.items()) == [("13:38 Resume", 0.0), ("13:39 P2", 95.18), ("13:47 Suspend", 519.36)]


# --- 0002 R7: duplicate marker texts ---


def test_labels_duplicate_texts_raise():
    markers = _markers([(0.0, 4, "a"), (1.0, 4, "b"), (2.0, 4, "a")])
    with pytest.raises(ValueError, match=r"ds.*\['a'\]"):
        _labels("ds", markers)


def test_labels_duplicate_timezone_markers_are_ignored():
    markers = _markers([(0.0, 4, "TimeZone: x"), (0.0, 4, "TimeZone: x"), (1.0, 4, "a")])
    assert _labels("ds", markers) == {"a": 1.0}


# --- 0002 R5, R8, R10: sample rate ---


def test_sample_rate_single():
    assert _sample_rate("ds", [10_000_000]) == 10_000_000


def test_sample_rate_no_records_raises():
    with pytest.raises(ValueError, match="ds"):
        _sample_rate("ds", [])


def test_sample_rate_several_raises():
    with pytest.raises(ValueError, match=r"ds.*5000000.*10000000"):
        _sample_rate("ds", [5_000_000, 10_000_000])


# --- 0002 R6, R9: thresholds ---


def test_thresholds_in_microvolts_unchanged():
    thresholds = _thresholds("ds", [1, 2], _pairs([2, 1], [40.0, 28.9]))
    assert thresholds == {1: pytest.approx(28.9), 2: pytest.approx(40.0)}


def test_thresholds_default_for_channel_without_hits_warns():
    with pytest.warns(UserWarning, match=r"ds.*channel 2"):
        thresholds = _thresholds("ds", [1, 2], _pairs([1], [28.9]))
    assert DEFAULT_THRESHOLD == 32.0
    assert thresholds[2] == pytest.approx(10 ** (32 / 20))  # ≈ 39.81 µV


def test_thresholds_several_per_channel_raise():
    with pytest.raises(ValueError, match=r"ds.*channel 1"):
        _thresholds("ds", [1, 2], _pairs([1, 1, 2], [28.9, 30.0, 28.9]))


def test_thresholds_ignore_nan():
    assert _thresholds("ds", [1], _pairs([1, 1], [28.9, np.nan])) == {1: pytest.approx(28.9)}
