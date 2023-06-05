from __future__ import annotations

from enum import Enum


class HttpFrameType(Enum):
    Data = 0
    Headers = 1


class HttpFrameFlag(Enum):
    Default = 0
    EndStream = 1


class HttpFrameHeader:
    def __init__(
        self,
        payload_length: int,
        type: HttpFrameType,
        flag: HttpFrameFlag,
        stream_id: int,
    ) -> None:
        self.payload_length = payload_length
        self.type: HttpFrameType = type
        self.flags: HttpFrameFlag = flag
        self.stream_id = stream_id

    def to_bytes(self) -> bytes:
        id_mask = 0x7FFF_FFFF

        return b"".join(
            [
                self.payload_length.to_bytes(3, "big"),
                self.type.value.to_bytes(1, "big"),
                self.flags.value.to_bytes(1, "big"),
                (self.stream_id & id_mask).to_bytes(4, "big"),
            ]
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> HttpFrameHeader:
        return cls(
            int.from_bytes(data[:3], "big"),
            HttpFrameType(data[3]),
            HttpFrameFlag(data[4]),
            int.from_bytes(data[5:9], "big"),
        )

    @staticmethod
    def size() -> int:
        return 9
    
