from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_id: int
    anki_mcp_url: str


DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_ANKI_MCP_URL = "http://127.0.0.1:3141/"


def load_config(path: Path | None = None) -> Config:
    cfg_path = path or DEFAULT_CONFIG_PATH
    data = yaml.safe_load(cfg_path.read_text()) or {}
    token = str(data.get("TG_API_TOKEN", "")).strip()
    user_id_raw = data.get("TG_USER_ID")
    if not token:
        raise ValueError("TG_API_TOKEN is required in config.yaml")
    if user_id_raw is None:
        raise ValueError("TG_USER_ID is required in config.yaml")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("TG_USER_ID must be an integer") from exc
    return Config(telegram_token=token, allowed_user_id=user_id, anki_mcp_url=DEFAULT_ANKI_MCP_URL)
