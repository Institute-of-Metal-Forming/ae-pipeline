from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ae_pipeline.plots.task_plot_waterfall import _add_hit, _channel_psds, _latex_escape, _sanitize_file_name
from ae_pipeline.spectral import HOP, NPERSEG, psd_frequencies, short_time_fft

SAMPLE_RATE = 10_000_000
HOP_TIME = HOP / SAMPLE_RATE


def _sine(frequency: float, n: int, amplitude: float = 100.0) -> np.ndarray:
    return amplitude * np.sin(2 * np.pi * frequency * np.arange(n) / SAMPLE_RATE)


def _expected(signal, record_start, hit_start, hit_end, start, bin_width, n_bins):
    """Reference binning, written independently of the implementation (0004 R2)."""
    spectrogram = short_time_fft(SAMPLE_RATE).spectrogram(signal)  # column k centered at k * HOP (p_min == 0)
    result = np.zeros((n_bins, NPERSEG // 2 + 1))
    for b in range(n_bins):
        bin_lo, bin_hi = start + b * bin_width, start + (b + 1) * bin_width
        for k in range(spectrogram.shape[1]):
            center = record_start + k * HOP_TIME
            lo = max(center - HOP_TIME / 2, hit_start, bin_lo)
            hi = min(center + HOP_TIME / 2, hit_end, bin_hi)
            if hi > lo:
                result[b] = np.maximum(result[b], spectrogram[:, k])
    return result


# --- 0004 R2: binning of one hit ---


def test_add_hit_only_within_hit_span():
    signal = _sine(250_000.0, 20 * NPERSEG)  # 4.096 ms
    n_bins, bin_width = 50, 0.1e-3
    psd = np.zeros((n_bins, NPERSEG // 2 + 1))
    _add_hit(
        psd,
        short_time_fft(SAMPLE_RATE),
        signal,
        record_start=0.0,
        hit_start=1.05e-3,
        hit_end=2.95e-3,
        start=0.0,
        bin_width=bin_width,
    )

    nonzero = np.flatnonzero(psd.max(axis=1) > 0)
    assert nonzero.tolist() == list(range(10, 30))
    expected = _expected(signal, 0.0, 1.05e-3, 2.95e-3, 0.0, bin_width, n_bins)
    np.testing.assert_allclose(psd, expected, rtol=1e-12)
    f = psd_frequencies(SAMPLE_RATE)
    assert np.all(np.abs(f[np.argmax(psd[nonzero], axis=1)] - 250_000.0) <= f[1])


def test_add_hit_many_columns_per_bin_keeps_maximum():
    # bins much wider than a hop: every bin holds the maximum over several columns
    signal = _sine(250_000.0, 40 * NPERSEG) * np.linspace(0.1, 1.0, 40 * NPERSEG)
    n_bins, bin_width = 4, 2e-3
    psd = np.zeros((n_bins, NPERSEG // 2 + 1))
    _add_hit(psd, short_time_fft(SAMPLE_RATE), signal, 0.0, 0.5e-3, 7.5e-3, 0.0, bin_width)
    np.testing.assert_allclose(psd, _expected(signal, 0.0, 0.5e-3, 7.5e-3, 0.0, bin_width, n_bins), rtol=1e-12)


def test_add_hit_record_start_offset():
    # the record starts before the plotted range (pretrigger) and the plotted range does not start at 0
    signal = _sine(500_000.0, 10 * NPERSEG)
    record_start, start = 9.9995, 10.0
    n_bins, bin_width = 30, 0.1e-3
    psd = np.zeros((n_bins, NPERSEG // 2 + 1))
    _add_hit(psd, short_time_fft(SAMPLE_RATE), signal, record_start, 10.00002, 10.00151, start, bin_width)
    expected = _expected(signal, record_start, 10.00002, 10.00151, start, bin_width, n_bins)
    np.testing.assert_allclose(psd, expected, rtol=1e-12)
    assert np.flatnonzero(psd.max(axis=1) > 0).tolist() == list(range(0, 16))


def test_add_hit_overlapping_hits_keep_maximum():
    stft = short_time_fft(SAMPLE_RATE)
    a, b = _sine(250_000.0, 10 * NPERSEG, 100.0), _sine(1_000_000.0, 10 * NPERSEG, 10.0)
    args = dict(record_start=0.0, hit_start=0.3e-3, hit_end=1.7e-3, start=0.0, bin_width=0.1e-3)
    psd_a, psd_b, psd_ab = (np.zeros((20, NPERSEG // 2 + 1)) for _ in range(3))
    _add_hit(psd_a, stft, a, **args)
    _add_hit(psd_b, stft, b, **args)
    _add_hit(psd_ab, stft, a, **args)
    _add_hit(psd_ab, stft, b, **args)
    np.testing.assert_array_equal(psd_ab, np.maximum(psd_a, psd_b))


def test_add_hit_short_record():
    # records shorter than a segment still contribute (0009 R3 padding)
    signal = _sine(250_000.0, 300)
    psd = np.zeros((10, NPERSEG // 2 + 1))
    _add_hit(psd, short_time_fft(SAMPLE_RATE), signal, 0.0, 10e-6, 25e-6, 0.0, 5e-6)
    assert np.flatnonzero(psd.max(axis=1) > 0).tolist() == [2, 3, 4]


def test_add_hit_empty_span_adds_nothing():
    psd = np.zeros((10, NPERSEG // 2 + 1))
    _add_hit(psd, short_time_fft(SAMPLE_RATE), _sine(250_000.0, 4096), 0.0, 1e-4, 1e-4, 0.0, 1e-5)
    assert np.all(psd == 0)


# --- 0004 R2: per-channel images from one pass over the hits table ---


def test_channel_psd_filters_channel_and_uses_pretrigger(tmp_path: Path):
    pretrigger = 1000
    hits = pd.DataFrame(
        {
            "time": [1.0, 1.0, 1.00205],
            "channel": np.array([1, 2, 1], dtype=np.uint8),
            "duration": np.array([0.45e-3, 1e-3, 0.2e-3], dtype=np.float32),
            "pretrigger": np.array([pretrigger] * 3, dtype=np.uint32),
            "signal": [_sine(250_000.0, 10 * NPERSEG).astype(np.float32)] * 3,
        },
        index=pd.Index(np.array([1, 2, 3], dtype=np.uint32), name="trai"),
    )
    path = tmp_path / "x.hits.parquet"
    hits.to_parquet(path)

    psds = _channel_psds(path, [1, 2], SAMPLE_RATE, 1.0, 1.003, n_bins=30, max_duration=1e-3)

    # bins of 0.1 ms: hit 1 covers [1.0, 1.00045] -> bins 0..4, hit 3 covers [1.00205, 1.00225] -> bins 20..22
    assert np.flatnonzero(psds[1].max(axis=1) > 0).tolist() == [0, 1, 2, 3, 4, 20, 21, 22]
    # hit 2 of channel 2 covers [1.0, 1.001 + float32 rounding] -> bins 0..10
    assert np.flatnonzero(psds[2].max(axis=1) > 0).tolist() == list(range(11))


def test_channel_psd_without_hits_is_zero(tmp_path: Path):
    hits = pd.DataFrame(
        {
            "time": [1.0],
            "channel": np.array([1], dtype=np.uint8),
            "duration": np.array([1e-3], dtype=np.float32),
            "pretrigger": np.array([0], dtype=np.uint32),
            "signal": [_sine(250_000.0, NPERSEG).astype(np.float32)],
        },
        index=pd.Index(np.array([1], dtype=np.uint32), name="trai"),
    )
    path = tmp_path / "x.hits.parquet"
    hits.to_parquet(path)
    psds = _channel_psds(path, [1, 2], SAMPLE_RATE, 0.0, 2.0, n_bins=10, max_duration=1e-3)
    assert set(psds) == {1, 2}
    assert np.all(psds[2] == 0)
    assert np.any(psds[1] > 0)


def test_channel_psds_only_hits_overlapping_range(tmp_path: Path):
    n = 4
    hits = pd.DataFrame(
        {
            "time": [0.5, 0.9995, 1.5, 2.5],
            "channel": np.array([1] * n, dtype=np.uint8),
            "duration": np.array([1e-3] * n, dtype=np.float32),
            "pretrigger": np.array([0] * n, dtype=np.uint32),
            "signal": [_sine(250_000.0, 4 * NPERSEG).astype(np.float32)] * n,
        },
        index=pd.Index(np.arange(1, n + 1, dtype=np.uint32), name="trai"),
    )
    path = tmp_path / "x.hits.parquet"
    # one row group per hit, so the time filter can skip row groups
    hits.to_parquet(path, row_group_size=1)

    psds = _channel_psds(path, [1], SAMPLE_RATE, 1.0, 2.0, n_bins=1000, max_duration=1e-3)

    # hit 2 ends at 1.0005 (bin 0), hit 3 covers [1.5, 1.501] (bin 500); hits 1 and 4 lie outside
    assert np.flatnonzero(psds[1].max(axis=1) > 0).tolist() == [0, 500]


# --- conventions (Package layout), 0004 R9: file names ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11:19 ruhe", "1119_ruhe"),
        ("13:46 Ende", "1346_Ende"),
        ('a:b/c\\d*e?f"g<h>i|j', "abcdefghij"),
        ("x  y\tz", "x__y_z"),
        ("v1.5 test", "v1.5_test"),
        ("11:35 alu körner", "1135_alu_körner"),
    ],
)
def test_sanitize_file_name(text, expected):
    assert _sanitize_file_name(text) == expected


# --- 0010 R5: LaTeX escaping ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain text 1", "plain text 1"),
        ("50% & more", r"50\% \& more"),
        ("a_b#c$d", r"a\_b\#c\$d"),
        ("{x}", r"\{x\}"),
        ("~^", r"\textasciitilde{}\textasciicircum{}"),
        ("a\\b", r"a\textbackslash{}b"),
    ],
)
def test_latex_escape(text, expected):
    assert _latex_escape(text) == expected
