import numpy as np
import pytest

from ae_pipeline.spectral import HOP, NPERSEG, psd_frequencies, short_time_fft, welch_psd

SAMPLE_RATE = 10_000_000


def _sine(frequency: float, n: int) -> np.ndarray:
    return np.sin(2 * np.pi * frequency * np.arange(n) / SAMPLE_RATE)


def test_psd_frequencies():
    f = psd_frequencies(SAMPLE_RATE)
    assert len(f) == NPERSEG // 2 + 1
    assert f[0] == 0
    assert f[-1] == pytest.approx(SAMPLE_RATE / 2)


def test_welch_psd_maximum_at_sine_frequency():
    frequency = 250_000.0
    psd = welch_psd(_sine(frequency, 20 * NPERSEG), SAMPLE_RATE)
    f = psd_frequencies(SAMPLE_RATE)
    assert len(psd) == len(f)
    assert abs(f[np.argmax(psd)] - frequency) <= f[1]


def test_welch_psd_pads_short_signals():
    psd = welch_psd(_sine(250_000.0, NPERSEG // 3), SAMPLE_RATE)
    assert psd.shape == (NPERSEG // 2 + 1,)


def test_welch_psd_is_float64_for_float32_input():
    psd = welch_psd(_sine(250_000.0, 4 * NPERSEG).astype(np.float32), SAMPLE_RATE)
    assert psd.dtype == np.float64


def test_welch_psd_of_zero_signal_is_zero():
    psd = welch_psd(np.zeros(4 * NPERSEG), SAMPLE_RATE)
    assert np.all(psd == 0)


@pytest.mark.parametrize("n", [100, NPERSEG, 10 * NPERSEG + 17])
def test_short_time_fft_columns(n):
    stft = short_time_fft(SAMPLE_RATE)
    spectrogram = stft.spectrogram(_sine(250_000.0, n).astype(np.float32))
    n_columns = spectrogram.shape[1]
    assert spectrogram.shape[0] == NPERSEG // 2 + 1
    assert n_columns >= 1
    assert spectrogram.dtype == np.float64
    # column k is centered at k * HOP / sample_rate
    assert stft.p_min == 0
    assert stft.delta_t == pytest.approx(HOP / SAMPLE_RATE)
    # the columns cover the whole signal and every column overlaps it
    last_center = (n_columns - 1) * HOP
    assert last_center + NPERSEG // 2 >= n
    assert last_center - NPERSEG // 2 < n


def test_short_time_fft_maximum_at_sine_frequency():
    frequency = 1_000_000.0
    spectrogram = short_time_fft(SAMPLE_RATE).spectrogram(_sine(frequency, 20 * NPERSEG))
    f = psd_frequencies(SAMPLE_RATE)
    inner = spectrogram[:, 2:-2]
    assert np.all(np.abs(f[np.argmax(inner, axis=0)] - frequency) <= f[1])


def test_short_time_fft_matches_welch_psd():
    rng = np.random.default_rng(0)
    signal = rng.normal(size=200 * NPERSEG)
    spectrogram = short_time_fft(SAMPLE_RATE).spectrogram(signal)
    # inner columns only: the first and last columns are partly zero-padded; welch removes the mean (lowest bins)
    np.testing.assert_allclose(spectrogram[:, 2:-2].mean(axis=1)[2:-1], welch_psd(signal, SAMPLE_RATE)[2:-1], rtol=0.05)
