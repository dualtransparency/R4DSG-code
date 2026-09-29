import json
from pathlib import Path

import pytest


@pytest.fixture
def frames_data():
    path = Path(__file__).resolve().parents[1] / "examples" / "frames.json"
    return json.loads(path.read_text())
