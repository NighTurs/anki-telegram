from __future__ import annotations

import os

import pytest

from app.anki_client import AnkiMcpClient
from app.models import Flashcard


@pytest.mark.asyncio
async def test_real_anki_add_delete_sync() -> None:
    if os.getenv("RUN_ANKI_TEST") != "1":
        pytest.skip("Set RUN_ANKI_TEST=1 to run this test")

    client = AnkiMcpClient("http://127.0.0.1:3141/", deck_name="Test")
    note_id = await client.add_note(Flashcard(front="Test", back="Test", create_reverse=False))
    await client.delete_note(note_id)
    await client.sync()
