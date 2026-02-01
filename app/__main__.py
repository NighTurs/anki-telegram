from __future__ import annotations

import logging

from app.anki_client import AnkiMcpClient
from app.config import load_config
from app.generator import CopilotGenerator
from app.service import FlashcardService
from app.state import StateStore
from app.telegram_adapter import build_application


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    generator = CopilotGenerator()
    anki_client = AnkiMcpClient(base_url=config.anki_mcp_url)
    service = FlashcardService(config, generator, anki_client, StateStore())
    app = build_application(config, service)
    app.run_polling()


if __name__ == "__main__":
    main()
