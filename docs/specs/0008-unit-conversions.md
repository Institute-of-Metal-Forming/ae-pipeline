# 0008 Unit conversions

- **Status:** not implemented
- **Module:** `ae_pipeline/units.py` (`volts_to_microvolts`, `amplitude_to_dB`, `dB_to_amplitude`, `power_to_dB`)

## Summary

Central conversion functions between the units of the pipeline. All stored data (metadata, hits table) is linear: voltages in µV, power quantities in µV² or µV²/Hz. Levels in dB(AE) are only computed where they are shown, e.g. in plots, and always through these functions, so the dB(AE) definition (`docs/conventions.md`) lives in one place.

## Inputs

None. The module is a plain library module, not a task module (its name does not start with `task_`, so pytask does not collect it).

## Outputs

None.

## Parameters

None.

## Requirements

1. `volts_to_microvolts(u)` returns `u * 1e6`. It is used for every V → µV conversion of data read from the Vallen databases (waveforms, hit amplitudes, thresholds).

2. `amplitude_to_dB(u)` returns the level of an amplitude in µV in dB(AE): `20 * np.log10(np.abs(u) / 1 µV)`. Negative values give the level of their magnitude.

3. `dB_to_amplitude(level)` is the inverse of R2 for non-negative amplitudes: `10 ** (level / 20)` in µV.

4. `power_to_dB(p)` returns the level of a power quantity in µV² (or a density in µV²/Hz) in dB(AE) (or dB(AE)/Hz): `10 * np.log10(p / 1 µV²)`.

5. All functions accept a scalar or a NumPy array (and anything `np.asarray` accepts) and return a result of the same shape. The floating point dtype of an array input is kept, e.g. float32 stays float32.

6. A zero input to R2 or R4 gives `-inf` without emitting a NumPy `RuntimeWarning` (use `np.errstate(divide="ignore")`). The result is not clipped or replaced.

7. No other module converts units inline: there are no `1e6` factors for V → µV and no `log10` for levels outside this module.

8. The functions are covered by pytest tests in `tests/test_units.py`: known values (1 µV → 0 dB(AE), 1000 µV → 60 dB(AE), 100 µV² → 20 dB(AE), 1 V → 1e6 µV), round trip of R2 and R3, zero → `-inf` without warning, dtype preservation. pytest is added as a dev dependency with `uv add --dev pytest`.

## Open questions

None.
