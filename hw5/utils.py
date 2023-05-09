from __future__ import annotations

import logging
import os

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="[%(levelname)s] %(name)s: %(message)s",
)


def set_logging_color(level: int, color: int) -> None:
    def get_color_code(color: int = 0) -> str:
        return f"\033[{color}m"

    fmt = get_color_code(color) + logging.getLevelName(level) + get_color_code()
    logging.addLevelName(level, fmt)


set_logging_color(logging.DEBUG, 34)  # blue
set_logging_color(logging.INFO, 32)  # green
set_logging_color(logging.WARNING, 33)  # yellow
set_logging_color(logging.ERROR, 31)  # red
set_logging_color(logging.CRITICAL, 35)  # magenta


def get_colored_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)
