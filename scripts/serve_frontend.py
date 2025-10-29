#!/usr/bin/env python3
"""Tiny static file server for the frontend directory.

Usage:
  python scripts/serve_frontend.py --port 5173 --dir frontend

Defaults:
  port: 5173
  dir:  frontend

This uses Python's built-in http.server to serve files. It's intended for
development only. For SSO cookies to work cross-origin, ensure the backend's
allowed_origins includes this origin (e.g., http://localhost:5173).
"""

import argparse
import os
import socket
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Serve static frontend")
    parser.add_argument("--port", type=int, default=5173, help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--dir", default="frontend", help="Directory to serve")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1] / args.dir
    if not root.exists():
        raise SystemExit(f"Directory not found: {root}")

    os.chdir(root)
    handler = SimpleHTTPRequestHandler
    httpd = ThreadingHTTPServer((args.host, args.port), handler)

    try:
        hostname = socket.gethostname()
        print(f"Serving {root} on http://{args.host}:{args.port} (hostname: {hostname})")
        print("Press Ctrl+C to stop")
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

