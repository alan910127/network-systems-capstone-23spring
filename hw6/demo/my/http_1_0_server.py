from __future__ import annotations

import random
import socket
import time
from pathlib import Path
from threading import Thread

from .utils import STREAM_BLOCK_SIZE, Version, get_colored_logger

log = get_colored_logger("HTTPServer")


class HTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.is_running = False
        self.root_path = Path.cwd()

    def run(self) -> None:
        thread = Thread(target=self.run_impl)
        self.is_running = True
        thread.start()

    def run_impl(self) -> None:
        log.info(f"Listening on {self.socket.getsockname()}")
        self.socket.settimeout(1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.listen()

        while self.is_running:
            try:
                client_socket, addr = self.socket.accept()
            except socket.timeout:
                continue

            log.info(f"Accept a connection from {addr}")
            self.handle(client_socket)
            client_socket.close()

    def set_static(self, path: str) -> None:
        self.root_path = Path(path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

        if not self.root_path.is_dir():
            raise ValueError(f"{path} is not a directory")

    def close(self) -> None:
        self.is_running = False
        self.socket.close()

    def handle(self, client: socket.socket) -> None:
        request = Request.from_socket(client)
        log.info(f"Request: {request.method} {request.resource} {request.version}")
        path, _query = request.resource.split("?", 1) if "?" in request.resource else (
            request.resource,
            "",
        )

        if request.method == "GET" and path in ("", "/"):
            handler = self.get_file_list_handler
        elif request.method == "GET" and path.startswith("/static/"):
            handler = self.get_file_handler
        else:
            handler = self.not_found_handler

        start = time.perf_counter()
        handler(client, request)
        end = time.perf_counter()
        log.info(f"{request.method} {request.resource}: {end - start:.2f}s")

        log.info(f"Close connection from {client.getpeername()}")

    def not_found_handler(self, client: socket.socket, _: Request) -> None:
        response = ResponseBuilder().set_status_code(404).build()
        client.sendall(response)

    def get_file_list_handler(self, client: socket.socket, _: Request) -> None:
        all_files = list(self.root_path.iterdir())
        file_list = random.sample(all_files, k=3)

        file_links_html = "<br />".join(
            f'<a href="/static/{file.name}">{file.name}</a>' for file in file_list
        )

        body = f"<html><header></header><body>{file_links_html}</body></html>"

        response = (
            ResponseBuilder()
            .set_status_code(200)
            .set_header("Content-Type", "text/html")
            .set_body(body.encode())
            .build()
        )

        client.sendall(response)

    def get_file_handler(self, client: socket.socket, request: Request) -> None:
        file_path = self.root_path / request.resource.lstrip("/static")

        if not file_path.is_file():
            self.not_found_handler(client, request)
            return

        file_size = file_path.stat().st_size

        with open(file_path, "rb") as f:
            first_chunk = f.read(STREAM_BLOCK_SIZE)
            bytes_sent = len(first_chunk)
            response = (
                ResponseBuilder()
                .set_status_code(200)
                .set_header("Content-Type", "text/plain")
                .set_header("Content-Length", str(file_size))
                .set_body_chunked(first_chunk)
                .build()
            )
            client.sendall(response)

            while bytes_sent < file_size:
                chunk = f.read(STREAM_BLOCK_SIZE)
                bytes_sent += len(chunk)

                client.sendall(chunk)


class Request:
    def __init__(self, method: str, resource: str, version: str) -> None:
        self.method = method
        self.resource = resource
        self.version = version

        self.headers: dict[str, str] = {}
        self.body: bytes | None = None

    @classmethod
    def from_socket(cls, client: socket.socket) -> Request:
        data = client.recv(STREAM_BLOCK_SIZE)
        if not data:
            raise ValueError("Empty request")

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


STATUS_CODES = {
    200: "OK",
    404: "Not Found",
}


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
