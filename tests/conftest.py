from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO)
