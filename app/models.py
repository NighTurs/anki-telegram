from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Flashcard:
    front: str
    back: str
    create_reverse: bool


@dataclass(frozen=True)
class AddResult:
    note_id: int
    flashcard: Flashcard


@dataclass(frozen=True)
class BotResponse:
    message: str
    ignored: bool = False
