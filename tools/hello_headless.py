#!/usr/bin/env python3
"""Checkpoint 0 headless & local HTTP static-serve smoke check (no display required)."""

from __future__ import annotations

import functools
import http.server
import json
import pathlib
import platform
import threading
import urllib.request

TOOLS_DIR = pathlib.Path(__file__).resolve().parent


def check_local_http_serve() -> int:
    """Bind an ephemeral localhost HTTP server and verify hello_3d.html serves HTTP 200."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(TOOLS_DIR))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/hello_3d.html", timeout=5) as resp:
                body = resp.read().decode("utf-8")
                if "__CP0_READY__" not in body:
                    raise RuntimeError("Unexpected hello_3d.html body")
                return resp.status
        finally:
            srv.shutdown()


def run_hello_headless() -> dict[str, object]:
    """Return CP0 environment readiness info (not Test Contract format)."""
    http_status = check_local_http_serve()
    return {
        "project": "Dao Den Long",
        "checkpoint": "phase-0",
        "mode": "headless",
        "python": platform.python_version(),
        "http_static_status": http_status,
        "status": "ready" if http_status == 200 else "error",
    }


def main() -> int:
    print(json.dumps(run_hello_headless(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
