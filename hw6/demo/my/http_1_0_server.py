from __future__ import annotations

import socket
from pathlib import Path
from threading import Thread

from utils import STREAM_BLOCK_SIZE, get_colored_logger

log = get_colored_logger("HTTPServer")


class HTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))

        self.root_path = Path.cwd()

    def run(self) -> None:
        thread = Thread(target=self.run_impl)
        thread.start()

    def run_impl(self) -> None:
        log.info(f"Listening on {self.socket.getsockname()}")
        self.socket.settimeout(1)
        self.socket.listen()

        while True:
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
        self.socket.close()

    def handle(self, client: socket.socket) -> None:
        raise NotImplementedError("TODO")


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
