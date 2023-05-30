from __future__ import annotations

import socket


class HTTPClient:
    def __init__(self) -> None:
        raise NotImplementedError("TODO")

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> Response:
        raise NotImplementedError("TODO")


class Response:
    def __init__(self, socket: socket.socket, stream: bool) -> None:
        self.socket = socket
        self.stream = stream

        self.version = "HTTP/1.0"
        self.status = ""
        self.headers: dict[str, str] = {}
        self.body = b""
        self.body_length = 0
        self.complete = False
        self.__remain_bytes = b""

    def get_full_body(self) -> bytes | None:
        if self.stream or not self.complete:
            return None

        return self.body

    def get_stream_content(self) -> bytes | None:
        if not self.stream or self.complete:
            return None

        if self.body != b"":
            content = self.body
            self.body = b""
            return content

        content = self.get_remain_body()
        return content

    def get_remain_body(self) -> bytes:
        raise NotImplementedError("TODO")
