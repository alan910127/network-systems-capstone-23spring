class HTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        raise NotImplementedError("TODO")

    def run(self) -> None:
        raise NotImplementedError("TODO")

    def set_static(self, path: str) -> None:
        raise NotImplementedError("TODO")

    def close(self) -> None:
        raise NotImplementedError("TODO")
