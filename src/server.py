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
from src.game.leaderboard import add_entry, export_leaderboard, load_entries  # noqa: E402
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
    if length > 65536:
        raise ValueError(f"WebSocket frame too large: {length}")
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

    def _send_json(self, code: int, obj: object) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route == "/ws":
            self._handle_websocket()
            return
        if route == "/api/leaderboard":
            self._send_json(200, {"entries": load_entries()})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route != "/api/leaderboard":
            self.send_error(404, "Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if length <= 0 or length > 8192:
            self._send_json(400, {"error": "Invalid request body size"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            entries = add_entry(
                name=str(body.get("name", "")),
                score=int(body.get("score", 0)),
                nights_won=int(body.get("nights_won", 0)),
                seed=int(body.get("seed", 1)),
            )
            self._send_json(200, {"entries": entries})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})

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
            nonlocal sim
            try:
                while not stop_flag.is_set():
                    try:
                        frame = read_ws_frame(conn)
                    except socket.timeout:
                        continue
                    except (OSError, ValueError):
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
                            cmd = msg.get("cmd")
                            if cmd in ("restart", "start"):
                                raw_seed = msg.get("seed", sim.seed + 1)
                                seed = raw_seed if isinstance(raw_seed, int) and not isinstance(raw_seed, bool) else sim.seed + 1
                                raw_night = msg.get("night", sim.night)
                                night = raw_night if raw_night in (1, 2, 3) else sim.night
                                sim = Simulation(seed=seed, night=night)
                                latest_input.clear()
                            else:
                                mv = msg.get("move")
                                if (
                                    isinstance(mv, list)
                                    and len(mv) == 2
                                    and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in mv)
                                ):
                                    latest_input["move"] = [
                                        max(-1.0, min(1.0, float(mv[0]))),
                                        max(-1.0, min(1.0, float(mv[1]))),
                                    ]
                                yaw = msg.get("cam_yaw_deg")
                                if isinstance(yaw, (int, float)) and not isinstance(yaw, bool):
                                    latest_input["cam_yaw_deg"] = float(yaw)
                                for k in ("jump", "interact", "pulse", "dash", "pause"):
                                    if isinstance(msg.get(k), bool):
                                        latest_input[k] = msg[k]
            finally:
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
                    evs = sim.step(latest_input if sim.state in ("playing", "paused") else None)
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
    parser.add_argument(
        "--export-leaderboard",
        metavar="OUT_JSON",
        help="Export top-10 local leaderboard to JSON and exit 0.",
    )
    args = parser.parse_args(argv)

    if args.export_leaderboard:
        export_leaderboard(args.export_leaderboard)
        return 0

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
