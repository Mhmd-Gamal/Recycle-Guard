"""Portable local launcher. No Unity, Python installation or model credentials needed."""
import argparse
import socket
import threading
import webbrowser
import uvicorn
from adviser.app import app


def main():
    parser = argparse.ArgumentParser(description="RecycleGuard local research demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: sock.bind(("127.0.0.1", args.port))
    except OSError:
        print(f"Port {args.port} is busy. Close the previous demo or use --port 8766.")
        return 1
    print("RecycleGuard | browser demo of the shared C# simulation")
    print("Offline fixture mode. No real LLM or Unity runtime in this executable.")
    print(f"Open http://127.0.0.1:{args.port} | Ctrl+C to stop.")
    if not args.no_browser:
        timer = threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}"))
        timer.daemon = True
        timer.start()
    config = uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning", loop="asyncio", http="h11", ws="none")
    try: uvicorn.Server(config).run(sockets=[sock])
    finally: sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
