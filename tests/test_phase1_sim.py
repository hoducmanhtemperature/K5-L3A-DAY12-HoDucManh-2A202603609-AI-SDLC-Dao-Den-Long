"""Unit, Test Contract v1.0, determinism, and import-boundary tests for Phase 1."""

from __future__ import annotations

import ast
import base64
import json
import math
import os
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.constants import PHASE1_TUNING  # noqa: E402
from src.game.sim import ContractInputError, Simulation, run_headless  # noqa: E402
from src.server import read_ws_frame, start_server  # noqa: E402


class TestPhase1Simulation(unittest.TestCase):
    """Verify PRD-0 mechanics and Test Contract v1.0 compliance."""

    def test_contract_json_matches_phase1_tuning(self) -> None:
        contract = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contract_version"], "1.0")
        self.assertEqual(contract["tuning"], PHASE1_TUNING)

    def test_sim_module_is_decoupled_from_io_and_rendering(self) -> None:
        forbidden_imports = {"http", "socket", "threading", "tkinter", "pygame", "pyglet", "os", "sys", "time"}
        for rel in ("src/game/constants.py", "src/game/sim.py"):
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertNotIn(top, forbidden_imports, f"{rel} must not import {top}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    self.assertNotIn(top, forbidden_imports, f"{rel} must not import {top}")

    def test_movement_cam_yaw_and_diagonal_normalization(self) -> None:
        sim = Simulation(seed=1, night=1, scenario={"random_motes": False, "random_shades": False})
        # Diagonal move [1, 1] with cam_yaw_deg=0 must normalize speed to player_speed (6.0 m/s -> 0.1 m/tick)
        sim.step({"move": [1.0, 1.0], "cam_yaw_deg": 0.0})
        dist = math.hypot(sim.player.pos[0], sim.player.pos[2])
        self.assertAlmostEqual(dist, 6.0 / 60.0, places=5)

        # Reset and move [0, 1] with cam_yaw_deg=90 -> x' = sin(90) = +1, z' = cos(90) = 0
        sim2 = Simulation(seed=1, night=1, scenario={"random_motes": False, "random_shades": False})
        sim2.step({"move": [0.0, 1.0], "cam_yaw_deg": 90.0})
        self.assertAlmostEqual(sim2.player.pos[0], 6.0 / 60.0, places=5)
        self.assertAlmostEqual(sim2.player.pos[2], 0.0, places=5)

    def test_mote_pickup_capacity_and_lantern_deposit_rising_edge_win(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 9, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [[0.0, 0.0, 24.5], [0.2, 0.0, 24.5]],
            "lanterns": [
                {"id": "L2", "lit": True},
                {"id": "L3", "lit": True},
                {"id": "L4", "lit": True},
                {"id": "L5", "lit": True},
            ],
            "time_left_s": 100.0,
        }
        sim = Simulation(seed=7, night=1, scenario=sc)
        # Setup must not award score or emit events
        self.assertEqual(sim.score, 0)
        # First tick picks up 1 mote to reach capacity=10 (second mote remains) and rising-edge interact lights L1
        evs = sim.step({"interact": True})
        names = [e["name"] for e in evs]
        self.assertIn("mote_picked", names)
        self.assertIn("deposit", names)
        self.assertIn("lantern_lit", names)
        self.assertIn("game_over", names)
        self.assertEqual(len(sim.motes), 1)
        self.assertEqual(sim.state, "won")
        # 10*10 + 100 + floor(99.983)*2 + 3*50 = 100 + 100 + 198 + 150 = 548
        self.assertEqual(sim.score, 548)

    def test_interact_held_does_not_retrigger_without_false_transition(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [[0.0, 0.0, 24.5]],
        }
        sim = Simulation(seed=2, night=1, scenario=sc)
        ev1 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "deposit" for e in ev1))
        self.assertEqual(sim.player.carried, 0)
        # Pick up a mote on tick 2 while interact remains True: must NOT deposit
        sim.motes.append(sim.motes[0] if sim.motes else type(sim.lanterns[0])("M9", [0.0, 0.0, 24.5]))  # noqa
        from src.game.sim import Mote

        sim.motes = [Mote(id="M9", pos=[0.0, 0.0, 24.5])]
        ev2 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "mote_picked" for e in ev2))
        self.assertFalse(any(e["name"] == "deposit" for e in ev2))
        # Release then press again -> deposits
        sim.step({"interact": False})
        ev4 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "deposit" for e in ev4))

    def test_pulse_stuns_pushes_and_respects_cooldown_and_cost(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 4, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "shades": [{"id": "S1", "pos": [3.0, 0.0, 0.0]}],
        }
        sim = Simulation(seed=3, night=1, scenario=sc)
        evs = sim.step({"pulse": True})
        pulse_ev = [e for e in evs if e["name"] == "pulse"]
        self.assertEqual(len(pulse_ev), 1)
        self.assertEqual(pulse_ev[0]["data"]["stunned_ids"], ["S1"])
        self.assertEqual(sim.player.carried, 1)
        self.assertEqual(sim.score, 5)
        self.assertEqual(sim.shades[0].state, "stunned")

        # Complete push over 15 ticks (1 already ran -> 14 more)
        for _ in range(14):
            sim.step({"pulse": False})
        self.assertGreater(sim.shades[0].pos[0], 6.5)

        # Pressing pulse while on cooldown or < pulse_cost does nothing
        evs_cd = sim.step({"pulse": True})
        self.assertFalse(any(e["name"] == "pulse" for e in evs_cd))

    def test_shade_hit_drops_motes_grants_invuln_and_safe_radius_blocks_shades(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "shades": [{"id": "S1", "pos": [0.5, 0.0, 0.0]}],
        }
        sim = Simulation(seed=5, night=1, scenario=sc)
        evs = sim.step()
        hits = [e for e in evs if e["name"] == "player_hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"], {"by": "shade", "flames": 2, "dropped": 2})
        self.assertEqual(sim.player.carried, 3)
        self.assertEqual(len(sim.motes), 2)

        # Lit lantern safe radius (6.0 m) keeps shade outside 6 m of L1 (0, 0, 25)
        sc_safe = {
            "player": {"pos": [0.0, 0.0, 25.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True}],
            "shades": [{"id": "S1", "pos": [0.0, 0.0, 20.5]}],
        }
        sim_safe = Simulation(seed=5, night=1, scenario=sc_safe)
        sim_safe.step()
        dist_to_l1 = math.hypot(sim_safe.shades[0].pos[0] - 0.0, sim_safe.shades[0].pos[2] - 25.0)
        self.assertGreaterEqual(dist_to_l1, 5.999)
        self.assertEqual(sim_safe.player.flames, 3)

    def test_fall_off_island_deducts_flame_and_respawns_or_loses(self) -> None:
        sc = {
            "player": {"pos": [41.0, -9.9, 0.0], "carried": 4, "flames": 2},
            "random_motes": False,
            "random_shades": False,
        }
        sim = Simulation(seed=9, night=1, scenario=sc)
        # Step enough ticks under gravity for Y < -10
        hit_events = []
        for _ in range(10):
            evs = sim.step()
            hit_events.extend(e for e in evs if e["name"] == "player_hit")
        self.assertEqual(len(hit_events), 1)
        self.assertEqual(hit_events[0]["data"], {"by": "fall", "flames": 1, "dropped": 4})
        self.assertEqual(sim.player.carried, 0)
        # Wait out 60-tick respawn delay
        for _ in range(65):
            sim.step()
        self.assertEqual(sim.player.pos, [0.0, 0.0, 0.0])
        self.assertEqual(sim.state, "playing")

        # Dawn timeout loses when time_left_s runs out
        sc_dawn = {"random_motes": False, "random_shades": False, "time_left_s": 0.05}
        sim_dawn = Simulation(seed=9, night=1, scenario=sc_dawn)
        for _ in range(5):
            sim_dawn.step()
        self.assertEqual(sim_dawn.state, "lost")

    def test_headless_cli_determinism_jsonl_contract_and_exit_code_2(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            inputs_file = tmp_dir / "inputs.json"
            inputs_file.write_text(
                json.dumps(
                    {
                        "frames": [
                            {"tick": 0, "move": [0, 1], "cam_yaw_deg": 0},
                            {"tick": 60, "move": [1, 0], "jump": True},
                            {"tick": 61, "jump": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out1 = tmp_dir / "run1.jsonl"
            out2 = tmp_dir / "run2.jsonl"

            for out_path in (out1, out2):
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "src" / "headless.py"),
                        "--seed",
                        "42",
                        "--night",
                        "1",
                        "--inputs",
                        str(inputs_file),
                        "--ticks",
                        "360",
                        "--snapshot-every",
                        "30",
                        "--out",
                        str(out_path),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)

            raw1 = out1.read_text(encoding="utf-8")
            raw2 = out2.read_text(encoding="utf-8")
            self.assertEqual(raw1, raw2, "Headless output must be byte-identical across runs")

            lines = [json.loads(line) for line in raw1.splitlines() if line.strip()]
            self.assertEqual(lines[0]["type"], "snapshot")
            self.assertEqual(lines[0]["tick"], 0)
            self.assertEqual(lines[-1]["type"], "end")
            self.assertEqual(lines[-1]["ticks"], 360)

            # Malformed inputs (non-increasing ticks) must exit 2
            bad_inputs = tmp_dir / "bad_inputs.json"
            bad_inputs.write_text(json.dumps({"frames": [{"tick": 5}, {"tick": 5}]}), encoding="utf-8")
            bad_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "headless.py"),
                    "--seed",
                    "1",
                    "--night",
                    "1",
                    "--inputs",
                    str(bad_inputs),
                    "--ticks",
                    "10",
                    "--out",
                    str(tmp_dir / "unused.jsonl"),
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(bad_proc.returncode, 2)

    def test_headless_full_night_performance_budget(self) -> None:
        t0 = time.monotonic()
        records = run_headless(seed=123, night=1, ticks=18000, snapshot_every=60)
        elapsed = time.monotonic() - t0
        self.assertEqual(records[-1]["type"], "end")
        self.assertLess(elapsed, 10.0, f"Full 18,000-tick night took too long: {elapsed:.2f}s")

    def test_3d_http_and_websocket_server_drives_live_simulation(self) -> None:
        srv = start_server("127.0.0.1", 0)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("Đảo Đèn Lồng", resp.read().decode("utf-8"))
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/vendor/three.min.js", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("THREE", resp.read().decode("utf-8", errors="ignore")[:2048])

            # Connect RFC 6455 WebSocket client, send input, receive live sim state
            with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                key = base64.b64encode(os.urandom(16)).decode("ascii")
                req = (
                    f"GET /ws HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                    f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
                )
                sock.sendall(req.encode("ascii"))
                handshake = sock.recv(1024).decode("ascii", errors="replace")
                self.assertIn("101 Switching Protocols", handshake)

                # Send masked WebSocket move frame
                payload = json.dumps({"move": [0, 1], "cam_yaw_deg": 0}).encode("utf-8")
                mask = b"\x12\x34\x56\x78"
                masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                sock.sendall(struct.pack("!BB", 0x81, 0x80 | len(payload)) + mask + masked)

                moved = False
                for _ in range(15):
                    frame = read_ws_frame(sock)
                    self.assertIsNotNone(frame)
                    _, raw = frame
                    msg = json.loads(raw.decode("utf-8"))
                    if msg["state"]["player"]["pos"][2] > 0.05:
                        moved = True
                        break
                self.assertTrue(moved, "Expected live WebSocket simulation to advance player position")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
