from __future__ import annotations

import socket
from urllib.parse import urlparse

from utils import STREAM_BLOCK_SIZE, Method, Version, get_colored_logger

log = get_colored_logger("HTTPClient")


class HTTPClient:
    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> Response:
        components = urlparse(url, scheme="http")
        builder = (
            RequestBuilder()
            .set_method("GET")
            .set_resource(components.path, components.query)
            .set_version("HTTP/1.0")
        )

        if headers is not None:
            for key, value in headers.items():
                builder.set_header(key, value)

        request = builder.build()

        self.socket.connect((components.hostname, components.port or 80))
        self.socket.sendall(request)

        response = Response(self.socket, stream)
        response.parse_header()

        return response


class RequestBuilder:
    def __init__(self) -> None:
        self.method: Method | None = None
        self.resource: str | None = None
        self.version: Version | None = None

        self.headers: dict[str, str] = {}
        self.body: bytes | None = None

    def set_method(self, method: Method) -> RequestBuilder:
        self.method = method
        return self

    def set_resource(self, path: str, query: str) -> RequestBuilder:
        self.resource = f"{path}?{query}"
        return self

    def set_version(self, version: Version) -> RequestBuilder:
        self.version = version
        return self

    def set_header(self, key: str, value: str) -> RequestBuilder:
        self.headers[key] = value
        return self

    def set_body(self, body: bytes) -> RequestBuilder:
        self.body = body
        return self

    def build(self) -> bytes:
        if self.method is None:
            raise ValueError("method is not set")
        if self.resource is None:
            raise ValueError("resource is not set")
        if self.version is None:
            raise ValueError("version is not set")

        request = bytearray()
        request.extend(f"{self.method} {self.resource} {self.version}\r\n".encode())

        for key, value in self.headers.items():
            request.extend(f"{key}: {value}\r\n".encode())
        request.extend(b"\r\n")

        if self.body is not None:
            request.extend(self.body)

        return bytes(request)


class Response:
    def __init__(self, socket: socket.socket, stream: bool) -> None:
        self.socket = socket
        self.stream = stream

        self.version = ""
        self.status = ""
        self.headers: dict[str, str] = {}
        self.body = b""
        self.body_length = 0
        self.complete = False

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

    def get_remain_body(self) -> bytes | None:
        self.complete = self.complete or len(self.body) >= self.body_length
        if self.complete:
            return None

        return self.socket.recv(STREAM_BLOCK_SIZE)

    def parse_header(self) -> None:
        data = self.socket.recv(STREAM_BLOCK_SIZE)

        if data == b"":
            return

        data = data.decode()
        head, data = data.split("\r\n", 1)
        self.version, self.status = head.split(maxsplit=1)
        log.info(f"version: {self.version}, status: {self.status}")

        headers, data = data.split("\r\n\r\n", 1)
        for header in headers.split("\r\n"):
            key, value = header.split(": ", 1)
            self.headers[key.lower()] = value

        log.info(f"headers: {self.headers}")

        if "content-length" in self.headers:
            self.body_length = int(self.headers["content-length"])

        if self.body_length == 0:
            self.complete = True
            return

        if self.stream:
            self.body = data.encode()
            return

        while not self.complete:
            body = self.get_remain_body()
            if body is None:
                break

            self.body += body
