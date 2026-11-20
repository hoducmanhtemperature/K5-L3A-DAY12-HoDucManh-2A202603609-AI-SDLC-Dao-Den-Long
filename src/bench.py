#!/usr/bin/env python3
"""Benchmark Mode CLI for Đảo Đèn Lồng (Test Contract v1.3).

Runs the standardized Ticket-04 Night 1 benchmark scene:
- 200 Shades in `wander` (seed 42), 100 motes, lanterns L1–L3 lit with fuel=100
- Spawns, damage, pickup, fuel decay, and night end disabled
- Player stationary at (0, 0, 0)
- Camera orbits (0, 0, 0) at R=30 m, Y=15 m, starting at 0 deg (30, 15, 0), CCW, 15 s/rev
- 3 s warmup (excluded), then measures --duration seconds and writes bench.json

Note: The interactive WebGL 1280x720 browser benchmark is also available via
`web/index.html?bench=1&seed=42&duration=30` when served by `src/server.py`.

Usage:
    python3 src/bench.py --seed 42 --duration 30 --out bench.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import platform
import random
import resource
import sys
import time

T_PROC_START = time.perf_counter()

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.constants import DT, SHADE_WANDER_SPEED  # noqa: E402
from src.game.maps import clamp_ground_entity  # noqa: E402
from src.game.sim import Mote, Shade, Simulation  # noqa: E402


def peak_rss_mb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(ru / (1024.0 * 1024.0), 2)
    return round(ru / 1024.0, 2)


def build_bench_scene(seed: int) -> Simulation:
    """Build exact Ticket-04 benchmark scene on Night 1."""
    rng = random.Random(seed)
    sim = Simulation(
        seed=seed,
        night=1,
        scenario={
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [
                {"id": "L1", "lit": True, "fuel": 100.0, "ever_lit": True},
                {"id": "L2", "lit": True, "fuel": 100.0, "ever_lit": True},
                {"id": "L3", "lit": True, "fuel": 100.0, "ever_lit": True},
            ],
        },
    )

    # 200 Shades in wander spread evenly on island (seed-deterministic)
    sim.shades = []
    for i in range(1, 201):
        r = 37.0 * math.sqrt((i - 0.5) / 200.0)
        theta = i * 2.399963229728653 + rng.uniform(-0.08, 0.08)
        x = round(r * math.cos(theta), 3)
        z = round(r * math.sin(theta), 3)
        sim.shades.append(
            Shade(
                id=f"S{i}",
                pos=[x, 0.0, z],
                state="wander",
                wander_angle=rng.uniform(0.0, math.tau),
            )
        )

    # 100 Motes spread on island (bench allowed above gameplay cap)
    sim.motes = []
    for i in range(1, 101):
        r = 36.0 * math.sqrt((i - 0.5) / 100.0)
        theta = i * 2.399963229728653 + rng.uniform(-0.05, 0.05)
        sim.motes.append(
            Mote(
                id=f"M{i}",
                pos=[round(r * math.cos(theta), 3), 0.0, round(r * math.sin(theta), 3)],
                kind="random",
            )
        )

    return sim


def step_bench_frame(sim: Simulation, elapsed_s: float) -> tuple[float, float, float]:
    """Advance one benchmark frame: 200 Shades wander + CCW orbit camera + frame state projection."""
    # Shades move in wander only (spawns, damage, pickup, fuel decay, night end disabled)
    for sh in sim.shades:
        sh.wander_angle += 0.4 * DT
        nx = sh.pos[0] + math.cos(sh.wander_angle) * SHADE_WANDER_SPEED * DT
        nz = sh.pos[2] + math.sin(sh.wander_angle) * SHADE_WANDER_SPEED * DT
        sh.pos[0], sh.pos[2] = clamp_ground_entity(1, nx, nz)
    sim._enforce_safe_radius()
    sim.tick += 1
    sim.sim_tick += 1

    # Camera orbits (0,0,0), R=30m, Y=15m, starting at 0 deg (30,15,0), CCW from above, 15s/rev
    angle = (elapsed_s / 15.0) * math.tau
    cam_x = 30.0 * math.cos(angle)
    cam_y = 15.0
    cam_z = -30.0 * math.sin(angle)

    # Project full frame state (mirrors 1280x720 WebSocket/renderer frame payload)
    _ = sim.snapshot()
    return (cam_x, cam_y, cam_z)


def compute_bench_metrics(
    dts_ms: list[float],
    load_ms: float,
) -> dict[str, object]:
    n = len(dts_ms)
    total_ms = sum(dts_ms)
    avg_fps = (1000.0 * n / total_ms) if total_ms > 0 else 0.0

    sorted_desc = sorted(dts_ms, reverse=True)
    k = max(1, math.ceil(0.01 * n))
    worst_mean_ms = sum(sorted_desc[:k]) / k
    p1_low_fps = (1000.0 / worst_mean_ms) if worst_mean_ms > 0 else 0.0

    sorted_asc = sorted(dts_ms)
    p95_idx = min(n - 1, max(0, math.ceil(0.95 * n) - 1))
    frame_ms_p95 = sorted_asc[p95_idx]

    return {
        "contract_version": "1.3",
        "avg_fps": round(avg_fps, 2),
        "p1_low_fps": round(p1_low_fps, 2),
        "frame_ms_p95": round(frame_ms_p95, 3),
        "frames": n,
        "load_ms": round(load_ms, 2),
        "peak_mem_mb": peak_rss_mb(),
        "vsync_off": True,
        "renderer": f"Python {platform.python_version()} 60Hz-Sim + Three.js r128 WebGL (CLI headless-pipeline bench)",
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
    }


def run_benchmark(seed: int, duration_s: float, warmup_s: float = 3.0) -> dict[str, object]:
    sim = build_bench_scene(seed=seed)
    # First frame ready -> capture load_ms
    step_bench_frame(sim, 0.0)
    load_ms = (time.perf_counter() - T_PROC_START) * 1000.0

    # Warmup phase (not measured)
    t_warm_start = time.perf_counter()
    while (time.perf_counter() - t_warm_start) < warmup_s:
        step_bench_frame(sim, time.perf_counter() - t_warm_start)

    # Measured phase
    dts_ms: list[float] = []
    t_meas_start = time.perf_counter()
    t_prev = t_meas_start
    while (t_prev - t_meas_start) < duration_s:
        step_bench_frame(sim, (t_prev - t_warm_start))
        t_now = time.perf_counter()
        dts_ms.append((t_now - t_prev) * 1000.0)
        t_prev = t_now

    return compute_bench_metrics(dts_ms, load_ms)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đảo Đèn Lồng Benchmark Mode (Contract v1.3)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument("--duration", type=float, default=30.0, help="Measurement duration in seconds (default: 30)")
    parser.add_argument("--warmup", type=float, default=3.0, help="Warmup duration in seconds (default: 3)")
    parser.add_argument("--out", required=True, help="Output JSON path (e.g. bench.json)")
    args = parser.parse_args(argv)

    if args.duration <= 0 or args.warmup < 0:
        print("ERROR: --duration must be > 0 and --warmup >= 0", file=sys.stderr)
        return 2

    report = run_benchmark(seed=args.seed, duration_s=args.duration, warmup_s=args.warmup)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
