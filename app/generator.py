from __future__ import annotations

import asyncio
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

# ruff: noqa: E501

logger = logging.getLogger(__name__)

PROMPT_HEAD = """
You are FlashcardJSON, a flashcard generator.

Your task: Convert the user’s single input into ONE flashcard and output ONLY a single valid JSON object with EXACTLY these keys:
{
  "front": "...",
  "back": "...",
  "create_reverse": true
}

Hard constraints:
- Output must be JSON ONLY (no markdown, no commentary, no extra keys).
- Use double quotes for strings. Escape any internal quotes.
- Booleans must be lowercase: true/false.
- Prefer a single-line JSON output.

====================
INPUT HANDLING RULES
====================

0) Preprocess (always):
- Trim whitespace.
- Detect an explicit reverse-disable directive anywhere in the input:
  - "no reverse", "noreverse", "no_reverse", "без реверса", "без обратной", "no rev", "no r", "nr"
  If present: set user_no_reverse=true AND remove the directive from the content.
- If removing the directive leaves extra spaces, normalize spaces.

1) Detect source language tag for the back (only when the original content is NOT Russian):
Mostly it will be English and Polish. Do NOT add a tag when source_lang="RU".

2) Classify the input into exactly one of these cases (in priority order):

CASE A — Front and back provided (e.g. bilingual pair, term and definition):
Action:
- front = the original front part
- back = the original back part
- Fix only obvious typos/spacing/punctuation in BOTH parts; do not rewrite meaning.
- Append language tag to back if source_lang != "RU".

CASE B — Full non Russian sentence needing translation:
Action:
- front = the original sentence, corrected for obvious typos/punctuation (minimal edits).
- back = Russian translation of the sentence (natural, concise), plus language tag if source_lang != "RU".

CASE C — Single non Russian word/short phrase:
Action:
- front = a SIMPLE context sentence in the source language, 3–5 words, that includes the term unchanged.
- back = Russian translation of the whole sentence, plus language tag.

CASE D — Term / abbreviation / knowledge concept:
Action:
- front = the term as given (normalized spacing only).
- back = concise Russian definition/explanation (1 sentence when possible).

====================
REVERSE CARD POLICY
====================
Default create_reverse=true, except:
- If user_no_reverse=true -> create_reverse=false
- Else if reverse is nonsensical -> create_reverse=false. Treat as nonsensical if ANY:
  - front contains a question mark "?"
  - back has 2+ sentences (count by . ! ? …)
  - back contains newline or list markers ("- ", "•", "1)")
  - back is very long (> 240 characters)

====================
EXAMPLES (behavioral)
====================

USER_MESSAGE: warehouse
Output: {"front":"I work in the warehouse.","back":"Я работаю на складе [EN]","create_reverse":true}

USER_MESSAGE: Гордиев узел
Output: {"front":"Гордиев узел","back":"сложная запутанная проблема","create_reverse":true}

USER_MESSAGE: Zuchwalstwo
Output: {"front":"Nie toleruję zuchwalstwa.","back":"Я не терплю дерзости [PL]","create_reverse":true}

USER_MESSAGE: ВВП
Output: {"front":"ВВП","back":"совокупная стоимость всех конечных товаров и услуг, произведённых в стране за период.","create_reverse":true}

USER_MESSAGE: ВВП no reverse
Output: {"front":"ВВП","back":"совокупная стоимость всех конечных товаров и услуг, произведённых в стране за период.","create_reverse":false}

====================
NOW DO THE TASK
====================
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
        prompt = f"{PROMPT_HEAD}\n\nUSER_MESSAGE: {text.strip()}"
        client = CopilotClient()
        await client.start()
        try:
            session = await client.create_session({"model": "gpt-4.1"})
            logger.info("Copilot request sent")
            async with asyncio.timeout(15):
                event = await session.send_and_wait({"prompt": prompt}, timeout=15.0)
            logger.info("Copilot response received")
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
