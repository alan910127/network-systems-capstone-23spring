from __future__ import annotations

from enum import Enum


class HttpFrameType(Enum):
    Data = 0
    Headers = 1


class HttpFrameHeader:
    def __init__(self, type: HttpFrameType, length: int) -> None:
        self.type = type
        self.length = length

    def to_bytes(self):
        return b"".join(
            [
                self.type.value.to_bytes(1, "big"),
                self.length.to_bytes(4, "big"),
            ]
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> HttpFrameHeader:
        return cls(
            HttpFrameType(data[0]),
            int.from_bytes(data[1:5], "big"),
        )

    @staticmethod
    def size() -> int:
        return 5
