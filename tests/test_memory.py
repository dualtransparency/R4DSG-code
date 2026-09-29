import copy
import json

import pytest

from r4dsg.memory import Config, build_memory
from r4dsg.schema import parse_frames


def build(rows, **kwargs):
    return build_memory(parse_frames(rows), Config(window_seconds=20), **kwargs)


def test_stable_transition_and_windows(frames_data):
    result = build(frames_data)
    assert len(result["tracks"]) == 3
    assert len(result["documents"]) == 2
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert (event["source_anchor"], event["destination_anchor"]) == ("shelf", "table")
    assert (event["start"], event["end"], event["confirmed_at"]) == (10, 20, 30)
    assert any("Transition: cup" in doc["text"] for doc in result["documents"])


def test_no_transition_variant_has_only_local_relations(frames_data):
    result = build(frames_data, transitions=False)
    assert result["tracks"] == result["events"] == []
    assert "track_id" not in json.dumps(result["documents"])
    assert "source_anchor" not in json.dumps(result["documents"])
    assert "cup on shelf" in result["documents"][0]["relations"]


def test_single_change_is_not_stable(frames_data):
    result = build(frames_data[:3])
    assert not result["events"]


def test_permutation_is_deterministic(frames_data):
    expected = build(frames_data)
    frames_data.reverse()
    for frame in frames_data:
        frame["objects"].reverse()
    assert build(frames_data) == expected


def test_similar_objects_do_not_share_a_track(frames_data):
    for frame in frames_data:
        duplicate = copy.deepcopy(frame["objects"][2])
        duplicate["local_id"] = "duplicate"
        frame["objects"].append(duplicate)
    result = build(frames_data)
    for track in result["tracks"]:
        frame_ids = [o["frame_id"] for o in track["observations"]]
        assert len(frame_ids) == len(set(frame_ids))
    assert not result["events"]


def test_separate_streams_never_link(frames_data):
    other = copy.deepcopy(frames_data)
    for frame in other:
        frame["stream_id"] = "other-session"
    result = build(frames_data + other)
    assert len(result["tracks"]) == 6
    assert len(result["events"]) == 2


def test_unknown_coordinate_alignment_does_not_link(frames_data):
    for frame in frames_data:
        frame["coordinate_frame"] = frame["frame_id"]
    assert len(build(frames_data)["tracks"]) == 12
    assert not build(frames_data)["events"]


def test_visual_instance_keys_can_link_across_local_coordinates(frames_data):
    for frame in frames_data:
        frame["coordinate_frame"] = frame["frame_id"]
        for obj in frame["objects"]:
            obj["instance_key"] = obj["local_id"]
            obj["anchor_candidate"] = obj["label"] in {"shelf", "table"}
    assert len(build(frames_data)["events"]) == 1


def test_long_gaps_split_tracks(frames_data):
    frames_data[2]["timestamp"] = 200
    frames_data[3]["timestamp"] = 210
    assert not build(frames_data)["events"]


def test_ambiguous_support_does_not_write_event(frames_data):
    for frame in frames_data[2:]:
        frame["relations"].append({"subject": "c", "predicate": "on", "object": "s"})
    assert not build(frames_data)["events"]


@pytest.mark.parametrize(
    "field",
    ["answer", "options", "choice_a", "reason", "rationale", "object_mentions", "why_fields"],
)
def test_unexpected_annotation_fields_rejected(frames_data, field):
    frames_data[0][field] = "not an observation"
    with pytest.raises(ValueError):
        build(frames_data)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "20"])
def test_invalid_timestamp_rejected(frames_data, value):
    frames_data[0]["timestamp"] = value
    with pytest.raises(ValueError):
        build(frames_data)


def test_duplicate_frames_rejected(frames_data):
    with pytest.raises(ValueError):
        build(frames_data + frames_data[:1])


def test_invalid_relation_rejected(frames_data):
    frames_data[0]["relations"][0]["object"] = "absent"
    with pytest.raises(ValueError):
        build(frames_data)


def test_missing_geometry_is_not_zero_geometry(frames_data):
    for frame in frames_data:
        for obj in frame["objects"]:
            obj.pop("position")
    result = build(frames_data)
    assert not result["events"]
    assert len(result["tracks"]) == 12


@pytest.mark.parametrize(
    "cfg",
    [
        {"stable_observations": 1},
        {"stable_observations": 2.5},
        {"window_seconds": 0},
        {"max_track_gap": True},
    ],
)
def test_invalid_config(cfg):
    with pytest.raises(ValueError):
        Config(**cfg)
