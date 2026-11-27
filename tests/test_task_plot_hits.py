import numpy as np
import pytest

from ae_pipeline.plots.task_plot_hits import MAX_POINTS, _level_envelope

SAMPLE_RATE = 10_000_000


# --- 0006 R2.1: level envelope ---


def test_max_points():
    assert MAX_POINTS == 10_000


@pytest.mark.parametrize("n", [1, 2016, MAX_POINTS])
def test_short_records_unchanged(n):
    level = np.random.default_rng(0).normal(size=n)
    times, envelope = _level_envelope(level, SAMPLE_RATE)
    np.testing.assert_array_equal(envelope, level)
    np.testing.assert_allclose(times, np.arange(n) / SAMPLE_RATE)


@pytest.mark.parametrize("n", [MAX_POINTS + 1, 25_001, 1_048_579])
def test_long_records_block_maximum(n):
    level = np.random.default_rng(1).normal(size=n)
    times, envelope = _level_envelope(level, SAMPLE_RATE)

    w = -(-n // MAX_POINTS)  # ceil
    starts = np.arange(0, n, w)
    assert len(envelope) <= MAX_POINTS
    assert len(envelope) == len(starts)
    np.testing.assert_allclose(times, starts / SAMPLE_RATE)
    expected = np.array([level[s : s + w].max() for s in starts])  # last block may be shorter
    np.testing.assert_array_equal(envelope, expected)


def test_envelope_keeps_minus_inf_blocks():
    # zero samples have a level of -inf; a block of only zeros stays -inf, a mixed block takes the finite maximum
    level = np.full(MAX_POINTS * 2, -np.inf)
    level[5] = 20.0
    _, envelope = _level_envelope(level, SAMPLE_RATE)
    assert envelope[2] == 20.0
    assert np.isneginf(envelope[0])
