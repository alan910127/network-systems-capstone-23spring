LOG_LEVEL := debug
PYTHON := python3
SERVER := quic_server.py
CLIENT := quic_client.py

.PHONY:  server client

server:
	@LOG_LEVEL=$(LOG_LEVEL) $(PYTHON) $(SERVER)

client:
	@LOG_LEVEL=$(LOG_LEVEL) $(PYTHON) $(CLIENT)
