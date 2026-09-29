"""Strict, observation-only input schema. Times are seconds within a named stream."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any


def fields(value: Any, required: set[str], optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    if not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ValueError("Missing or unsupported schema fields; see docs/SCHEMA.md")
    return value


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a non-empty string")
    return value.strip()


def number(value: Any, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected a finite number")
    if not math.isfinite(value) or value < minimum:
        raise ValueError("Number outside permitted range")
    return float(value)


def vector(value: Any, *, positive: bool = False) -> tuple[float, float, float] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("Expected a three-element vector")
    result = tuple(number(v, 0 if positive else -math.inf) for v in value)
    if positive and any(v == 0 for v in result):
        raise ValueError("Sizes must be positive")
    return result


@dataclass(frozen=True)
class Observation:
    local_id: str
    label: str
    position: tuple[float, float, float] | None = None
    size: tuple[float, float, float] | None = None
    state: str | None = None
    instance_key: str | None = None
    anchor_candidate: bool = False

    @classmethod
    def parse(cls, value: dict) -> Observation:
        v = fields(
            value,
            {"local_id", "label"},
            {"position", "size", "state", "instance_key", "anchor_candidate"},
        )
        anchor = v.get("anchor_candidate", False)
        if not isinstance(anchor, bool):
            raise ValueError("anchor_candidate must be boolean")
        return cls(
            text(v["local_id"]),
            text(v["label"]),
            vector(v.get("position")),
            vector(v.get("size"), positive=True),
            text(v["state"]) if v.get("state") is not None else None,
            text(v["instance_key"]) if v.get("instance_key") is not None else None,
            anchor,
        )


@dataclass(frozen=True)
class Relation:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0

    @classmethod
    def parse(cls, value: dict) -> Relation:
        v = fields(value, {"subject", "predicate", "object"}, {"confidence"})
        confidence = number(v.get("confidence", 1))
        if confidence > 1:
            raise ValueError("Confidence exceeds one")
        return cls(text(v["subject"]), text(v["predicate"]), text(v["object"]), confidence)


@dataclass(frozen=True)
class Frame:
    frame_id: str
    stream_id: str
    timestamp: float
    coordinate_frame: str
    location: str
    activity: str
    objects: tuple[Observation, ...]
    relations: tuple[Relation, ...] = ()

    @classmethod
    def parse(cls, value: dict) -> Frame:
        v = fields(
            value,
            {
                "frame_id",
                "stream_id",
                "timestamp",
                "coordinate_frame",
                "location",
                "activity",
                "objects",
            },
            {"relations"},
        )
        if not isinstance(v["objects"], list) or not isinstance(v.get("relations", []), list):
            raise ValueError("objects and relations must be lists")
        objects = tuple(Observation.parse(o) for o in v["objects"])
        ids = [o.local_id for o in objects]
        keys = [o.instance_key for o in objects if o.instance_key]
        if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
            raise ValueError("Duplicate object identifiers in a frame")
        relations = tuple(Relation.parse(r) for r in v.get("relations", []))
        if any(r.subject not in ids or r.object not in ids for r in relations):
            raise ValueError("Relation references an absent object")
        return cls(
            text(v["frame_id"]),
            text(v["stream_id"]),
            number(v["timestamp"]),
            text(v["coordinate_frame"]),
            text(v["location"]),
            text(v["activity"]),
            objects,
            relations,
        )


def parse_frames(value: Any) -> list[Frame]:
    if not isinstance(value, list) or not value:
        raise ValueError("Expected a non-empty list of frames")
    frames = [Frame.parse(v) for v in value]
    ids = [(f.stream_id, f.frame_id) for f in frames]
    times = [(f.stream_id, f.timestamp) for f in frames]
    if len(set(ids)) != len(ids) or len(set(times)) != len(times):
        raise ValueError("Duplicate frame or timestamp within a stream; merge views first")
    return sorted(frames, key=lambda f: (f.stream_id, f.timestamp, f.frame_id))


def serialize(value: Any) -> dict:
    return json.loads(json.dumps(asdict(value), allow_nan=False))
