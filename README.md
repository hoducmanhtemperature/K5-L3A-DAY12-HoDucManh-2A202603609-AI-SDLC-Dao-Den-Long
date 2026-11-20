# Đảo Đèn Lồng — Release `v1.0.0` (Test Contract v1.3)

**Video demo (3:23):** [docs/demo/demo_montage.mp4](docs/demo/demo_montage.mp4)

A 3D third-person fairy-tale survival game built across 4 AI SDLC phases (`phase-1` → `phase-4` / `v1.0.0`) with a deterministic 60-Hz Python simulation core and a zero-dependency Three.js WebGL renderer.

## System Requirements
- **Python 3.10+** (tested on Python 3.13, standard library only — zero `pip` installs required)
- Any modern web browser with WebGL (for the 3D interactive mode)
- Optional: Docker (see `Dockerfile`)

## Quick Start (≤ 3 commands from a clean clone)
```bash
git clone <repo-url> && cd K5-L3-LAB-Day12-AI-SDLC
python3 src/server.py
```
Open `http://127.0.0.1:8080/` in your browser to play all 3 Nights (**Đảo Bến**, **Đảo Cau**, **Đảo Chuông**).

To run with Docker:
```bash
docker build -t dao-den-long:1.0.0 .
docker run --rm -p 8080:8080 dao-den-long:1.0.0
```

## Controls (Default — All Rebindable in Settings)
- `W A S D` / Arrow keys: Move Mây (camera-relative)
- `Space`: Jump · `Shift`: Dash (`Lướt`)
- Mouse Drag / `J` `L`: Rotate camera
- `E`: Deposit motes / Refuel / Relight nearby Great Lantern
- `Q` / `F`: Light Pulse (`Tỏa Sáng`, costs 3 motes)
- `Esc` / `P`: Pause & Settings (Volume, Mouse Sensitivity, Colorblind Mode, Reduced Motion, Large Text `×1.25`, Key Rebinding)

## Scoring & Rules (Contract v1.3 / Dawn Survival)
- **Win condition:** Survive until dawn (`time_left_s == 0`) with at least `ceil(0.6 × total)` lit lanterns (`3/5` Night 1, `4/6` Night 2, `5/7` Night 3).
- **Lantern Fuel:** Lit lanterns start at `100` fuel, decay `1.0/s`, lose their `6 m` safe zone below `30` (attracting Shades to `drain` `5.0/s`), and extinguish at `0`. Refuel gives `+10` fuel/mote; relighting costs `5` motes (vs `10` first light).
- **Progressive Capacity:** Starts at `10`, `+2` per successful light/relight up to `20`.
- **Points:** `+5`/mote deposited or refueled · `+100` first light · `+40` relight · `+5` Pulse stun (`+15` on draining Shade) · Dawn Victory bonus: `+50 + floor(fuel)` per lit lantern + `+50` per remaining Flame.

## Verification, Headless, Benchmark, Soak & Leaderboard Commands
```bash
# 1. Full unit test suite + secret scan + determinism gate
python3 tools/verify.py --phase 4

# 2. Deterministic headless Test Contract v1.3 CLI
python3 src/headless.py --seed 42 --night 1 --ticks 3600 --snapshot-every 30 --out run.jsonl

# 3. Benchmark mode (Ticket-04: 200 wander Shades, 100 motes, L1-L3 lit, 3s warmup + 30s measure)
python3 src/bench.py --seed 42 --duration 30 --out bench.json
# Browser WebGL 1280x720 benchmark: open http://127.0.0.1:8080/?bench=1&seed=42&duration=30
# (Note: browser WebGL cannot turn off OS compositor VSync or read process RSS, so peak_mem_mb is null in browser mode.)

# 4. Soak test (10 consecutive nights 1->2->3 in one process, crash & RSS leak check)
python3 src/soak.py --seed 7 --nights 10 --out soak.json

# 5. Export local Top-10 Leaderboard
python3 src/server.py --export-leaderboard out.json
```

## Sáng tạo của tôi
- Procedural Web Audio night chimes & SFX (zero external audio files, offline-ready).
- Fairy-tale *nón lá* with dangling warm lantern, 3D floating fuel bars above lanterns, and progressive night sky brightening (`0.15 + 0.55 * lit/total`).
- All visual/audio additions live strictly in `web/` and never alter headless Test Contract output.

## License & Credits
MIT License — see [LICENSE](LICENSE), [CREDITS.md](CREDITS.md), [CHANGELOG.md](CHANGELOG.md), and [docs/notes/retro.md](docs/notes/retro.md).
