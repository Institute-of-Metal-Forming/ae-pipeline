from pathlib import Path

import pytest
import tomli_w

from ae_pipeline.metadata import LabelInterval, Metadata, label_intervals, load_metadata


def _metadata(labels: dict[str, float]) -> Metadata:
    return Metadata.model_validate(
        {
            "general": {"clock_rate": 10_000_000, "sample_rate": 10_000_000},
            "channels": {"1": {"threshold": 28.9}, "2": {"threshold": 39.8}},
            "labels": labels,
        }
    )


def test_load_metadata(tmp_path: Path):
    document = {
        "general": {"clock_rate": 10_000_000, "sample_rate": 5_000_000},
        "channels": {"2": {"threshold": 28.9}, "1": {"threshold": 39.8}},
        "labels": {"11:19 ruhe": 0.0, "11:20 walze dreht": 57.7},
    }
    path = tmp_path / "x.metadata.toml"
    path.write_text(tomli_w.dumps(document))

    metadata = load_metadata(path)

    assert metadata.general.sample_rate == 5_000_000
    assert list(metadata.channels) == [2, 1]
    assert metadata.channels[1].threshold == pytest.approx(39.8)
    assert list(metadata.labels.items()) == [("11:19 ruhe", 0.0), ("11:20 walze dreht", 57.7)]


def test_label_intervals_between_consecutive_labels():
    metadata = _metadata({"a": 0.0, "b": 10.0, "c": 25.0})
    assert label_intervals(metadata, 1.0) == [LabelInterval("a", 0.0, 10.0), LabelInterval("b", 10.0, 25.0)]


def test_label_intervals_minimum_length():
    metadata = _metadata({"a": 0.0, "b": 1.0, "c": 1.5, "d": 4.0})
    assert label_intervals(metadata, 1.0) == [LabelInterval("a", 0.0, 1.0), LabelInterval("c", 1.5, 4.0)]
    assert label_intervals(metadata, 2.0) == [LabelInterval("c", 1.5, 4.0)]


def test_label_intervals_skip_suspend():
    metadata = _metadata({"13:38 Resume": 0.0, "13:40 Suspend": 10.0, "13:45 Resume": 20.0, "13:47 Ende": 30.0})
    assert label_intervals(metadata, 1.0) == [
        LabelInterval("13:38 Resume", 0.0, 10.0),
        LabelInterval("13:45 Resume", 20.0, 30.0),
    ]


def test_label_intervals_last_label_starts_no_interval():
    metadata = _metadata({"a": 0.0, "b": 10.0})
    intervals = label_intervals(metadata, 0.0)
    assert [i.label for i in intervals] == ["a"]


@pytest.mark.parametrize("labels", [{}, {"a": 0.0}])
def test_label_intervals_fewer_than_two_labels(labels):
    assert label_intervals(_metadata(labels), 0.0) == []


def test_serialized_metadata_keeps_document_layout(tmp_path: Path):
    metadata = _metadata({"11:19 ruhe": 0.0, "11:20 walze dreht": 57.7, "a": 60.0})
    text = tomli_w.dumps(metadata.model_dump(mode="json"))

    assert "[channels.1]" in text
    assert text.index("[general]") < text.index("[channels.1]") < text.index("[labels]")
    path = tmp_path / "x.metadata.toml"
    path.write_text(text)
    assert load_metadata(path) == metadata
    assert list(load_metadata(path).labels) == ["11:19 ruhe", "11:20 walze dreht", "a"]
