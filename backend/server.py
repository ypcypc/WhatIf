"""Sidecar entry point — finds a free port, starts FastAPI."""
import socket
import uvicorn
from api.app import app


def main():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    print(f"__PORT__:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
