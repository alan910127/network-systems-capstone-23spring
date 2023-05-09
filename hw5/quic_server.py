import socket

import utils
from quic_impl import QuicConnection

logger = utils.get_colored_logger("QUIC_SERVER")


class QUICServer:
    def __init__(self) -> None:
        """Initialize the QUIC server."""

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connection: QuicConnection | None = None

    def listen(self, socket_addr: tuple[str, int]) -> None:
        """Listen for incoming QUIC connections on the given socket address."""

        self.socket.bind(socket_addr)

        ip, port = self.socket.getsockname()
        logger.info(f"Listening on {ip}:{port}")

    def accept(self) -> None:
        """Accept an incoming QUIC connection."""

        connection = QuicConnection.accept_one(self.socket)

        if connection is None:
            return

        self.connection, ip, port = connection
        logger.info(f"Accepted connection from {ip}:{port}")

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        if self.connection is None:
            raise RuntimeError("No client connected")

        self.connection.send(stream_id, data)

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        if self.connection is None:
            raise RuntimeError("No client connected")

        return self.connection.recv()

    def close(self) -> None:
        """Close the QUIC server."""

        if self.connection is not None:
            self.connection.close()

        self.socket.close()


def main():
    server = QUICServer()
    server.listen(("", 30000))
    server.accept()
    for i in range(5):
        server.send(i, b"1" * 1_000_000)
        _, recv_data = server.recv()
        print(recv_data.decode())  # "Hello Server!"
    server.close()


if __name__ == "__main__":
    main()
