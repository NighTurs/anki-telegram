from __future__ import annotations

import pytest

from app.generator import GeneratorError, parse_flashcard_json


@pytest.mark.asyncio
async def test_invalid_json_logs_raw_output(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("ERROR")

    with pytest.raises(GeneratorError):
        parse_flashcard_json("{bad}")

    assert any("Copilot JSON parse error" in record.message for record in caplog.records)
