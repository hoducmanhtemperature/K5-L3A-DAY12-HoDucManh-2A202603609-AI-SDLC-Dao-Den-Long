# Changelog

All notable changes to **Đảo Đèn Lồng** across lab phases.

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
