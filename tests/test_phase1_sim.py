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
        # Updated in Phase 2 (Ticket-02): contract_version upgraded to 1.1 while preserving all v1.0 keys
        self.assertEqual(contract["contract_version"], "1.1")
        required_tuning_keys = {
            "player_speed", "carry_capacity", "lantern_cost", "lantern_count_night1",
            "pickup_radius", "interact_radius", "pulse_cost", "pulse_radius",
            "night1_duration_s", "flames", "invuln_s", "hit_drop_ratio",
            "pulse_stun_s", "pulse_push_m", "pulse_cooldown_s", "safe_radius",
            "shade_speed", "shade_hit_radius", "fall_enabled", "score",
        }
        self.assertTrue(required_tuning_keys.issubset(contract["tuning"].keys()))
        self.assertEqual(
            set(contract["tuning"]["score"].keys()),
            {"per_mote", "per_lantern", "per_stun", "per_second_left", "per_flame_left"},
        )
        self.assertEqual(contract["tuning"], PHASE1_TUNING)

    def test_sim_module_is_decoupled_from_io_and_rendering(self) -> None:
        forbidden_imports = {
            "http", "socket", "threading", "tkinter", "pygame", "pyglet",
            "os", "sys", "time", "subprocess", "importlib", "json", "pathlib", "numpy",
        }
        for rel in ("src/game/constants.py", "src/game/maps.py", "src/game/sim.py"):
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
        # First tick (k=0) produces events with tick == 1
        evs = sim.step({"interact": True})
        names = [e["name"] for e in evs]
        self.assertIn("mote_picked", names)
        self.assertIn("deposit", names)
        self.assertIn("lantern_lit", names)
        self.assertIn("game_over", names)
        for ev in evs:
            self.assertEqual(ev["tick"], 1, f"Step k=0 event must record tick=1: {ev}")
        self.assertEqual(len(sim.motes), 1)
        self.assertEqual(sim.state, "won")
        # 10*10 + 100 + floor(99.983)*2 + 3*50 = 100 + 100 + 198 + 150 = 548
        self.assertEqual(sim.score, 548)

    def test_interact_held_does_not_retrigger_without_false_transition(self) -> None:
        from src.game.sim import Mote

        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "motes": [[0.0, 0.0, 24.5]],
        }
        sim = Simulation(seed=2, night=1, scenario=sc)
        ev1 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "deposit" and e["tick"] == 1 for e in ev1))
        self.assertEqual(sim.player.carried, 0)
        # Pick up a mote on tick 2 while interact remains True: must NOT deposit
        sim.motes = [Mote(id="M9", pos=[0.0, 0.0, 24.5])]
        ev2 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "mote_picked" and e["tick"] == 2 for e in ev2))
        self.assertFalse(any(e["name"] == "deposit" for e in ev2))
        # Release then press again -> deposits on tick 4
        sim.step({"interact": False})
        ev4 = sim.step({"interact": True})
        self.assertTrue(any(e["name"] == "deposit" and e["tick"] == 4 for e in ev4))

    def test_pulse_stuns_pushes_and_respects_cooldown_and_cost(self) -> None:
        # Updated in Phase 2 (Ticket-02 Part 1): Pulse measures 3D distance from feet+0.8m to shade center
        sc = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 7, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "shades": [
                {"id": "S1", "pos": [5.0, 0.8, 0.0]},
                {"id": "S2", "pos": [5.05, 0.8, 0.0]},
            ],
        }
        sim = Simulation(seed=3, night=1, scenario=sc)
        evs = sim.step({"pulse": True})
        pulse_ev = [e for e in evs if e["name"] == "pulse"]
        self.assertEqual(len(pulse_ev), 1)
        self.assertEqual(pulse_ev[0]["tick"], 1)
        # S1 at exactly 5.0 m is hit (<= r); S2 at 5.05 m is outside
        self.assertEqual(pulse_ev[0]["data"]["stunned_ids"], ["S1"])
        self.assertEqual(sim.player.carried, 4)
        self.assertEqual(sim.score, 5)
        self.assertEqual(sim.shades[0].state, "stunned")

        # Complete push over 15 ticks (1 already ran -> 14 more)
        for _ in range(14):
            sim.step({"pulse": False})
        self.assertGreater(sim.shades[0].pos[0], 8.5)

        # Still on cooldown even though carried (4) >= pulse_cost (3) -> must NOT fire
        evs_cd = sim.step({"pulse": True})
        self.assertFalse(any(e["name"] == "pulse" for e in evs_cd))
        sim.step({"pulse": False})

        # Clear S2 so it does not hit player during the 3s cooldown wait, then verify pulse re-fires cleanly
        sim.shades = [sim.shades[0]]
        sim.player.carried = 4
        for _ in range(165):
            sim.step({"pulse": False})
        evs_refire = sim.step({"pulse": True})
        self.assertTrue(any(e["name"] == "pulse" for e in evs_refire))
        self.assertEqual(sim.player.carried, 1)

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
        self.assertEqual(hit_events[0]["data"]["by"], "fall")
        self.assertEqual(hit_events[0]["data"]["flames"], 1)
        self.assertEqual(hit_events[0]["data"]["dropped"], 4)
        self.assertEqual(hit_events[0]["data"]["lost"], 4)
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
            snaps = [r for r in lines if r["type"] == "snapshot"]
            self.assertEqual([s["tick"] for s in snaps], list(range(0, 361, 30)))
            self.assertAlmostEqual(snaps[2]["time_left_s"], 300.0 - 60 / 60.0, places=3)
            self.assertEqual(snaps[0]["motes_active"], len(snaps[0]["motes"]))
            self.assertEqual(lines[-1]["type"], "end")
            self.assertEqual(lines[-1]["ticks"], 360)

            # Default --snapshot-every is 10, --ticks 0 emits tick 0 + end, early-stop on win works
            win_out = tmp_dir / "win.jsonl"
            win_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "headless.py"),
                    "--seed", "42", "--night", "1",
                    "--scenario", str(ROOT / "tests" / "scenarios" / "p1_win_night1.json"),
                    "--inputs", str(ROOT / "tests" / "scenarios" / "p1_win_inputs.json"),
                    "--ticks", "200",
                    "--out", str(win_out),
                ],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(win_proc.returncode, 0, win_proc.stderr)
            win_lines = [json.loads(ln) for ln in win_out.read_text(encoding="utf-8").splitlines()]
            win_snaps = [r for r in win_lines if r["type"] == "snapshot"]
            self.assertEqual([r["tick"] for r in win_snaps], [0, 10, 20, 26])
            self.assertEqual(win_snaps[-1]["state"], "won")
            self.assertEqual(win_lines[-1]["state"], "won")
            self.assertEqual(win_lines[-1]["ticks"], 26)

            zero_records = run_headless(seed=1, night=1, ticks=0)
            self.assertEqual([r["type"] for r in zero_records], ["snapshot", "end"])
            self.assertEqual(zero_records[-1]["ticks"], 0)

            # Malformed inputs AND malformed scenario must exit 2
            bad_inputs = tmp_dir / "bad_inputs.json"
            bad_inputs.write_text(json.dumps({"frames": [{"tick": 5}, {"tick": 5}]}), encoding="utf-8")
            bad_proc = subprocess.run(
                [
                    sys.executable, str(ROOT / "src" / "headless.py"),
                    "--seed", "1", "--night", "1", "--inputs", str(bad_inputs),
                    "--ticks", "10", "--out", str(tmp_dir / "unused.jsonl"),
                ],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(bad_proc.returncode, 2)

            bad_scenario = tmp_dir / "bad_scenario.json"
            bad_scenario.write_text('{"player": "not-an-object"}', encoding="utf-8")
            bad_sc_proc = subprocess.run(
                [
                    sys.executable, str(ROOT / "src" / "headless.py"),
                    "--seed", "1", "--night", "1", "--scenario", str(bad_scenario),
                    "--ticks", "10", "--out", str(tmp_dir / "unused2.jsonl"),
                ],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(bad_sc_proc.returncode, 2)

    def test_headless_full_night_performance_budget(self) -> None:
        t0 = time.monotonic()
        records = run_headless(seed=123, night=1, ticks=18000, snapshot_every=60)
        elapsed = time.monotonic() - t0
        self.assertEqual(records[-1]["type"], "end")
        self.assertIn(records[-1]["state"], ("lost", "won"))
        self.assertTrue(any(r.get("name") == "shade_spawned" for r in records))
        self.assertLess(elapsed, 10.0, f"Full 18,000-tick night took too long: {elapsed:.2f}s")

    def test_vendor_threejs_sha256_and_contract_edge_cases(self) -> None:
        import hashlib

        digest = hashlib.sha256((ROOT / "web" / "vendor" / "three.min.js").read_bytes()).hexdigest()
        self.assertEqual(digest, "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2")

        # Explicit scenario lit:false takes precedence over deposited>=cost
        sim_lit = Simulation(
            seed=1,
            night=1,
            scenario={"random_motes": False, "random_shades": False, "lanterns": [{"id": "L1", "lit": False, "deposited": 10}]},
        )
        self.assertFalse(sim_lit.lanterns[0].lit)

        # no_flames loss when falling with 1 flame left
        sim_loss = Simulation(
            seed=1,
            night=1,
            scenario={"player": {"pos": [41.0, -9.9, 0.0], "carried": 2, "flames": 1}, "random_motes": False, "random_shades": False},
        )
        game_overs = []
        for _ in range(10):
            game_overs.extend(e for e in sim_loss.step() if e["name"] == "game_over")
        self.assertEqual(sim_loss.state, "lost")
        self.assertEqual(game_overs[-1]["data"], {"result": "lost", "reason": "no_flames"})

        # Out-of-range move and snapshot_every=0 raise ContractInputError
        with self.assertRaises(ContractInputError):
            run_headless(seed=1, night=1, ticks=5, inputs_data={"frames": [{"tick": 0, "move": [1.5, 0.0]}]})
        with self.assertRaises(ContractInputError):
            run_headless(seed=1, night=1, ticks=5, snapshot_every=0)

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
