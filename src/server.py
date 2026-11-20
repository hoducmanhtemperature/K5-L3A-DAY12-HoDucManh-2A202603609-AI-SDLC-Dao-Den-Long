#!/usr/bin/env python3
"""Local HTTP + RFC 6455 WebSocket server driving the 3D browser view with pure Simulation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import pathlib
import socket
import socketserver
import struct
import sys
import threading
import time
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.constants import DT  # noqa: E402
from src.game.sim import Simulation  # noqa: E402


def encode_ws_text(text: str) -> bytes:
    """Encode a UTF-8 string into an unmasked RFC 6455 WebSocket text frame."""
    payload = text.encode("utf-8")
    n = len(payload)
    if n < 126:
        header = struct.pack("!BB", 0x81, n)
    elif n < 65536:
        header = struct.pack("!BBH", 0x81, 126, n)
    else:
        header = struct.pack("!BBQ", 0x81, 127, n)
    return header + payload


def read_ws_frame(sock: socket.socket) -> tuple[int, bytes] | None:
    """Read one RFC 6455 WebSocket frame from socket; returns (opcode, payload) or None on EOF."""
    def recv_exact(k: int) -> bytes | None:
        buf = bytearray()
        while len(buf) < k:
            chunk = sock.recv(k - len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    hdr = recv_exact(2)
    if hdr is None:
        return None
    b1, b2 = hdr[0], hdr[1]
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    length = b2 & 0x7F
    if length == 126:
        ext = recv_exact(2)
        if ext is None:
            return None
        length = struct.unpack("!H", ext)[0]
    elif length == 127:
        ext = recv_exact(8)
        if ext is None:
            return None
        length = struct.unpack("!Q", ext)[0]
    mask = recv_exact(4) if masked else b""
    if masked and mask is None:
        return None
    payload = recv_exact(length) if length > 0 else b""
    if payload is None:
        return None
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


class LanternHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Serves web/ static assets and upgrades /ws to WebSocket game sessions."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return  # Keep terminal output quiet

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] == "/ws":
            self._handle_websocket()
            return
        super().do_GET()

    def _handle_websocket(self) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "Missing Sec-WebSocket-Key")
            return
        accept = base64.b64encode(hashlib.sha1((key + WS_MAGIC).encode("ascii")).digest()).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        conn: socket.socket = self.connection
        conn.settimeout(0.05)

        lock = threading.Lock()
        sim = Simulation(seed=1, night=1)
        latest_input: dict[str, object] = {}
        stop_flag = threading.Event()

        def reader() -> None:
            while not stop_flag.is_set():
                try:
                    frame = read_ws_frame(conn)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 0x8:  # Close
                    break
                if opcode == 0x9:  # Ping
                    try:
                        conn.sendall(struct.pack("!BB", 0x8A, len(payload)) + payload)
                    except OSError:
                        break
                    continue
                if opcode == 0x1:  # Text
                    try:
                        msg = json.loads(payload.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if not isinstance(msg, dict):
                        continue
                    with lock:
                        if msg.get("cmd") == "restart":
                            seed = int(msg.get("seed", sim.seed + 1))
                            sim.__init__(seed=seed, night=1)
                            latest_input.clear()
                        else:
                            for k in ("move", "cam_yaw_deg", "jump", "interact", "pulse"):
                                if k in msg:
                                    latest_input[k] = msg[k]
            stop_flag.set()

        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()

        try:
            next_tick_time = time.monotonic()
            while not stop_flag.is_set():
                now = time.monotonic()
                if now < next_tick_time:
                    time.sleep(min(0.005, next_tick_time - now))
                    continue
                next_tick_time += DT
                if now - next_tick_time > 0.25:
                    next_tick_time = now + DT

                with lock:
                    evs = sim.step(latest_input if sim.state == "playing" else None)
                    payload_obj = {
                        "state": sim.render_state(),
                        "events": evs,
                    }
                try:
                    conn.sendall(encode_ws_text(json.dumps(payload_obj, separators=(",", ":"))))
                except OSError:
                    break
        finally:
            stop_flag.set()


class ReusableThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server(host: str = "127.0.0.1", port: int = 8080) -> ReusableThreadingHTTPServer:
    return ReusableThreadingHTTPServer((host, port), LanternHTTPHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Đảo Đèn Lồng 3D Web Server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser tab.")
    args = parser.parse_args(argv)

    try:
        srv = start_server(args.host, args.port)
    except OSError:
        srv = start_server(args.host, 0)

    actual_port = srv.server_address[1]
    url = f"http://{args.host}:{actual_port}/"
    print(f"Dao Den Long 3D running at {url} (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        srv.shutdown()
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
