#!/usr/bin/env python3
"""Headless Soak Test runner for Đảo Đèn Lồng (Test Contract v1.3).

Usage:
    python3 src/soak.py --seed 7 --nights 10 --out soak.json
"""

from __future__ import annotations

import argparse
import gc
import json
import pathlib
import random
import resource
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.constants import TICK_RATE  # noqa: E402
from src.game.maps import NIGHT_CONFIGS  # noqa: E402
from src.game.sim import Simulation  # noqa: E402


def current_rss_mb() -> float:
    """Return current process RSS in MiB (VmRSS on Linux, maxrss fallback)."""
    status_path = pathlib.Path("/proc/self/status")
    if status_path.exists():
        try:
            for line in status_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return round(int(parts[1]) / 1024.0, 2)
        except OSError:
            pass
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB, macOS reports bytes
    if sys.platform == "darwin":
        return round(ru / (1024.0 * 1024.0), 2)
    return round(ru / 1024.0, 2)


def run_soak(seed: int, nights: int) -> dict[str, object]:
    t0 = time.perf_counter()
    crashes = 0
    results: list[str] = []
    mem_start_mb: float | None = None

    for i in range(nights):
        night_num = (i % 3) + 1
        night_seed = seed + i
        in_rng = random.Random(night_seed)
        max_ticks = int(round(NIGHT_CONFIGS[night_num].duration_s * TICK_RATE))
        try:
            sim = Simulation(seed=night_seed, night=night_num)
            if i == 0:
                mem_start_mb = current_rss_mb()

            move_dir = [0.0, 0.0]
            for tick_idx in range(max_ticks):
                if sim.state in ("won", "lost"):
                    break
                if tick_idx % 30 == 0:
                    move_dir = [in_rng.uniform(-1.0, 1.0), in_rng.uniform(-1.0, 1.0)]
                sim.step(
                    {
                        "move": move_dir,
                        "jump": in_rng.random() < 0.05,
                        "dash": in_rng.random() < 0.03,
                        "pulse": in_rng.random() < 0.02,
                        "interact": in_rng.random() < 0.10,
                    }
                )
            results.append(sim.state if sim.state in ("won", "lost") else "lost")
            del sim
            gc.collect()
        except Exception:
            crashes += 1
            results.append("crash")
            traceback.print_exc(file=sys.stderr)

    gc.collect()
    mem_end_mb = current_rss_mb()
    if mem_start_mb is None:
        mem_start_mb = mem_end_mb

    return {
        "nights": nights,
        "crashes": crashes,
        "results": results,
        "mem_start_mb": mem_start_mb,
        "mem_end_mb": mem_end_mb,
        "duration_s": round(time.perf_counter() - t0, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đảo Đèn Lồng Soak Test (Contract v1.3)")
    parser.add_argument("--seed", type=int, default=7, help="Base RNG seed (default: 7)")
    parser.add_argument("--nights", type=int, default=10, help="Number of consecutive nights (default: 10)")
    parser.add_argument("--out", required=True, help="Output JSON path (e.g. soak.json)")
    args = parser.parse_args(argv)

    if args.nights < 1:
        print("ERROR: --nights must be >= 1", file=sys.stderr)
        return 2

    report = run_soak(seed=args.seed, nights=args.nights)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["crashes"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
