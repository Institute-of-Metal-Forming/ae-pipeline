# 0009 Spectral configuration

- **Status:** implemented
- **Module:** `ae_pipeline/spectral.py` (`NPERSEG`, `HOP`, `WINDOW`, `psd_frequencies`, `welch_psd`, `short_time_fft`)

## Summary

One place for the spectral analysis settings and the functions that apply them. The Welch PSD of the hit characterization (0003) and the STFT spectrograms of the waterfall plots (0004) use the same window, segment length and hop, so their results are comparable by construction.

## Inputs

None. The module is a plain library module, not a task module.

## Outputs

None.

## Parameters

| Name      | Value                 | Meaning                                |
| --------- | --------------------- | -------------------------------------- |
| `NPERSEG` | 2048                  | segment length and FFT length, samples |
| `HOP`     | `NPERSEG // 2` = 1024 | segment shift, samples (50 % overlap)  |
| `WINDOW`  | `"hann"`              | window, as accepted by `scipy.signal`  |

## Requirements

1. `psd_frequencies(sample_rate)` returns the frequencies in Hz of a PSD or spectrogram column: `np.fft.rfftfreq(NPERSEG, 1 / sample_rate)`, `NPERSEG // 2 + 1` values from 0 to the Nyquist frequency.

2. `welch_psd(signal, sample_rate)` returns the Welch PSD of `signal` (µV) in µV²/Hz, `scipy.signal.welch(signal, sample_rate, window=WINDOW, nperseg=NPERSEG, noverlap=NPERSEG - HOP)`, at the frequencies of R1. Signals shorter than `NPERSEG` samples are zero-padded at the end to `NPERSEG` samples first, so the result always has `NPERSEG // 2 + 1` values. The computation is done in float64, whatever the input dtype.

3. `short_time_fft(sample_rate)` returns a `scipy.signal.ShortTimeFFT` with `WINDOW`, `NPERSEG`, `HOP`, the given sample rate, `fft_mode="onesided2X"` and `scale_to="psd"`. `onesided2X` doubles the non-DC bins like the Welch PSD, so a spectrogram column of a stationary signal equals its Welch PSD (R2); the scipy default `onesided` would give half of it. Its `spectrogram(signal)` gives the PSD per column in µV²/Hz at the frequencies of R1, and column `k` is centered at `k * HOP / sample_rate` from the start of the signal. The input is converted to float64 first, as in R2. `ShortTimeFFT` rejects signals shorter than `NPERSEG - NPERSEG // 2` = 1024 samples, so its `stft` and `spectrogram` (e.g. in a `ShortTimeFFT` subclass) zero-pad such signals at the end to that length first; this adds no column, and every signal gets at least one column.

4. All other modules take these settings and functions from here; no other module defines a segment length, hop or window for spectral analysis.

5. Tasks that use this module declare `ae_pipeline/spectral.py` as a dependency (see `docs/conventions.md`, Tasks), so a change of the settings rebuilds their products.

6. The functions are covered by pytest tests in `tests/test_spectral.py` with synthetic signals: the PSD of a sine has its maximum at the sine frequency (within one frequency bin), a short signal is padded to `NPERSEG // 2 + 1` values, the number and centers of the STFT columns match R3, and the PSD of a constant zero signal is zero.

## Open questions

None.
