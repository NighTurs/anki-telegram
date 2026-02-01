from __future__ import annotations

import json

import pytest

from app.generator import GeneratorError, parse_flashcard_json


def test_parse_flashcard_json_success() -> None:
    payload = json.dumps({"front": "A", "back": "B", "create_reverse": True})
    flashcard = parse_flashcard_json(payload)

    assert flashcard.front == "A"
    assert flashcard.back == "B"
    assert flashcard.create_reverse is True


def test_parse_flashcard_json_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("ERROR")

    with pytest.raises(GeneratorError):
        parse_flashcard_json("not json")

    assert any("Copilot JSON parse error" in record.message for record in caplog.records)
