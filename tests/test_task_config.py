import shutil
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

import ae_pipeline.task_config as task_config
from ae_pipeline.task_config import Dataset, _discover_datasets, image_produces


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


# --- 0001 Dataset discovery ---


def test_discover_datasets_pairs_and_skips_unpaired(tmp_path: Path):
    _touch(tmp_path / "a.pridb")
    _touch(tmp_path / "a.tradb")
    _touch(tmp_path / "only_pridb.pridb")
    _touch(tmp_path / "only_tradb.tradb")
    _touch(tmp_path / "_trash" / "hidden.pridb")
    _touch(tmp_path / "_trash" / "hidden.tradb")

    with pytest.warns(UserWarning) as record:
        datasets = _discover_datasets(tmp_path)

    assert [ds.name for ds in datasets] == ["a"]
    messages = [str(w.message) for w in record]
    assert any("only_pridb.pridb" in m for m in messages)  # R4
    assert any("only_tradb.tradb" in m for m in messages)  # R6
    assert len(messages) == 2  # R7: nothing about files in _trash/


def test_discover_datasets_without_unpaired_files_does_not_warn(tmp_path: Path):
    _touch(tmp_path / "a.pridb")
    _touch(tmp_path / "a.tradb")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        datasets = _discover_datasets(tmp_path)
    assert len(datasets) == 1


def test_dataset_derived_paths(tmp_path: Path):
    primary = _touch(tmp_path / "2026-11-26-walzen1.pridb")
    _touch(tmp_path / "2026-11-26-walzen1.tradb")
    ds = Dataset(primary_file=primary)
    assert ds.name == "2026-11-26-walzen1"
    assert ds.transient_file == tmp_path / "2026-11-26-walzen1.tradb"
    assert ds.hits_file == tmp_path / "2026-11-26-walzen1.hits.parquet"
    assert ds.metadata_file == tmp_path / "2026-11-26-walzen1.metadata.toml"


def test_dataset_missing_transient_file_raises(tmp_path: Path):
    primary = _touch(tmp_path / "a.pridb")
    with pytest.raises(ValueError, match="transient file"):
        Dataset(primary_file=primary)


def test_dataset_missing_primary_file_raises(tmp_path: Path):
    _touch(tmp_path / "a.tradb")
    with pytest.raises(ValueError, match="primary file"):
        Dataset(primary_file=tmp_path / "a.pridb")


def test_no_debug_flag():
    # 0001 R8
    assert not hasattr(task_config, "DEBUG")
    assert isinstance(task_config.EACH_HIT, bool)


# --- 0010 Plot configuration ---


def test_plot_formats_default():
    assert task_config.PLOT_FORMATS == ["png"]


def test_image_produces_appends_suffix_to_dotted_names(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(task_config, "PLOT_FORMATS", ["png", "pdf"])
    base = Path("/plots/ds/waterfall/v1.5_test")
    assert image_produces(base) == [
        Path("/plots/ds/waterfall/v1.5_test.png"),
        Path("/plots/ds/waterfall/v1.5_test.pdf"),
    ]


def test_image_produces_default_format():
    assert image_produces(Path("/plots/ds/waterfall")) == [Path("/plots/ds/waterfall.png")]


def test_latex_preamble():
    assert mpl.rcParams["text.usetex"] is True
    preamble = mpl.rcParams["text.latex.preamble"]
    assert r"\usepackage{siunitx}" in preamble
    assert "per-mode = symbol" in preamble
    assert r"\DeclareSIUnit\dBAE{\decibel\of{AE}}" in preamble


@pytest.mark.skipif(shutil.which("latex") is None or shutil.which("dvipng") is None, reason="no TeX toolchain")
def test_latex_units_render(tmp_path: Path):
    # 0010 R3–R6: the preamble compiles and the units used by the plots render
    fig, ax = plt.subplots()
    ax.set_xlabel(r"Frequency in \unit{\kilo\hertz}")
    ax.set_ylabel(r"Power Spectral Density in \unit{\micro\volt\squared\per\hertz}")
    ax.set_title(r"Power Spectral Density in \unit{\dBAE\per\hertz}, Intensity in \unit{\dBAE}")
    path = tmp_path / "units.png"
    fig.savefig(path, dpi=50)
    plt.close(fig)
    assert path.stat().st_size > 0
