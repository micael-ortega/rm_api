"""Utilities to load environment variables for the application."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values, load_dotenv


def _find_env_path() -> Path | None:
    """Locate the .env file in multiple fallback locations."""

    candidates: list[Path] = []

    # When frozen by PyInstaller, resources may live alongside the executable
    # or inside the temporary _MEIPASS directory.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / ".env")
        candidates.append(Path(sys.executable).parent / ".env")

    # Project root relative to this file (works during development).
    candidates.append(Path(__file__).resolve().parents[2] / ".env")

    # Current working directory as a last resort.
    candidates.append(Path.cwd() / ".env")

    for path in candidates:
        if path.is_file():
            return path
    return None


_ENV_PATH = _find_env_path()


@lru_cache(maxsize=1)
def _load_env() -> Mapping[str, str]:
    """Return environment variables defined in the project .env file."""
    if _ENV_PATH:
        load_dotenv(_ENV_PATH)
        return dotenv_values(_ENV_PATH)
    return {}


ENV = _load_env()

