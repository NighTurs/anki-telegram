# Prompt: Build a Telegram-to-Anki Flashcard Bot (Python)

## Goal
Create a Python application that runs a Telegram bot which helps a single authorized user create Anki flashcards. The bot:

- Accepts user messages (often a single word/phrase) and generates flashcard **Front** and **Back** via `copilot-sdk`.
- Adds the flashcard to Anki via an **Anki MCP server API** (direct API calls from Python; **not** via copilot).
- Optionally creates a reversed card unless the user explicitly opts out.
- Supports `/d` command to delete the **most recently added** flashcard (in-memory only).
- Attempts to sync Anki after add/delete; sync failure is non-fatal and should be reported.

## Hard constraints
- Python version: **3.13** managed via **pyenv** (assume Python 3.13 already installed).
- Dependency management: **uv**
- Linting: **ruff**
- Telegram library: **python-telegram-bot**
- Card content generation: **copilot-sdk** with model `"GPT-4.1"` using single-turn prompt/response.
- Anki operations: **Anki MCP server API** (direct API calls from Python; not used by copilot).
- Configuration: `config.yaml` containing:
  - Telegram bot token
  - Allowed user id (only this user is serviced; all others ignored)
- Decouple business logic from Telegram so the core bot can be tested without Telegram.

---

## Functional requirements

### A) Add a flashcard
**Trigger:** user sends any non-command message (text).

**Flow:**
1. Validate authorization: if sender user id != allowed id, ignore (no reply).
2. Validate input: if empty/whitespace-only, reply with a user-friendly error.
3. Build a **static prompt head** for copilot and append the user’s message.
4. Call `copilot-sdk` once (no conversation/session). Model: `"GPT-4.1"`. You can find copilot SDK usage instructions in `copilot-sdk-python.instructions.md`
5. Parse the response deterministically into:
   - `front` (string)
   - `back` (string)
   - `create_reverse` (boolean)
6. Add to Anki MCP:
   - Deck: `Default`
   - Note type: `Basic` if no reverse, otherwise `Basic (and reversed card)`
7. Store “last added” record in memory (by note id).
8. Sync Anki via MCP.
   - If sync fails, continue; the operation still counts as success, but report “sync failed”.
9. Reply to the user with:
   - Front and Back (formatted clearly)
   - Whether reverse card was created
   - If sync failed, include warning text.

**Failure handling:**
- Any failure before Anki add: reply with an error message.
- Failure when adding note: reply with an error message.
- Failure in parsing copilot response: treat as error and reply with a concise user error; log raw output.

---

### B) Delete last flashcard (`/d`)
**Trigger:** message text equals `/d` (tolerate surrounding whitespace).

**Flow:**
1. Validate authorization (same rule).
2. If no last-added record exists, reply “Nothing to delete.”
3. Call Anki MCP to remove that last added note.
4. Sync Anki (non-fatal if fails; report).
5. Reply with the front/back of the deleted flashcard, plus sync warning if applicable.
6. Clear the in-memory last-added record.

---

## Content generation requirements (copilot prompt head)

### Purpose
Given a user message, produce flashcard content. Often the message is a single foreign word/phrase intended for language learning; sometimes it’s richer instructions (sentence, translation, domain fact, definition).

### Rules for copilot
- Detect intent from the user message:
  1. **Single word/phrase:** assume it is a foreign-language item to learn.
     - Front: put the word/phrase into a short, typical 3–5 word context sentence (not long).
     - Back: Russian translation of the intended meaning.
  2. **Full sentence:** treat it as already contextualized; translate to Russian.
  3. **User provides sentence + translation:** preserve user-provided content; fix obvious grammar if needed; keep consistent.
  4. **Non-language knowledge (term/date/geography/etc.):** create a definition-style card; front is a question/prompt, back a concise answer/definition.
  5. **Language/translation target:**
     - Default back language: Russian.
     - If the user explicitly requests another language or “definition only”, comply.
- Reverse card policy:
  - Default `create_reverse = true`.
  - If user explicitly requests “no reverse”, set `false`.
  - If reverse is nonsensical (e.g., long definition), set `false`.

### Copilot output format (strict)
Copilot MUST output **only** valid JSON (no markdown, no extra text), exactly:

```json
{
  "front": "…",
  "back": "…",
  "create_reverse": true
}
```

## Parsing requirements
- Parse JSON strictly.
- If parsing fails:
  - Show a concise user-facing error message.
  - Log the raw copilot output for debugging (do not send raw output to the user).

---

## Architecture requirements (decoupled from Telegram)

Implement a layered design:

### 1) Core domain/service (Telegram-agnostic)
- Public API:
  - `FlashcardService.handle_text(text: str) -> BotResponse`
- Responsibilities:
  - Implements add/delete logic.
  - Calls generator and Anki client.
  - Maintains in-memory last-added state.
- Depends on abstractions/interfaces:
  - `Generator` (copilot client)
  - `AnkiClient` (MCP API client)
  - `Config`
  - `StateStore` (in-memory last-added)

### 2) Telegram adapter
Minimal glue layer that:
- Extracts user id and text from Telegram updates.
- Calls the core service.
- Formats and sends replies.
- Ignores unauthorized users silently (no reply).

---

## Testing requirements (integration tests without Telegram)

- Use `pytest`.
- Tests must run via: `uv run pytest`.

### Required tests (core service)
1. **Happy path add**
   - Generator returns valid JSON.
   - Anki add is called.
   - Sync is attempted.
   - Response includes front/back and reverse decision.
2. **Add with sync failure**
   - Sync fails.
   - Operation still succeeds, but response includes a warning.
3. **Delete happy path after add**
   - Delete removes the last note.
   - Response includes removed front/back and reverse decision.
4. **Delete with nothing to delete**
   - Returns “Nothing to delete.” (or equivalent).
5. **Unauthorized user**
   - No operations performed.
   - No reply (or a sentinel “ignored” result).
6. **Generator invalid JSON**
   - Handled gracefully with concise user error.
   - Raw generator output is logged.
7. **Real Generator query**
    - Integration test that uses the real copilot client to get and parse json response.

### Test doubles strategy
- Prefer a deterministic **fake `Generator`**, only use real copilot in **Real Generator query**.
- Use a **real MCP client**, but instead of "Default" use "Test" deck.

---

## Operational requirements
- Provide a runnable entrypoint: `python -m app` (or equivalent).
- Provide `README.md` including:
  - pyenv setup commands
  - uv install/run commands
  - how to set up `config.yaml`
  - how to run tests and lint (`ruff`)
- Logging:
  - Use Python `logging`.
  - Log copilot raw output on parse failure (not sent to the user).

---

## Deliverables
- Source code in a clear package structure (e.g., `app/`).
- Tests under `tests/`.
- `pyproject.toml` configured for uv + ruff + pytest.
- Clear error messages and robust handling for API failures.

---

## Notes to the implementer LLM
- Do not attempt to test Telegram or call Telegram APIs in tests.
- Copilot must not be given tool access; copilot only produces JSON content.
- Use MCP API directly for add/remove/sync.