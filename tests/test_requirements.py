from __future__ import annotations

import pytest

from app.config import Config
from app.generator import Generator
from app.service import FlashcardService
from app.state import StateStore


class DummyGenerator(Generator):
    async def generate(self, text: str):
        raise AssertionError("Should not be called")


class DummyAnki:
    async def add_note(self, flashcard):
        raise AssertionError("Should not be called")

    async def delete_note(self, note_id: int) -> None:
        raise AssertionError("Should not be called")

    async def sync(self) -> None:
        return None


@pytest.mark.asyncio
async def test_empty_message() -> None:
    service = FlashcardService(
        Config(telegram_token="token", allowed_user_id=1, anki_mcp_url="http://anki"),
        DummyGenerator(),
        DummyAnki(),
        StateStore(),
    )

    result = await service.handle_text(" ", user_id=1)

    assert result.message == "Please send a non-empty message."
