from __future__ import annotations

import logging

from app.anki_client import AnkiClient
from app.config import Config
from app.generator import Generator
from app.models import AddResult, BotResponse, Flashcard
from app.state import StateStore

logger = logging.getLogger(__name__)


class FlashcardService:
    def __init__(
        self,
        config: Config,
        generator: Generator,
        anki_client: AnkiClient,
        state_store: StateStore,
    ) -> None:
        self._config = config
        self._generator = generator
        self._anki = anki_client
        self._state = state_store

    async def handle_text(self, text: str, user_id: int | None = None) -> BotResponse:
        if user_id is not None and user_id != self._config.allowed_user_id:
            return BotResponse(message="", ignored=True)

        normalized = (text or "").strip()
        if not normalized:
            return BotResponse(message="Please send a non-empty message.")
        if normalized == "/d":
            return await self._handle_delete()
        return await self._handle_add(normalized)

    async def _handle_add(self, text: str) -> BotResponse:
        try:
            result = await self._generator.generate(text)
        except Exception as exc:
            logger.error("Generator error: %s", exc)
            return BotResponse(message="Sorry, I could not generate a flashcard.")

        flashcard = result.flashcard
        try:
            await self._try_sync()
            note_id = await self._anki.add_note(flashcard)
        except Exception as exc:
            logger.error("Anki add failed: %s", exc)
            return BotResponse(message="Failed to add flashcard to Anki.")

        self._state.set_last_added(AddResult(note_id=note_id, flashcard=flashcard))
        sync_warning = await self._try_sync()
        return BotResponse(message=_format_add_message(flashcard, sync_warning))

    async def _handle_delete(self) -> BotResponse:
        if self._state.last_added is None:
            return BotResponse(message="Nothing to delete.")

        last = self._state.last_added
        try:
            await self._try_sync()
            await self._anki.delete_note(last.note_id)
        except Exception as exc:
            logger.error("Anki delete failed: %s", exc)
            return BotResponse(message="Failed to delete flashcard from Anki.")

        sync_warning = await self._try_sync()
        self._state.clear_last_added()
        return BotResponse(message=_format_delete_message(last.flashcard, sync_warning))

    async def _try_sync(self) -> str | None:
        try:
            await self._anki.sync()
        except Exception as exc:
            logger.warning("Anki sync failed: %s", exc)
            return "Warning: Anki sync failed."
        return None


def _format_add_message(flashcard: Flashcard, sync_warning: str | None) -> str:
    lines = [
        "Flashcard added:",
        f"Front: {flashcard.front}",
        f"Back: {flashcard.back}",
        f"Reverse card: {'yes' if flashcard.create_reverse else 'no'}",
    ]
    if sync_warning:
        lines.append(sync_warning)
    return "\n".join(lines)


def _format_delete_message(flashcard: Flashcard, sync_warning: str | None) -> str:
    lines = [
        "Flashcard deleted:",
        f"Front: {flashcard.front}",
        f"Back: {flashcard.back}",
        f"Reverse card: {'yes' if flashcard.create_reverse else 'no'}",
    ]
    if sync_warning:
        lines.append(sync_warning)
    return "\n".join(lines)
