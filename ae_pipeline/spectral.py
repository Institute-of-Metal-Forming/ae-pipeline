"""Spectral analysis settings and the functions that apply them (spec 0009).

The Welch PSD of the hits (0003) and the STFT spectrograms of the waterfall plots (0004) use the same window, segment
length and hop, so their results are comparable.
"""

import numpy as np
import scipy.signal as sig
from numpy.typing import ArrayLike

NPERSEG = 2048
"""Segment length and FFT length in samples."""

HOP = NPERSEG // 2
"""Segment shift in samples (50 % overlap)."""

WINDOW = "hann"
"""Window, as accepted by ``scipy.signal``."""


def psd_frequencies(sample_rate: float) -> np.ndarray:
    """Frequencies in Hz of a PSD or spectrogram column, ``NPERSEG // 2 + 1`` values from 0 to Nyquist."""
    return np.fft.rfftfreq(NPERSEG, 1 / sample_rate)


def welch_psd(signal: ArrayLike, sample_rate: float) -> np.ndarray:
    """Welch PSD of ``signal`` (µV) in µV²/Hz at the frequencies of :func:`psd_frequencies`.

    Signals shorter than ``NPERSEG`` samples are zero-padded at the end. Computed in float64.
    """
    x = np.asarray(signal, dtype=np.float64)
    if len(x) < NPERSEG:
        x = np.pad(x, (0, NPERSEG - len(x)))
    _, psd = sig.welch(x, sample_rate, window=WINDOW, nperseg=NPERSEG, noverlap=NPERSEG - HOP)
    return psd


class _Float64ShortTimeFFT(sig.ShortTimeFFT):
    """``ShortTimeFFT`` for 1-d signals that converts its input to float64 before the transform.

    ``scipy`` rejects signals shorter than half a segment. These are zero-padded at the end to that length, so every
    signal gets at least one column. The padding adds no column, because all columns of the padded signal still
    overlap the original samples.
    """

    def _prepare(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        min_length = self.m_num - self.m_num_mid
        if x.ndim == 1 and len(x) < min_length:
            x = np.pad(x, (0, min_length - len(x)))
        return x

    def stft(self, x, *args, **kwargs):
        return super().stft(self._prepare(x), *args, **kwargs)

    def spectrogram(self, x, *args, **kwargs):
        if kwargs.get("y") is not None:
            kwargs["y"] = self._prepare(kwargs["y"])
        return super().spectrogram(self._prepare(x), *args, **kwargs)


def short_time_fft(sample_rate: float) -> sig.ShortTimeFFT:
    """STFT with ``WINDOW``, ``NPERSEG`` and ``HOP`` whose ``spectrogram`` gives the PSD per column in µV²/Hz.

    The one-sided spectrum doubles the non-DC bins (``fft_mode="onesided2X"``), like :func:`welch_psd`, so both give
    the same power spectral density. Column ``k`` is centered at ``k * HOP / sample_rate`` from the signal start.
    The input is converted to float64.
    """
    window = sig.get_window(WINDOW, NPERSEG)
    return _Float64ShortTimeFFT(
        window,
        hop=HOP,
        fs=sample_rate,
        fft_mode="onesided2X",
        mfft=NPERSEG,
        scale_to="psd",
    )
