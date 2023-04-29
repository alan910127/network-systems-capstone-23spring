import logging
import socket

from quic_impl import Connection

logger = logging.getLogger("quic_server")


class QUICServer:
    def __init__(self) -> None:
        """Initialize the QUIC server."""

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connection: Connection | None = None

    def listen(self, socket_addr: tuple[str, int]) -> None:
        """Listen for incoming QUIC connections on the given socket address."""

        self.socket.bind(socket_addr)
        logger.info(f"Server listening on {socket_addr[0]}:{socket_addr[1]}")

    def accept(self) -> None:
        """Accept an incoming QUIC connection."""

        data, address = self.socket.recvfrom(4096)
        logger.debug(f"{data=}")
        logger.info(f"Accepted a connection from {address[0]}:{address[1]}")
        self.connection = Connection(address)
        self.connection.server_handshake()

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
    server.send(1, b"SOME DATA, MAY EXCEED 1500 bytes")
    _, recv_data = server.recv()
    print(recv_data.decode())  # "Hello Server!"
    server.close()


if __name__ == "__main__":
    main()
