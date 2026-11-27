import warnings

import numpy as np
import pytest

from ae_pipeline.units import amplitude_to_dB, dB_to_amplitude, hz_to_khz, power_to_dB, volts_to_microvolts


def test_known_values():
    assert amplitude_to_dB(1.0) == pytest.approx(0.0)
    assert amplitude_to_dB(1000.0) == pytest.approx(60.0)
    assert power_to_dB(100.0) == pytest.approx(20.0)
    assert volts_to_microvolts(1.0) == pytest.approx(1e6)
    assert dB_to_amplitude(60.0) == pytest.approx(1000.0)
    assert hz_to_khz(1000.0) == pytest.approx(1.0)


def test_negative_amplitude_gives_level_of_magnitude():
    assert amplitude_to_dB(-1000.0) == pytest.approx(60.0)


def test_amplitude_round_trip():
    u = np.array([1e-3, 0.5, 1.0, 39.81, 1e4])
    np.testing.assert_allclose(dB_to_amplitude(amplitude_to_dB(u)), u)
    level = np.array([-20.0, 0.0, 32.0, 100.0])
    np.testing.assert_allclose(amplitude_to_dB(dB_to_amplitude(level)), level)


@pytest.mark.parametrize("func", [amplitude_to_dB, power_to_dB])
def test_zero_gives_minus_inf_without_warning(func):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert func(0.0) == -np.inf
        result = func(np.array([0.0, 1.0]))
    assert result[0] == -np.inf
    assert result[1] == 0.0


@pytest.mark.parametrize("func", [volts_to_microvolts, amplitude_to_dB, dB_to_amplitude, power_to_dB, hz_to_khz])
@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_dtype_and_shape_preserved(func, dtype):
    x = np.ones((2, 3), dtype=dtype)
    result = func(x)
    assert result.dtype == dtype
    assert result.shape == x.shape


@pytest.mark.parametrize("func", [volts_to_microvolts, amplitude_to_dB, dB_to_amplitude, power_to_dB, hz_to_khz])
def test_scalar_and_list_inputs(func):
    assert np.ndim(func(2.0)) == 0
    assert np.ndim(func(2)) == 0
    assert np.shape(func([1.0, 2.0])) == (2,)
