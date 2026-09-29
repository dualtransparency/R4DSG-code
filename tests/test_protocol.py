import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from r4dsg.evaluation import evaluate
from r4dsg.memory import build_memory
from r4dsg.qa import ChatClient, NoRedirect, Query, build_mcq_prompt, options_from_row, parse_answer
from r4dsg.retrieval import Index
from r4dsg.schema import parse_frames


def test_retrieval_ignores_all_other_qa_metadata(frames_data):
    index = Index(build_memory(parse_frames(frames_data))["documents"])
    row = {"id": "toy", "question": "Where is the cup?"}
    expected = index.search(Query.from_row(row).question)
    row.update(
        {
            "answer": "A",
            "choice_a": "table",
            "choice_b": "shelf",
            "reason": "a private annotation",
            "rationale": "counter",
            "object_mentions": ["unseen"],
            "keywords": ["irrelevant"],
            "trigger": "different",
        }
    )
    assert index.search(Query.from_row(row).question) == expected
    with pytest.raises(TypeError):
        index.search(row)


def test_retrieval_empty_and_limits(frames_data):
    index = Index(build_memory(parse_frames(frames_data))["documents"])
    assert index.search("zzzznotpresent") == []
    assert index.search("") == []
    assert len(index.search("cup", 1)) == 1
    assert Index([]).search("cup") == []
    with pytest.raises(ValueError):
        index.search("cup", 0)


def test_mcq_prompt_projects_question_choices_and_evidence():
    row = {
        "id": "toy",
        "question": "Where?",
        "options": dict(zip("ABCD", ["table", "shelf", "box", "floor"])),
        "answer": "B",
        "reason": "SECRET_TEST_CANARY",
    }
    prompt = build_mcq_prompt(
        Query.from_row(row),
        options_from_row(row),
        [{"doc_id": "d", "text": "cup on shelf", "reason": "SECRET_TEST_CANARY"}],
    )
    assert "SECRET_TEST_CANARY" not in json.dumps(prompt)
    payload = json.loads(prompt[1]["content"])
    assert payload["options"]["B"] == "shelf"
    assert set(payload) == {"question", "options", "evidence"}


@pytest.mark.parametrize("value", ["The answer is A", "A or B", "a", "", "AB"])
def test_response_parser_does_not_guess(value):
    with pytest.raises(ValueError):
        parse_answer(value)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/v1",
        "file:///tmp/model",
        "https://user@example.com",
        "https://example.com?key=secret",
    ],
)
def test_endpoint_validation(endpoint):
    with pytest.raises(ValueError):
        ChatClient(endpoint, "test-model")


def test_http_model_protocol_and_error_redaction(monkeypatch):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            response = {
                "choices": [
                    {
                        "message": {
                            "content": "B" if len(seen) == 1 else "unexpected private response"
                        }
                    }
                ]
            }
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        def log_message(self, *args):
            pass

    monkeypatch.delenv("R4DSG_API_KEY", raising=False)
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = ChatClient(f"http://127.0.0.1:{server.server_port}/v1", "test-model")
        assert client.answer([{"role": "user", "content": "synthetic prompt"}]) == "B"
        assert seen[0]["temperature"] == 0
        assert seen[0]["model"] == "test-model"
        with pytest.raises(RuntimeError) as exc:
            client.answer([])
        assert "private response" not in str(exc.value)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_eval_counts_and_missing_types():
    result = evaluate(
        [{"id": "a", "prediction": "A"}, {"id": "b", "prediction": "A"}],
        [{"id": "a", "answer": "A", "type": "when"}, {"id": "b", "answer": "B", "type": "why"}],
    )
    assert result["overall"]["accuracy_percent"] == 50
    assert result["when"]["accuracy_percent"] == 100
    assert result["why"]["accuracy_percent"] == 0


def test_eval_refuses_incomplete_or_duplicate_predictions():
    labels = [{"id": "a", "answer": "B"}]
    for predictions in ([], [{"id": "b", "prediction": "B"}], [{"id": "a", "prediction": "B"}] * 2):
        with pytest.raises(ValueError):
            evaluate(predictions, labels)
    assert evaluate([{"id": "a", "prediction": "B"}], labels)["when"]["accuracy_percent"] is None


def test_redirects_are_refused():
    with pytest.raises(urllib.error.URLError):
        NoRedirect().redirect_request(None, None, 302, "found", {}, "https://example.com")


def test_model_response_type_is_validated():
    with pytest.raises(ValueError):
        parse_answer(None)
