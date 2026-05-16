"""Logging setup.

No structlog here — Virtual Mouse runs on a desktop, not a service. Plain
stdlib logging is enough; we just configure a level and a clean format.
"""

from __future__ import annotations

import logging
import os
import sys


def configure_logging() -> None:
    level = os.environ.get("VM_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        level=getattr(logging, level, logging.INFO),
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
