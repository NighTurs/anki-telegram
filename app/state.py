from __future__ import annotations

from dataclasses import dataclass

from app.models import AddResult


@dataclass
class StateStore:
    last_added: AddResult | None = None

    def set_last_added(self, result: AddResult) -> None:
        self.last_added = result

    def clear_last_added(self) -> None:
        self.last_added = None
