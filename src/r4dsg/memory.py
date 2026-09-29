"""Conservative tracking, stable anchor changes, and windowed memory writing."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from r4dsg.schema import Frame, Observation

ANCHOR_LABELS = {"table", "desk", "shelf", "counter", "sofa", "drawer", "fridge", "door", "wall"}
SUPPORT_RELATIONS = {"on", "in", "inside", "under", "against", "atop", "supported_by"}


@dataclass(frozen=True)
class Config:
    window_seconds: float = 60.0
    max_track_gap: float = 30.0
    match_distance: float = 1.5
    size_tolerance: float = 0.5
    ambiguity_margin: float = 0.05
    static_motion: float = 0.1
    anchor_distance: float = 2.0
    stable_observations: int = 2

    def __post_init__(self) -> None:
        for key, value in asdict(self).items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"Invalid positive configuration value: {key}")
        if not isinstance(self.stable_observations, int) or self.stable_observations < 2:
            raise ValueError("stable_observations must be an integer >= 2")


@dataclass
class Track:
    track_id: str
    label: str
    observations: list[tuple[Frame, Observation]] = field(default_factory=list)
    is_anchor: bool = False


def distance(a: tuple, b: tuple) -> float:
    return math.dist(a, b)


def size_distance(a: tuple | None, b: tuple | None) -> float:
    if a is None or b is None:
        return 0.0
    return sum(abs(x - y) / max(x, y) for x, y in zip(a, b)) / 3


def match_score(frame: Frame, obj: Observation, track: Track, cfg: Config) -> float | None:
    previous, seen = track.observations[-1]
    if frame.stream_id != previous.stream_id or obj.label.casefold() != track.label.casefold():
        return None
    if not 0 < frame.timestamp - previous.timestamp <= cfg.max_track_gap:
        return None
    if obj.instance_key or seen.instance_key:
        return 0.0 if obj.instance_key and obj.instance_key == seen.instance_key else None
    if frame.coordinate_frame != previous.coordinate_frame or frame.location != previous.location:
        return None
    if obj.position is None or seen.position is None:
        return None
    d = distance(obj.position, seen.position)
    s = size_distance(obj.size, seen.size)
    return d + s if d <= cfg.match_distance and s <= cfg.size_tolerance else None


def associate(frames: list[Frame], cfg: Config) -> tuple[list[Track], dict]:
    tracks: list[Track] = []
    assignment: dict[tuple[str, str, str], str] = {}
    for frame in frames:
        candidates: dict[str, list[tuple[float, str]]] = defaultdict(list)
        reverse: dict[str, list[tuple[float, str]]] = defaultdict(list)
        for obj in frame.objects:
            for track in tracks:
                score = match_score(frame, obj, track, cfg)
                if score is not None:
                    candidates[obj.local_id].append((score, track.track_id))
                    reverse[track.track_id].append((score, obj.local_id))
        eligible = []
        for local_id, matches in candidates.items():
            matches.sort()
            score, track_id = matches[0]
            competing = sorted(reverse[track_id])
            if len(matches) > 1 and matches[1][0] - score < cfg.ambiguity_margin:
                continue
            if competing[0][1] != local_id or (
                len(competing) > 1 and competing[1][0] - score < cfg.ambiguity_margin
            ):
                continue
            eligible.append((score, local_id, track_id))
        matched = {local_id: tid for _, local_id, tid in sorted(eligible)}
        by_id = {t.track_id: t for t in tracks}
        for obj in sorted(frame.objects, key=lambda o: o.local_id):
            tid = matched.get(obj.local_id)
            if tid is None:
                tid = f"T{len(tracks) + 1:06d}"
                track = Track(tid, obj.label)
                tracks.append(track)
                by_id[tid] = track
            by_id[tid].observations.append((frame, obj))
            assignment[(frame.stream_id, frame.frame_id, obj.local_id)] = tid
    for track in tracks:
        obs = track.observations
        candidate = track.label.casefold() in ANCHOR_LABELS or all(
            o.anchor_candidate for _, o in obs
        )
        if not candidate or len(obs) < cfg.stable_observations:
            continue
        pairs = [
            (a, b)
            for (fa, a), (fb, b) in zip(obs, obs[1:])
            if fa.coordinate_frame == fb.coordinate_frame
            and a.position is not None
            and b.position is not None
        ]
        measured_static = len(pairs) == len(obs) - 1 and all(
            distance(a.position, b.position) <= cfg.static_motion for a, b in pairs
        )
        explicitly_static = all(o.anchor_candidate and o.instance_key for _, o in obs)
        track.is_anchor = bool(measured_static or explicitly_static)
    return tracks, assignment


def dominant_anchor(
    frame: Frame, obj: Observation, assignment: dict, anchors: set[str], cfg: Config
) -> str | None:
    def tid(local_id: str) -> str:
        return assignment[(frame.stream_id, frame.frame_id, local_id)]

    support = {}
    for relation in frame.relations:
        anchor = tid(relation.object)
        if (
            relation.subject == obj.local_id
            and relation.predicate.casefold() in SUPPORT_RELATIONS
            and anchor in anchors
            and relation.confidence >= 0.5
        ):
            support[anchor] = max(support.get(anchor, 0), relation.confidence)
    if support:
        ranked = sorted(support, key=lambda key: (-support[key], key))
        if len(ranked) > 1 and support[ranked[0]] - support[ranked[1]] < cfg.ambiguity_margin:
            return None
        return ranked[0]
    if obj.position is None:
        return None
    nearby = sorted(
        (distance(obj.position, other.position), tid(other.local_id))
        for other in frame.objects
        if tid(other.local_id) in anchors and other.position is not None
    )
    if not nearby or nearby[0][0] > cfg.anchor_distance:
        return None
    if len(nearby) > 1 and nearby[1][0] - nearby[0][0] < cfg.ambiguity_margin:
        return None
    return nearby[0][1]


def write_events(tracks: list[Track], assignment: dict, cfg: Config) -> list[dict]:
    anchors = {t.track_id for t in tracks if t.is_anchor}
    labels = {t.track_id: t.label for t in tracks}
    events = []
    for track in tracks:
        if track.is_anchor:
            continue
        stable, pending = None, None
        pending_count = 0
        pending_start = last_support = 0.0
        for frame, obj in track.observations:
            anchor = dominant_anchor(frame, obj, assignment, anchors, cfg)
            if anchor is None:
                pending, pending_count = None, 0
                if frame.timestamp - last_support > cfg.max_track_gap:
                    stable = None
                continue
            if anchor == stable:
                last_support = frame.timestamp
                pending, pending_count = None, 0
                continue
            if pending != anchor:
                pending, pending_count, pending_start = anchor, 0, frame.timestamp
            pending_count += 1
            if pending_count < cfg.stable_observations:
                continue
            if stable is not None and pending_start - last_support <= cfg.max_track_gap:
                events.append(
                    {
                        "event_id": f"E{len(events) + 1:06d}",
                        "stream_id": frame.stream_id,
                        "track_id": track.track_id,
                        "object": track.label,
                        "source_anchor_id": stable,
                        "source_anchor": labels[stable],
                        "destination_anchor_id": anchor,
                        "destination_anchor": labels[anchor],
                        "start": last_support,
                        "end": pending_start,
                        "confirmed_at": frame.timestamp,
                    }
                )
            stable, last_support, pending, pending_count = anchor, frame.timestamp, None, 0
    return events


def document_text(doc: dict) -> str:
    lines = [
        f"Time: {doc['stream_id']} {doc['start']:g}-{doc['end']:g} seconds.",
        "Location: " + "; ".join(doc["locations"]),
        "Activity: " + "; ".join(doc["activities"]),
    ]
    for obj in doc["objects"]:
        parts = [obj["label"]]
        if obj.get("track_id"):
            parts.append("id=" + obj["track_id"])
        if obj["state"]:
            parts.append("state=" + obj["state"])
        if obj["position"] is not None:
            parts.append("local_position=" + str(obj["position"]))
            parts.append("coordinate_frame=" + obj["coordinate_frame"])
        if obj["size"] is not None:
            parts.append("size=" + str(obj["size"]))
        lines.append("Object: " + "; ".join(parts))
    lines.extend("Relation: " + relation for relation in doc["relations"])
    for event in doc["events"]:
        lines.append(
            f"Transition: {event['object']} {event['track_id']} from {event['source_anchor']} {event['source_anchor_id']} to {event['destination_anchor']} {event['destination_anchor_id']}; observed interval {event['start']:g}-{event['end']:g}; confirmed {event['confirmed_at']:g}."
        )
    return "\n".join(lines)


def build_memory(
    frames: list[Frame], cfg: Config | None = None, *, transitions: bool = True
) -> dict:
    cfg = cfg or Config()
    if not frames or not all(isinstance(f, Frame) for f in frames):
        raise ValueError("Expected validated observation frames")
    frames = sorted(frames, key=lambda f: (f.stream_id, f.timestamp, f.frame_id))
    tracks, assignment = associate(frames, cfg)
    events = write_events(tracks, assignment, cfg) if transitions else []
    buckets = defaultdict(list)
    for frame in frames:
        buckets[(frame.stream_id, math.floor(frame.timestamp / cfg.window_seconds))].append(frame)
    docs = []
    for (stream, _), group in sorted(buckets.items()):
        objects, relations = {}, set()
        for frame in group:
            labels = {o.local_id: o.label for o in frame.objects}
            for obj in frame.objects:
                row = {
                    "label": obj.label,
                    "state": obj.state,
                    "position": obj.position,
                    "size": obj.size,
                    "coordinate_frame": frame.coordinate_frame,
                }
                if transitions:
                    row["track_id"] = assignment[(stream, frame.frame_id, obj.local_id)]
                objects[json.dumps(row, sort_keys=True)] = row
            for rel in frame.relations:
                if transitions:
                    subject = assignment[(stream, frame.frame_id, rel.subject)]
                    target = assignment[(stream, frame.frame_id, rel.object)]
                    relations.add(
                        f"{labels[rel.subject]} {subject} {rel.predicate} {labels[rel.object]} {target}"
                    )
                else:
                    relations.add(f"{labels[rel.subject]} {rel.predicate} {labels[rel.object]}")
        start, end = group[0].timestamp, group[-1].timestamp
        doc = {
            "doc_id": f"D{len(docs) + 1:06d}",
            "stream_id": stream,
            "start": start,
            "end": end,
            "frame_ids": [f.frame_id for f in group],
            "locations": sorted({f.location for f in group}),
            "activities": sorted({f.activity for f in group}),
            "objects": [objects[k] for k in sorted(objects)],
            "relations": sorted(relations),
            "events": [
                e
                for e in events
                if e["stream_id"] == stream and e["start"] <= end and start <= e["end"]
            ],
        }
        doc["text"] = document_text(doc)
        docs.append(doc)
    track_rows = (
        [
            {
                "track_id": t.track_id,
                "label": t.label,
                "is_anchor": t.is_anchor,
                "stream_id": t.observations[0][0].stream_id,
                "observations": [
                    {"frame_id": f.frame_id, "timestamp": f.timestamp, "local_id": o.local_id}
                    for f, o in t.observations
                ],
            }
            for t in tracks
        ]
        if transitions
        else []
    )
    return {
        "schema_version": 1,
        "variant": "r4dsg" if transitions else "no-transition-object-relation",
        "config": asdict(cfg),
        "tracks": track_rows,
        "events": events,
        "documents": docs,
    }
