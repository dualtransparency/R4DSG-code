# Input and memory schemas

## Canonical observations

Input is a non-empty JSON array. Each frame requires:

| Field | Meaning |
| --- | --- |
| frame_id | Unique frame identifier within the stream |
| stream_id | Recording/session/day identity; association never crosses streams |
| timestamp | Finite, non-negative recording time in seconds, increasing within a stream |
| coordinate_frame | Identity of the coordinate system for positions, not a room label |
| location | Observation-derived place label |
| activity | Observation-derived activity label |
| objects | List of visible object observations; may be empty |
| relations | Optional list of local object-object relations |

Do not mix wall-clock and clip-relative time within a stream. For multiple clips on
one continuous timeline, convert offsets using actual recording metadata. Merge
simultaneous views into one observation before import. Unknown geometry is null,
never silently converted to the origin.

An object requires `local_id` and `label`. Optional fields are `position` (three
finite coordinates), `size` (three positive dimensions in the same length unit),
`state` (visual state string), `instance_key` (independent visual-tracker identity),
and `anchor_candidate` (boolean). Local IDs have no cross-frame identity semantics.
An instance key is trusted only within a stream and bounded time gap; it must not
come from question annotations. Repeated explicit anchor candidates with visual
instance keys can establish an anchor without global geometry.

A relation has `subject`, `predicate`, `object`, and optional `confidence` in [0,1].
Subject/object refer to object-local IDs in the same frame. Unknown fields at frame,
object, and relation levels are rejected. Frame timestamps, local IDs, and non-null
instance keys must be unique in their respective scopes. See [frames.json](../examples/frames.json).

## Node/edge cache adapter

Accepted source structure:

```json
{
  "frames": {
    "frame-0": {
      "nodes": [
        {"node_id": "room", "node_type": "space", "object_class": "studio"},
        {"node_id": "task", "node_type": "activity", "object_class": "sorting"},
        {"node_id": "cup-0", "node_type": "object", "object_class": "cup",
         "location_3d": {"x": 0.0, "y": 0.0, "z": 1.0},
         "bounding_box_3d": {"width": 0.1, "height": 0.1, "depth": 0.1},
         "visual_attributes": {"state": "empty"}}
      ],
      "edges": []
    }
  }
}
```

The separate timestamp manifest maps exactly the imported frame IDs:

```json
{"frame-0": {"stream_id": "session-1", "timestamp": 0.0}}
```

An optional `coordinate_frame` may be supplied only when cross-frame alignment is
known. Otherwise a unique per-frame coordinate system is assigned. Edges use
`subject_node`, `predicate`, `object_node`, optional `confidence`. Edges involving
non-object nodes are omitted: location/activity labels are stored separately.
Arbitrary semantic attributes are not imported. Only recognized visual fields are
projected; this does not certify the upstream provenance of their contents.

The adapter does not automatically merge independent graph branches or resolve
conflicting duplicate observations. Convert each source into one validated,
deduplicated observation stream before building memory.

## Output memory

The JSON root contains `schema_version`, `variant`, the complete numeric `config`,
`tracks`, `events`, and `documents`. Each document records:

- `doc_id`, `stream_id`, observed `start`/`end` seconds, and `frame_ids`;
- `locations`, `activities`, visible `objects`, and local `relations`;
- overlapping transition `events` and reproducibly generated `text`.

An event stores object/track identity, source/destination anchor labels and IDs,
the interval between last supported source and first supported destination, and
`confirmed_at` after stability is established. This interval is not an exact
movement timestamp. A window's span covers its sampled observations, not proof of
continuous visibility. Events may extend beyond an overlapping document's span.

Documents are built offline. Future observations can confirm earlier changes;
this release does not claim causal online evaluation. Tokenization is recomputed
from document text during indexing, never taken from auxiliary QA metadata.
