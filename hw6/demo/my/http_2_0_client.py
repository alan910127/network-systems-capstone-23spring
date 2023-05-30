from __future__ import annotations

import time
from collections import deque


class HTTPClient:
    def __init__(self) -> None:
        raise NotImplementedError("TODO")

    def get(self, url: str, headers: dict[str, str] | None = None) -> Response:
        raise NotImplementedError("TODO")


NOT_YET = "Not yet"


class Response:
    def __init__(
        self,
        stream_id: int,
        headers: dict[str, str] | None = None,
        status: str = NOT_YET,
    ) -> None:
        self.stream_id = stream_id
        self.headers = headers or {}

        self.status = status
        self.body = b""

        self.contents: deque[bytes] = deque()
        self.complete = False

    def get_headers(self) -> dict[str, str] | None:
        begin_time = time.time()
        while self.status == NOT_YET:
            if time.time() - begin_time > 5:
                return None
        return self.headers

    def get_full_body(self) -> bytes | None:
        begin_time = time.time()
        while not self.complete:
            if time.time() - begin_time > 5:
                return None

        if len(self.body) > 0:
            return self.body

        while len(self.contents) > 0:
            self.body += self.contents.popleft()

        return self.body

    def get_stream_content(self) -> bytes | None:
        begin_time = time.time()
        while len(self.contents) == 0:
            if self.complete or time.time() - begin_time > 5:
                return None

        return self.contents.popleft()
