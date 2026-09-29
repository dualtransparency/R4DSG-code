import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from r4dsg.adapter import import_graphs
from r4dsg.io import read_json, write_json
from r4dsg.schema import parse_frames


def test_adapter_projects_only_visual_fields():
    graph = {
        "frames": {
            "f0": {
                "nodes": [
                    {"node_id": "s", "node_type": "space", "object_class": "studio"},
                    {
                        "node_id": "a",
                        "node_type": "activity",
                        "object_class": "sorting",
                        "semantic_attributes": {"reason": "CANARY"},
                    },
                    {
                        "node_id": "o",
                        "node_type": "object",
                        "object_class": "cup",
                        "semantic_attributes": {"purpose": "CANARY"},
                        "visual_attributes": {"state": "empty"},
                        "location_3d": {"x": 1, "y": 2, "z": 3},
                    },
                ],
                "edges": [],
                "reason": "CANARY",
            }
        }
    }
    converted = import_graphs(graph, {"f0": {"timestamp": 0, "stream_id": "demo"}})
    assert "CANARY" not in json.dumps(converted)
    assert converted[0]["coordinate_frame"] == "frame:f0"
    assert len(parse_frames(converted)) == 1
    with pytest.raises(ValueError):
        import_graphs(graph, {})


def command(*args):
    return subprocess.run(
        [sys.executable, "-m", "r4dsg", *map(str, args)], capture_output=True, text=True
    )


def test_cli_build_retrieve_and_atomic_io(tmp_path, frames_data):
    frames = tmp_path / "frames.json"
    memory = tmp_path / "memory.json"
    questions = tmp_path / "questions.json"
    output = tmp_path / "retrieval.json"
    write_json(str(frames), frames_data)
    write_json(str(questions), [{"id": "demo", "question": "cup shelf"}])
    assert command("build", "--frames", frames, "--output", memory).returncode == 0
    assert (
        command(
            "retrieve", "--memory", memory, "--questions", questions, "--output", output
        ).returncode
        == 0
    )
    assert read_json(str(output))[0]["retrieved"][0]["doc_id"] == "D000001"
    assert not list(tmp_path.glob(".r4dsg-*"))
    result = command(
        "answer",
        "--memory",
        memory,
        "--questions",
        questions,
        "--output",
        output,
        "--base-url",
        "http://127.0.0.1:1/v1",
        "--model",
        "test-model",
    )
    assert result.returncode != 0


def test_cli_invalid_input_does_not_echo_private_data(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("PRIVATE_PAYLOAD_NOT_JSON")
    result = command("build", "--frames", path, "--output", tmp_path / "out.json")
    assert result.returncode == 2
    assert "PRIVATE_PAYLOAD" not in result.stderr


def test_cli_evaluator(tmp_path):
    predictions, labels, output = (
        tmp_path / name for name in ("pred.json", "labels.json", "metrics.json")
    )
    write_json(str(predictions), [{"id": "toy", "prediction": "A"}])
    write_json(str(labels), [{"id": "toy", "answer": "A", "type": "when"}])
    assert (
        command(
            "evaluate", "--predictions", predictions, "--labels", labels, "--output", output
        ).returncode
        == 0
    )
    assert read_json(str(output))["overall"]["count"] == 1


def test_output_cannot_replace_input(tmp_path, frames_data):
    path = tmp_path / "frames.json"
    write_json(str(path), frames_data)
    before = path.read_bytes()
    assert command("build", "--frames", path, "--output", path, "--overwrite").returncode == 2
    assert path.read_bytes() == before


def test_existing_output_requires_explicit_overwrite(tmp_path, frames_data):
    frames, output = tmp_path / "frames.json", tmp_path / "memory.json"
    write_json(str(frames), frames_data)
    args = ("build", "--frames", frames, "--output", output)
    assert command(*args).returncode == 0
    assert command(*args).returncode == 2
    assert command(*args, "--overwrite").returncode == 0


def test_answer_cli_checkpoint_and_completion(tmp_path, frames_data, monkeypatch):
    from r4dsg.memory import build_memory

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            answer = "not a letter" if len(requests) == 2 else "A"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"content": answer}}]}).encode())

        def log_message(self, *args):
            pass

    monkeypatch.delenv("R4DSG_API_KEY", raising=False)
    memory, questions, output = (
        tmp_path / name for name in ("memory.json", "questions.json", "pred.json")
    )
    write_json(str(memory), build_memory(parse_frames(frames_data)))
    write_json(
        str(questions),
        [
            {
                "id": str(i),
                "question": "Where is the cup?",
                "options": dict(zip("ABCD", ["table", "shelf", "box", "floor"])),
                "answer": "PRIVATE_LABEL",
                "reason": "PRIVATE_EXPLANATION",
            }
            for i in range(2)
        ],
    )
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    args = (
        "answer",
        "--memory",
        memory,
        "--questions",
        questions,
        "--output",
        output,
        "--base-url",
        f"http://127.0.0.1:{server.server_port}/v1",
        "--model",
        "mock-model",
        "--send-to-model",
    )
    try:
        assert command(*args).returncode == 2
        assert len(read_json(str(output))) == 1
        assert command(*args, "--overwrite").returncode == 0
        predictions = read_json(str(output))
        assert len(predictions) == 2
        assert all(row["prediction"] == "A" and row["retrieved"] for row in predictions)
        assert "PRIVATE_LABEL" not in json.dumps(requests)
        assert "PRIVATE_EXPLANATION" not in json.dumps(requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
