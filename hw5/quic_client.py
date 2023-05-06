import utils
from quic_impl import QuicConnection

logger = utils.get_colored_logger("QUIC_CLIENT")


class QUICClient:
    def __init__(self):
        """Initialize the QUIC client."""

        self.connection: QuicConnection | None = None

    def connect(self, socket_addr: tuple[str, int]) -> None:
        """Connect to a QUIC server on the given socket address."""

        self.connection = QuicConnection.connect_to(socket_addr)

        ip, port = socket_addr
        logger.info(f"Connected to {ip}:{port}")

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        if self.connection is None:
            raise RuntimeError("No server connected")

        self.connection.send(stream_id, data)

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        if self.connection is None:
            raise RuntimeError("No server connected")

        return self.connection.recv()

    def close(self) -> None:
        """Close the connection and the socket."""

        if self.connection is not None:
            self.connection.close()


def main():
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    _, recv_data = client.recv()
    print(recv_data.decode())  # "SOME DATA, MAY EXCEED 1500 bytes"
    client.send(1, b"Hello Server!")
    client.close()


if __name__ == "__main__":
    main()
