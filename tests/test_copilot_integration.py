from __future__ import annotations

import os

import pytest

from app.generator import CopilotGenerator


@pytest.mark.asyncio
async def test_real_copilot_query() -> None:
    if os.getenv("RUN_COPILOT_TEST") != "1":
        pytest.skip("Set RUN_COPILOT_TEST=1 to run this test")

    generator = CopilotGenerator()
    result = await generator.generate("bonjour")

    assert result.flashcard.front
    assert result.flashcard.back
    assert isinstance(result.flashcard.create_reverse, bool)
