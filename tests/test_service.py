from __future__ import annotations

import json

import pytest

from app.anki_client import AnkiClientError
from app.config import Config
from app.generator import Generator, GeneratorError, parse_flashcard_json
from app.models import Flashcard
from app.service import FlashcardService
from app.state import StateStore


class FakeGenerator(Generator):
    def __init__(self, response: str) -> None:
        self._response = response

    async def generate(self, text: str):
        flashcard = parse_flashcard_json(self._response)
        return type("Result", (), {"flashcard": flashcard})


class ErrorGenerator(Generator):
    async def generate(self, text: str):
        raise GeneratorError("boom")


class FakeAnki:
    def __init__(self, *, sync_fails: bool = False) -> None:
        self.added: list[Flashcard] = []
        self.deleted: list[int] = []
        self.sync_calls = 0
        self.sync_fails = sync_fails
        self.next_id = 100

    async def add_note(self, flashcard: Flashcard) -> int:
        self.added.append(flashcard)
        self.next_id += 1
        return self.next_id

    async def delete_note(self, note_id: int) -> None:
        self.deleted.append(note_id)

    async def sync(self) -> None:
        self.sync_calls += 1
        if self.sync_fails:
            raise AnkiClientError("sync failed")


def make_config() -> Config:
    return Config(telegram_token="token", allowed_user_id=123, anki_mcp_url="http://anki")


@pytest.mark.asyncio
async def test_add_happy_path() -> None:
    response = json.dumps({"front": "Hola amigo", "back": "Privet", "create_reverse": True})
    service = FlashcardService(
        make_config(),
        FakeGenerator(response),
        FakeAnki(),
        StateStore(),
    )

    result = await service.handle_text("hola", user_id=123)

    assert "Flashcard added" in result.message
    assert "Front: Hola amigo" in result.message
    assert "Back: Privet" in result.message
    assert "Reverse card: yes" in result.message


@pytest.mark.asyncio
async def test_add_with_sync_failure() -> None:
    response = json.dumps({"front": "Hola amigo", "back": "Privet", "create_reverse": True})
    service = FlashcardService(
        make_config(),
        FakeGenerator(response),
        FakeAnki(sync_fails=True),
        StateStore(),
    )

    result = await service.handle_text("hola", user_id=123)

    assert "Warning: Anki sync failed." in result.message


@pytest.mark.asyncio
async def test_delete_after_add() -> None:
    response = json.dumps({"front": "Hola amigo", "back": "Privet", "create_reverse": False})
    anki = FakeAnki()
    service = FlashcardService(make_config(), FakeGenerator(response), anki, StateStore())

    await service.handle_text("hola", user_id=123)
    result = await service.handle_text("/d", user_id=123)

    assert "Flashcard deleted" in result.message
    assert anki.deleted


@pytest.mark.asyncio
async def test_delete_nothing() -> None:
    service = FlashcardService(
        make_config(),
        FakeGenerator('{"front":"A","back":"B","create_reverse":false}'),
        FakeAnki(),
        StateStore(),
    )

    result = await service.handle_text("/d", user_id=123)

    assert result.message == "Nothing to delete."


@pytest.mark.asyncio
async def test_unauthorized_ignored() -> None:
    response = json.dumps({"front": "Hola amigo", "back": "Privet", "create_reverse": False})
    service = FlashcardService(make_config(), FakeGenerator(response), FakeAnki(), StateStore())

    result = await service.handle_text("hola", user_id=999)

    assert result.ignored is True
    assert result.message == ""


@pytest.mark.asyncio
async def test_generator_invalid_json_logs(caplog: pytest.LogCaptureFixture) -> None:
    service = FlashcardService(make_config(), ErrorGenerator(), FakeAnki(), StateStore())
    caplog.set_level("ERROR")

    result = await service.handle_text("hola", user_id=123)

    assert "could not generate" in result.message
    assert any("Generator error" in record.message for record in caplog.records)
