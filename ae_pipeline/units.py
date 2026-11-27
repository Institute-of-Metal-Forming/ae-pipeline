"""Central unit conversions of the pipeline (spec 0008).

All stored data is linear (voltages in µV, power quantities in µV² or µV²/Hz). Levels in dB(AE), i.e. relative to
1 µV, are computed only where they are shown, always through these functions.
"""

from typing import Any

import numpy as np

MICROVOLTS_PER_VOLT = 1e6
"""Factor from V to µV."""

HZ_PER_KHZ = 1e3
"""Factor from kHz to Hz."""

REFERENCE_AMPLITUDE = 1.0
"""Reference amplitude of dB(AE) in µV."""

REFERENCE_POWER = REFERENCE_AMPLITUDE**2
"""Reference power of dB(AE) in µV²."""


def _as_float_array(x: Any) -> np.ndarray:
    """Convert to an array, keeping floating point dtypes and promoting everything else to float64."""
    a = np.asarray(x)
    if not np.issubdtype(a.dtype, np.floating):
        a = a.astype(np.float64)
    return a


def _result(a: np.ndarray, x: Any) -> Any:
    """Return a NumPy scalar for scalar inputs and the array otherwise."""
    return a[()] if np.ndim(x) == 0 else a


def volts_to_microvolts(u: Any) -> Any:
    """Convert a voltage from V to µV."""
    a = _as_float_array(u)
    return _result(a * a.dtype.type(MICROVOLTS_PER_VOLT), u)


def amplitude_to_dB(u: Any) -> Any:
    """Level of an amplitude in µV in dB(AE), ``20 * log10(|u| / 1 µV)``. Zero gives ``-inf``."""
    a = _as_float_array(u)
    with np.errstate(divide="ignore"):
        level = a.dtype.type(20) * np.log10(np.abs(a) / a.dtype.type(REFERENCE_AMPLITUDE))
    return _result(level, u)


def dB_to_amplitude(level: Any) -> Any:
    """Amplitude in µV of a level in dB(AE), the inverse of :func:`amplitude_to_dB` for non-negative amplitudes."""
    a = _as_float_array(level)
    return _result(a.dtype.type(REFERENCE_AMPLITUDE) * a.dtype.type(10) ** (a / a.dtype.type(20)), level)


def power_to_dB(p: Any) -> Any:
    """Level of a power quantity in µV² (or density in µV²/Hz) in dB(AE) (or dB(AE)/Hz). Zero gives ``-inf``."""
    a = _as_float_array(p)
    with np.errstate(divide="ignore"):
        level = a.dtype.type(10) * np.log10(a / a.dtype.type(REFERENCE_POWER))
    return _result(level, p)


def hz_to_khz(f: Any) -> Any:
    """Convert a frequency from Hz to kHz."""
    a = _as_float_array(f)
    return _result(a / a.dtype.type(HZ_PER_KHZ), f)
