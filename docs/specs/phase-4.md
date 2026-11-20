# Phase 4 Specification — Ticket-04 · Bình minh v1.0.0 (Test Contract v1.3)

Source: `1111.html` (Ticket-04 · Bình minh v1.0.0).

## 1. Benchmark Mode (`bench_cmd`)
- Command: `<bench_cmd> --seed 42 --duration 30 --out bench.json`
- 1280×720 window (not fullscreen), vsync off if supported.
- Loads Night 1 with 200 Shades in `wander` (seed 42), 100 motes, lanterns L1–L3 lit with `fuel = 100`.
- Disables spawning, damage, mote pickup, fuel decay, and night end; Shades still move in `wander`.
- Player stationary at `(0, 0, 0)`. Camera orbits `(0, 0, 0)` at radius `30 m`, height `Y = 15 m`, starting at `0°` `(30, 15, 0)`, CCW, `15 s/rev`.
- 3 s warmup (excluded), then measure `--duration` seconds and exit `0`.
- Output `bench.json`:
  - `contract_version: "1.3"`, `avg_fps`, `p1_low_fps`, `frame_ms_p95`, `frames`, `load_ms`, `peak_mem_mb`, `vsync_off`, `renderer`, `os`.
  - Thresholds (on grading machine): `avg_fps >= 60`, `p1_low_fps >= 30`, `load_ms <= 10000`.

## 2. Soak Test (`soak_cmd`)
- Command: `<soak_cmd> --seed 7 --nights 10 --out soak.json`
- Runs 10 consecutive nights headless in a single process (cycling Night 1 → 2 → 3), Night `i` uses seed `7 + i`, running until won/lost or standard night duration.
- Seeded random input: every 30 ticks pick new move direction; each tick 5% jump, 3% dash, 2% pulse, 10% interact.
- Output `soak.json`: `{nights, crashes, results, mem_start_mb, mem_end_mb, duration_s}`.
- Thresholds: `crashes == 0`, `mem_end_mb <= 1.2 * mem_start_mb`.

## 3. Local Leaderboard
- Prompt for name after Dawn Victory (Night 3 win) or Loss on any night.
- Name: 3–12 chars `[A-Za-z0-9_]` (Vietnamese letters optional bonus).
- Fields: `name`, `score` (sum of won nights' scores), `nights_won` (`0..3`), `achieved_at` (ISO-8601 with timezone), `seed`.
- Keep top 10 sorted by `score` descending (tie: earlier `achieved_at` first), persisted on local disk, viewable from main menu.
- Export CLI: `<run_cmd> --export-leaderboard out.json` outputs `{"entries": [...]}` in rank order and exits `0`.

## 4. Accessibility
- Key rebinding: 4-way move, jump, dash, interact, pulse, pause, with conflict detection, reset-to-defaults button, persisted.
- Visual subtitles/indicators: Shade spawn (+ screen-edge directional arrow), wind warning, last 10 s countdown, low-fuel lantern (`fuel < 30`).
- Reduced Motion toggle (disables camera shake and screen flashes).
- UI font size `>= 18 px` at 1280×720 + Large Text (`×1.25`) toggle.

## 5. Packaging, Contract v1.3, Retro & Release
- `contract_version: "1.3"`, `game.contract.json` adds `bench_cmd` and `soak_cmd`.
- Clean clone → follow `README.md` (≤ 3 commands) → playable.
- `CHANGELOG.md` (all 4 phases), `CREDITS.md`, `LICENSE`, `Dockerfile`, committed `bench.json` & `soak.json`, 4-phase retro (`docs/notes/retro.md`), tags `phase-4` & Release `v1.0.0`.
