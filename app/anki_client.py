from __future__ import annotations

import json
import logging
from typing import Protocol

import httpx

from app.models import Flashcard

logger = logging.getLogger(__name__)


class AnkiClientError(Exception):
    pass


class AnkiClient(Protocol):
    async def add_note(self, flashcard: Flashcard) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    async def delete_note(self, note_id: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def sync(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class AnkiMcpClient:
    def __init__(
        self,
        base_url: str,
        deck_name: str = "Default",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._deck_name = deck_name
        self._transport = transport

    async def add_note(self, flashcard: Flashcard) -> int:
        model_name = "Basic (and reversed card)" if flashcard.create_reverse else "Basic"
        payload = {
            "deck_name": self._deck_name,
            "model_name": model_name,
            "fields": {"Front": flashcard.front, "Back": flashcard.back},
            "allow_duplicate": True,
        }
        result = await self._call_tool("addNote", payload)
        note_id = result.get("note_id")
        if note_id is None:
            raise AnkiClientError("Anki returned empty note id")
        return int(note_id)

    async def delete_note(self, note_id: int) -> None:
        await self._call_tool("deleteNotes", {"notes": [note_id], "confirmDeletion": True})

    async def sync(self) -> None:
        await self._call_tool("sync", {})

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        logger.info("Anki MCP call started (tool=%s)", name)
        session_id = await self._initialize_session()
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        response_text = await self._post_sse(payload, session_id)
        result = _extract_result(response_text)
        logger.info("Anki MCP call completed (tool=%s)", name)
        return result

    async def _initialize_session(self) -> str:
        logger.info("Anki MCP initialize started")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "anki-telegram", "version": "0.1"},
            },
        }
        response_text, session_id = await self._post_sse(payload, None, return_session=True)
        _extract_result(response_text)
        if not session_id:
            raise AnkiClientError("Missing MCP session id")
        logger.info("Anki MCP initialize completed")
        return session_id

    async def _post_sse(
        self, payload: dict, session_id: str | None, *, return_session: bool = False
    ) -> tuple[str, str | None] | str:
        headers = {"Accept": "application/json, text/event-stream"}
        if session_id:
            headers["mcp-session-id"] = session_id
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=10.0,
                transport=self._transport,
                headers=headers,
            ) as client:
                response = await client.post("/", json=payload)
                response.raise_for_status()
                text = response.text
                sid = response.headers.get("mcp-session-id")
        except httpx.HTTPError as exc:
            logger.error("Anki MCP request failed: %s", exc)
            raise AnkiClientError("Failed to reach Anki MCP server") from exc
        return (text, sid) if return_session else text


def _extract_result(response_text: str) -> dict:
    for line in response_text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line.replace("data: ", "", 1))
            if "error" in payload and payload["error"]:
                raise AnkiClientError(str(payload["error"]))
            result = payload.get("result")
            if isinstance(result, dict):
                return result.get("structuredContent", result)
    raise AnkiClientError("Unexpected MCP response")
