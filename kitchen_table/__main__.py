"""`python -m kitchen_table` — start the server and print the address to open on the phone."""

import argparse
import socket

import uvicorn

from . import config


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is sent; just picks the LAN interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description="Kitchen Table: a private letter explainer.")
    ap.add_argument("--port", type=int, default=8484)
    ap.add_argument("--local-only", action="store_true", help="only this computer, not the phone")
    args = ap.parse_args()
    host = "127.0.0.1" if args.local_only else "0.0.0.0"
    print(f"\n  Kitchen Table is using {config.MODEL} via {config.OLLAMA_URL}")
    print(f"  On this computer:  http://localhost:{args.port}")
    if not args.local_only:
        print(f"  On the phone (same Wi-Fi):  http://{lan_ip()}:{args.port}\n")
    uvicorn.run("kitchen_table.app:app", host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
