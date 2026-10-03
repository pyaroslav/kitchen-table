"""`python -m kitchen_table` — start the server and print the address to open on the phone."""

import argparse
import socket

import uvicorn

from . import config, pairing


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
    ap.add_argument("--new-key", action="store_true", help="unpair every phone and make a new pairing code")
    args = ap.parse_args()
    host = "127.0.0.1" if args.local_only else "0.0.0.0"
    print(f"\n  Kitchen Table is using {config.MODEL} via {config.OLLAMA_URL}")
    print(f"  On this computer:  http://localhost:{args.port}")
    if not args.local_only:
        url = f"http://{lan_ip()}:{args.port}/?key={pairing.get_key(rotate=args.new_key)}"
        print("\n  Pair the phone: scan this with its camera (same Wi-Fi), once.\n")
        try:
            import qrcode
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except ImportError:
            pass
        print(f"\n  or open: {url}\n  (keep this private: it lets a device read the letters)\n")
    uvicorn.run("kitchen_table.app:app", host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
