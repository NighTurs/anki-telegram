from __future__ import annotations

import json

import httpx
import pytest

from app.anki_client import AnkiClientError, AnkiMcpClient, _extract_result
from app.models import Flashcard


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n"


@pytest.mark.asyncio
async def test_client_uses_current_mcp_tool_names() -> None:
    called_tools: list[str] = []
    session_id = "sid-1"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        method = body["method"]
        if method == "initialize":
            return httpx.Response(
                200,
                text=_sse({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}),
                headers={"mcp-session-id": session_id},
            )
        if method == "tools/call":
            tool_name = body["params"]["name"]
            called_tools.append(tool_name)
            if tool_name == "add_note":
                return httpx.Response(
                    200,
                    text=_sse(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "result": {"structuredContent": {"note_id": 42}},
                        }
                    ),
                )
            return httpx.Response(
                200,
                text=_sse({"jsonrpc": "2.0", "id": 2, "result": {"structuredContent": {}}}),
            )
        raise AssertionError(f"Unexpected method: {method}")

    client = AnkiMcpClient("http://anki", transport=httpx.MockTransport(handler))
    note_id = await client.add_note(Flashcard(front="Front", back="Back", create_reverse=False))
    await client.delete_note(note_id)
    await client.sync()

    assert note_id == 42
    assert called_tools == ["add_note", "delete_notes", "sync"]


def test_extract_result_raises_for_tool_error() -> None:
    response_text = _sse(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "structuredContent": {
                    "isError": True,
                    "content": [{"type": "text", "text": "Unknown tool: addNote"}],
                }
            },
        }
    )

    with pytest.raises(AnkiClientError, match="Unknown tool: addNote"):
        _extract_result(response_text)
