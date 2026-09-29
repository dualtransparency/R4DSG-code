"""Import node/edge caches using an explicit recording-time manifest."""

from __future__ import annotations

from r4dsg.schema import parse_frames, serialize


def import_graphs(graphs: dict, manifest: dict) -> list[dict]:
    frames = graphs.get("frames")
    if not isinstance(frames, dict) or not frames:
        raise ValueError("Expected a non-empty frames mapping")
    if set(frames) != set(manifest):
        raise ValueError("Manifest must cover exactly the imported frame IDs")
    result = []
    for frame_id, graph in sorted(frames.items()):
        meta = manifest[frame_id]
        if not isinstance(meta, dict) or not {"stream_id", "timestamp"} <= meta.keys():
            raise ValueError("Manifest needs stream_id and timestamp for every frame")
        if meta.keys() - {"stream_id", "timestamp", "coordinate_frame"}:
            raise ValueError("Unsupported manifest fields")
        nodes = graph.get("nodes", [])
        objects = []
        for node in nodes:
            if node.get("node_type") != "object":
                continue
            position = node.get("location_3d") or {}
            size = node.get("bounding_box_3d") or {}
            state = (node.get("visual_attributes") or {}).get("state")
            objects.append(
                {
                    "local_id": node["node_id"],
                    "label": node["object_class"],
                    "position": [position[k] for k in ("x", "y", "z")]
                    if all(k in position for k in ("x", "y", "z"))
                    else None,
                    "size": [size[k] for k in ("width", "height", "depth")]
                    if all(k in size for k in ("width", "height", "depth"))
                    else None,
                    "state": state
                    if state and str(state).casefold() not in {"unknown", "unspecified"}
                    else None,
                }
            )
        ids = {o["local_id"] for o in objects}
        relations = []
        for edge in graph.get("edges", []):
            if edge.get("subject_node") in ids and edge.get("object_node") in ids:
                relations.append(
                    {
                        "subject": edge["subject_node"],
                        "predicate": edge["predicate"],
                        "object": edge["object_node"],
                        "confidence": edge.get("confidence", 1),
                    }
                )
        locations = sorted({n["object_class"] for n in nodes if n.get("node_type") == "space"})
        activities = sorted({n["object_class"] for n in nodes if n.get("node_type") == "activity"})
        result.append(
            {
                "frame_id": frame_id,
                "stream_id": meta["stream_id"],
                "timestamp": meta["timestamp"],
                "coordinate_frame": meta.get("coordinate_frame", "frame:" + frame_id),
                "location": "; ".join(locations) or "unknown",
                "activity": "; ".join(activities) or "unknown",
                "objects": objects,
                "relations": relations,
            }
        )
    return [serialize(f) for f in parse_frames(result)]
