"""Ground truth is consumed only here, after predictions have been written."""

from __future__ import annotations

import re

from r4dsg.qa import parse_answer, row_id


def evaluate(predictions: list[dict], labels: list[dict]) -> dict:
    def index(rows: list[dict]) -> dict:
        result = {row_id(row): row for row in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate evaluation IDs")
        return result

    predicted, truth = index(predictions), index(labels)
    if not truth or predicted.keys() != truth.keys():
        raise ValueError(
            "Prediction and label IDs must match exactly; incomplete runs are not scored"
        )
    groups = {"overall": [], "when": [], "why": []}
    for ident, label in truth.items():
        correct = parse_answer(predicted[ident]["prediction"]) == parse_answer(label["answer"])
        groups["overall"].append(correct)
        kind = label.get("type", "").casefold()
        if not kind:
            match = re.match(r"\s*(when|why)\b", label.get("question", ""), re.I)
            kind = match.group(1).casefold() if match else ""
        if kind in {"when", "why"}:
            groups[kind].append(correct)
    return {
        kind: {
            "count": len(values),
            "correct": sum(values),
            "accuracy_percent": 100 * sum(values) / len(values) if values else None,
        }
        for kind, values in groups.items()
    }
