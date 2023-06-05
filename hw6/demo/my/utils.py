from __future__ import annotations

import logging
import os
import socket
from typing import Literal

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


Version = Literal["HTTP/1.0", "HTTP/1.1", "HTTP/2.0", "HTTP/3.0"]
Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

STREAM_BLOCK_SIZE = 4096

STATUS_CODES = {
    200: "OK",
    404: "Not Found",
}


class Request:
    def __init__(self, method: str, resource: str, version: str) -> None:
        self.method = method
        self.resource = resource
        self.version = version

        self.headers: dict[str, str] = {}
        self.body: bytes | None = None

    @classmethod
    def from_socket(cls, client: socket.socket) -> Request | None:
        data = client.recv(STREAM_BLOCK_SIZE)
        if not data:
            return None

        data = data.decode()
        head, data = data.split("\r\n", 1)
        method, resource, version, *_ = head.split()

        request = cls(method, resource, version)

        if not data or data == "\r\n":
            return request

        headers, data = data.split("\r\n\r\n", 1)
        for line in headers.split("\r\n"):
            key, value = line.split(": ", 1)
            request.headers[key.lower()] = value

        content_length = int(request.headers.get("content-length", "0"))

        body = data
        while len(body) < int(content_length):
            body += client.recv(STREAM_BLOCK_SIZE).decode()

        if request.method == "POST":
            request.body = data.encode()

        return request


class ResponseBuilder:
    def __init__(self):
        self.version: Version = "HTTP/1.0"
        self.status_code = 200
        self.headers: dict[str, str] = {}
        self.body: bytes | None = None

    def set_version(self, version: Version) -> ResponseBuilder:
        self.version = version
        return self

    def set_status_code(self, status_code: int) -> ResponseBuilder:
        self.status_code = status_code
        return self

    def set_header(self, key: str, value: str) -> ResponseBuilder:
        self.headers[key] = value
        return self

    def set_body(self, body: bytes) -> ResponseBuilder:
        self.body = body
        self.set_header("Content-Length", str(len(body)))
        return self

    def set_body_chunked(self, body: bytes) -> ResponseBuilder:
        self.body = body
        return self

    def build(self) -> bytes:
        status_line = (
            f"{self.version} {self.status_code} {STATUS_CODES[self.status_code]}"
        )
        header_lines = "".join(
            f"{key}: {value}\r\n" for key, value in self.headers.items()
        )
        return (f"{status_line}\r\n{header_lines}\r\n").encode() + (self.body or b"")


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
        if query == "":
            self.resource = path
        else:
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
        self.received_length = 0
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
        if self.complete:
            return None

        if self.received_length >= self.body_length:
            self.complete = True
            return None

        data = self.socket.recv(STREAM_BLOCK_SIZE)
        self.received_length += len(data)
        return data

    def parse_header(self) -> None:
        data = self.socket.recv(STREAM_BLOCK_SIZE)

        if data == b"":
            return

        data = data.decode()
        head, data = data.split("\r\n", 1)
        self.version, self.status = head.split(maxsplit=1)

        headers, data = data.split("\r\n\r\n", 1)
        for header in headers.split("\r\n"):
            key, value = header.split(": ", 1)
            self.headers[key.lower()] = value

        self.body = data.encode()
        self.received_length = len(data)

        if "content-length" in self.headers:
            self.body_length = int(self.headers["content-length"])

        if self.body_length == 0:
            self.complete = True
            return

        if self.stream:
            return

        while not self.complete:
            body = self.get_remain_body()
            if body is None:
                break

            self.body += body
