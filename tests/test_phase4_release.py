"""Phase 4 tests: Contract v1.3, Benchmark mode, Soak test, Leaderboard, Accessibility, and Packaging."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.leaderboard import add_entry, export_leaderboard, load_entries, validate_name  # noqa: E402
from src.game.sim import run_headless  # noqa: E402
from src.server import start_server  # noqa: E402


class TestPhase4Release(unittest.TestCase):
    """Verify Ticket-04 release requirements and Test Contract v1.3."""

    def test_contract_v1_3_has_bench_and_soak_cmds(self) -> None:
        contract = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contract_version"], "1.3")
        self.assertEqual(contract["bench_cmd"], "python3 src/bench.py")
        self.assertEqual(contract["soak_cmd"], "python3 src/soak.py")
        self.assertTrue((ROOT / "Dockerfile").exists())
        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertTrue((ROOT / "CREDITS.md").exists())
        self.assertTrue((ROOT / "CHANGELOG.md").exists())

    def test_bench_cli_produces_valid_v1_3_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = pathlib.Path(tmp) / "bench_test.json"
            proc = subprocess.run(
                [
                    sys.executable, str(ROOT / "src" / "bench.py"),
                    "--seed", "42", "--duration", "0.4", "--warmup", "0.1",
                    "--out", str(out_path),
                ],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["contract_version"], "1.3")
            for k in (
                "avg_fps", "p1_low_fps", "frame_ms_p95", "frames",
                "load_ms", "peak_mem_mb", "vsync_off", "renderer", "os",
            ):
                self.assertIn(k, data)
            self.assertGreater(data["frames"], 10)
            self.assertGreaterEqual(data["avg_fps"], 60.0)
            self.assertGreaterEqual(data["p1_low_fps"], 30.0)
            self.assertLessEqual(data["load_ms"], 10000.0)
            self.assertGreater(data["peak_mem_mb"], 0)

    def test_soak_cli_runs_consecutive_nights_without_crash_or_mem_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = pathlib.Path(tmp) / "soak_test.json"
            proc = subprocess.run(
                [
                    sys.executable, str(ROOT / "src" / "soak.py"),
                    "--seed", "7", "--nights", "2", "--out", str(out_path),
                ],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["nights"], 2)
            self.assertEqual(data["crashes"], 0)
            self.assertEqual(len(data["results"]), 2)
            for r in data["results"]:
                self.assertIn(r, ("won", "lost"))
            self.assertLessEqual(data["mem_end_mb"], data["mem_start_mb"] * 1.2)
            self.assertGreater(data["duration_s"], 0.0)

    def test_leaderboard_validation_sorting_top10_export_and_http_api(self) -> None:
        # Name validation: 3-12 chars [A-Za-z0-9_] (+ Vietnamese bonus)
        self.assertEqual(validate_name("May_01"), "May_01")
        self.assertEqual(validate_name("ĐènLồng"), "ĐènLồng")
        for bad in ("ab", "too_long_name_13", "bad name", "bad!@#", ""):
            with self.assertRaises(ValueError):
                validate_name(bad)

        with tempfile.TemporaryDirectory() as tmp:
            lb_file = pathlib.Path(tmp) / "lb.json"
            # Add 12 entries including a score tie to test tie-breaker (earlier achieved_at first) & top-10 cap
            add_entry("LaterTie", 500, 2, 10, achieved_at="2026-11-20T12:05:00+07:00", path=lb_file)
            add_entry("EarlierTie", 500, 2, 11, achieved_at="2026-11-20T12:00:00+07:00", path=lb_file)
            for i in range(10):
                add_entry(f"Player_{i}", 100 + i * 50, 1, i, achieved_at=f"2026-11-20T11:0{i}:00+07:00", path=lb_file)

            entries = load_entries(lb_file)
            self.assertEqual(len(entries), 10)
            self.assertEqual(entries[0]["name"], "Player_9")  # 550
            self.assertEqual(entries[1]["name"], "Player_8")  # 500 at 11:08 (earliest tie)
            self.assertEqual(entries[2]["name"], "EarlierTie")  # 500 at 12:00
            self.assertEqual(entries[3]["name"], "LaterTie")  # 500 at 12:05

            # CLI --export-leaderboard must write {"entries": [...]} and exit 0
            export_path = pathlib.Path(tmp) / "exported.json"
            env = dict(os.environ)
            env["DDL_LEADERBOARD_PATH"] = str(lb_file)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "src" / "server.py"), "--export-leaderboard", str(export_path)],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(exported["entries"][0]["name"], "Player_9")
            self.assertEqual(len(exported["entries"]), 10)

            # Live HTTP GET/POST /api/leaderboard
            old_env = os.environ.get("DDL_LEADERBOARD_PATH")
            os.environ["DDL_LEADERBOARD_PATH"] = str(lb_file)
            srv = start_server("127.0.0.1", 0)
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/leaderboard",
                    data=json.dumps({"name": "Champion", "score": 9999, "nights_won": 3, "seed": 42}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    body = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(body["entries"][0]["name"], "Champion")

                # Invalid name returns HTTP 400
                bad_req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/leaderboard",
                    data=json.dumps({"name": "x", "score": 10, "nights_won": 0, "seed": 1}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(bad_req, timeout=5)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()
                if old_env is None:
                    os.environ.pop("DDL_LEADERBOARD_PATH", None)
                else:
                    os.environ["DDL_LEADERBOARD_PATH"] = old_env

    def test_web_accessibility_and_p4_night3_dawn_scenario(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn("opt-reduced-motion", html)
        self.assertIn("opt-large-text", html)
        self.assertIn("btn-reset-keys", html)
        self.assertIn("btn-leaderboard", html)
        self.assertIn("subtitle-bar", html)
        self.assertIn("font-size: 18px", css)
        self.assertIn("body.large-text", css)

        sc = json.loads((ROOT / "tests" / "scenarios" / "p4_release_night3.json").read_text(encoding="utf-8"))
        recs = run_headless(seed=42, night=3, ticks=60, scenario_data=sc, snapshot_every=30)
        self.assertEqual(recs[-1]["state"], "won")
        go = [r for r in recs if r["type"] == "event" and r["name"] == "game_over"]
        self.assertEqual(go[0]["data"]["reason"], "dawn_survived")


if __name__ == "__main__":
    unittest.main()
