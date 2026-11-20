# Changelog

All notable changes to **Đảo Đèn Lồng** across lab phases.

## [v1.0.0 / phase-4] — Ticket-04 "Bình minh v1.0.0" (Test Contract v1.3)
### Added
- **Benchmark Mode (`bench_cmd`):** `python3 src/bench.py --seed 42 --duration 30 --out bench.json` (plus interactive WebGL 1280×720 `?bench=1` mode in `web/app.js`), running Night 1 with 200 wander Shades, 100 motes, L1–L3 lit at fuel 100, CCW circular orbit camera (R=30 m, Y=15 m, 15 s/rev), 3 s warmup + duration measurement, outputting `avg_fps`, `p1_low_fps`, `frame_ms_p95`, `frames`, `load_ms`, `peak_mem_mb`, `vsync_off`, `renderer`, `os`.
- **Soak Test (`soak_cmd`):** `python3 src/soak.py --seed 7 --nights 10 --out soak.json`, executing 10 consecutive headless nights (1→2→3 cycling, seed `7+i`) in one process with seeded random inputs and RSS leak checks (`crashes == 0`, `mem_end_mb <= 1.2 * mem_start_mb`).
- **Local Persistent Leaderboard:** Top-10 local disk leaderboard (`src/game/leaderboard.py`, `GET/POST /api/leaderboard`, main-menu viewer, Dawn/Loss name entry `3–12` chars `[A-Za-z0-9_]` + Vietnamese letters), sorted by score desc (tie: earlier `achieved_at`), plus CLI `python3 src/server.py --export-leaderboard out.json`.
- **Accessibility:** Full key rebinding (9 actions) with duplicate-key detection and "Khôi phục mặc định" persisted in `localStorage`; visual subtitles & screen-edge Shade spawn directional arrow; Reduced Motion toggle; `>= 18 px` base UI font size at 1280×720 + Large Text (`×1.25`) toggle.
- **Release Packaging:** `Dockerfile`, `game.contract.json` v1.3 (`bench_cmd`, `soak_cmd`), committed `bench.json` & `soak.json`, complete 4-phase retro (`docs/notes/retro.md`), and updated `README.md` / `CREDITS.md`.

## [phase-3] — Ticket-03 "Đèn cạn dầu" (Test Contract v1.2)
### Breaking Changes
- **[REPLACED] Win condition:** Lighting all lanterns no longer ends the night early (`all_lit` removed). Players must survive until dawn (`time_left_s == 0`) with at least `ceil(0.6 * total)` lit lanterns (`dawn_survived`: 3/5 Night 1, 4/6 Night 2, 5/7 Night 3).
- **[REPLACED] Night durations:** Night 1/2/3 changed from `300/330/360 s` to `240/270/300 s`.
- **[REPLACED] Permanent lanterns → Fuel system:** Lit lanterns start at `fuel = 100`, decay `1.0/s` (tracked as integer `1/60`), extinguish at `<= 0` (`lantern_out`), and can be refueled (`+10` fuel/mote) or relit for `5` motes (`relight: true`).
- **[REPLACED] Safe zone & Shade AI:** Lit lanterns with `fuel < 30` lose their 6 m safe zone; `wander` Shades move to weak lanterns and enter `drain` state (`5 fuel/s`, emitting `fuel_drain` every 60 ticks).
- **[REPLACED] Scoring:** `+5`/mote deposited or refueled (was `+10`), `+100` first light, `+40` relight, `+15` pulsing a draining Shade (`+5` normal), dawn win bonus `+50 + floor(fuel)` per lit lantern + `+50` per Flame; time bonus removed.

### Added
- Progressive carry capacity: `min(20, 10 + 2 * successful_lights)`.
- Colorblind mode ("Bảng màu dễ phân biệt", saved in `localStorage`) and non-color visual cues for unlit/low-fuel lanterns.
- ADR: `docs/adr/ADR-001-lantern-fuel-and-dawn-survival.md`.

## [phase-2] — Ticket-02 "Ba hòn đảo" (Test Contract v1.1)
- Standardized physics, 12-step tick order, and 3 Nights (Đảo Bến, Đảo Cau, Đảo Chuông).
- Added Dash (`Lướt`), Jump Pads, Gió Lạc (`Drifters`), Bùa Gió (`Charms`), Night 3 Strong Wind, Pause/Resume, persistent settings, full HUD + off-screen lantern arrow, and TA clarifications (`spawning` 60 ticks, Night 3 start `(0,0,-15)`, `night_start` tick 1).

## [phase-1] — PRD-0 (Test Contract v1.0)
- Implemented pure Python 60-Hz simulation (`src/game/sim.py`), headless CLI (`src/headless.py`), and Three.js r128 MIT 3D browser renderer over stdlib HTTP+WebSocket (`src/server.py`, `web/`).

## [cp0] — Checkpoint 0
- Initialized AI SDLC harness (`AGENTS.md`, skills, `.githooks/pre-commit`, CI, `tools/verify.py`, independent `qwen4-max-preview` reviewer `tools/qwen_review.py`).
