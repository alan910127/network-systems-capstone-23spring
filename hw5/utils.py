from __future__ import annotations

import ctypes
import logging
import os
from typing import Type, TypeVar, get_type_hints

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


class ReprBuilder:
    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        self._fields: list[str] = []

    def field(self, name: str, value: object) -> ReprBuilder:
        self._fields.append(f"{name}={value!r}")
        return self

    def finish(self) -> str:
        return f"{self.class_name}({', '.join(self._fields)})"


S = TypeVar("S", bound=Type[ctypes.BigEndianStructure])


def annotated_struct(cls: S) -> S:
    hints = get_type_hints(cls)
    fields = [(name, hints[name]) for name in cls.__annotations__]
    cls._fields_ = fields
    return cls


T = TypeVar("T", bound=ctypes.BigEndianStructure)


class DataParser:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def parse(self, cls: Type[T]) -> T:
        return cls.from_buffer_copy(self.data)

    def consume(self, cls: Type[T]) -> T:
        result = self.parse(cls)
        self.data = self.data[ctypes.sizeof(cls) :]
        return result
