# Anki Telegram Bot

Telegram bot for a single user that turns messages into Anki flashcards via MCP and Copilot.

## Setup

```bash
pyenv local 3.13.0
uv venv
uv sync
```

## Anki MCP

Install the Anki MCP plugin: https://ankiweb.net/shared/info/124672614

## Configuration

Copy the example:

```bash
cp config.yaml.example config.yaml
```

```yaml
TG_API_TOKEN: "YOUR_TELEGRAM_BOT_TOKEN"
TG_USER_ID: 123456789
```

## Run

```bash
uv run python -m app
```

## Tests

```bash
uv run pytest
```
or 
```bash
RUN_COPILOT_TEST=1 RUN_ANKI_TEST=1 uv run pytest
```

## Lint

```bash
uv run ruff check .
```
