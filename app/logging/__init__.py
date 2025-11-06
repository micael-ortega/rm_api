"""Logging helpers used across the project."""

from __future__ import annotations

import logging

from app.config import ENV

_LOG_LEVEL = ENV.get("LOG_LEVEL", "INFO").upper()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=getattr(logging, _LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

logger = logging.getLogger("rm_api")

