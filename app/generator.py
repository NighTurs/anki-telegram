from __future__ import annotations

import json
import logging
from dataclasses import dataclass

try:
    from copilot import CopilotClient
    from copilot.generated.session_events import SessionEventType
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    CopilotClient = None
    SessionEventType = None

from app.models import Flashcard

logger = logging.getLogger(__name__)

PROMPT_HEAD = """
You are a flashcard generator.

Rules:
1. Single word/phrase: assume foreign-language item.
   - Front: short 3-5 word context sentence.
   - Back: Russian translation.
2. Full sentence: translate to Russian.
3. Sentence + translation: preserve user-provided content; fix obvious grammar.
4. Non-language knowledge: front is a question/prompt, back is concise answer/definition.
5. Default back language is Russian unless explicitly requested otherwise.

Reverse card policy:
- create_reverse defaults to true.
- If user explicitly requests no reverse, set false.
- If reverse is nonsensical (e.g., long definition), set false.

Output ONLY valid JSON exactly in this format:
{
  "front": "...",
  "back": "...",
  "create_reverse": true
}
""".strip()


class GeneratorError(Exception):
    pass


@dataclass(frozen=True)
class GeneratorResult:
    flashcard: Flashcard
    raw_output: str


class Generator:
    async def generate(self, text: str) -> GeneratorResult:  # pragma: no cover - interface
        raise NotImplementedError


class CopilotGenerator(Generator):
    async def generate(self, text: str) -> GeneratorResult:
        if CopilotClient is None or SessionEventType is None:
            raise GeneratorError("Copilot SDK is not installed")
        prompt = f"{PROMPT_HEAD}\n\nUser message: {text.strip()}"
        client = CopilotClient()
        await client.start()
        try:
            session = await client.create_session({"model": "gpt-4.1"})
            event = await session.send_and_wait({"prompt": prompt}, timeout=60.0)
            if event is None or event.type != SessionEventType.ASSISTANT_MESSAGE:
                raise GeneratorError("Copilot did not return a message")
            raw = str(event.data.content).strip()
        finally:
            await session.destroy()
            await client.stop()
        flashcard = parse_flashcard_json(raw)
        return GeneratorResult(flashcard=flashcard, raw_output=raw)


def parse_flashcard_json(raw: str) -> Flashcard:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Copilot JSON parse error: %s", raw)
        raise GeneratorError("Failed to parse flashcard JSON") from exc
    if not isinstance(payload, dict):
        logger.error("Copilot JSON parse error: %s", raw)
        raise GeneratorError("Flashcard JSON must be an object")
    front = str(payload.get("front", "")).strip()
    back = str(payload.get("back", "")).strip()
    create_reverse = payload.get("create_reverse")
    if not front or not back or not isinstance(create_reverse, bool):
        logger.error("Copilot JSON parse error: %s", raw)
        raise GeneratorError("Flashcard JSON missing required fields")
    return Flashcard(front=front, back=back, create_reverse=create_reverse)
