# Evaluation & Retrospective

## Phase-by-Phase Check-in
### Checkpoint 0
- **Achieved:** Secret protection (`.gitignore`, index+worktree+binary ASCII scanner, `.githooks/pre-commit`), CI workflow, fail-closed `tools/verify.py`, independent `qwen4-max-preview` reviewer (`VERDICT: PASS`), and clean-clone proof.
- **Lesson:** Over-iterated CP0 harness (~11 Qwen runs); shifted to leaner targeted reviews in Phases 1–2 to conserve tokens.

### Phase 1 (`tag: phase-1`)
- **Achieved:** Decoupled pure Python 60-Hz simulation (`src/game/sim.py`), Test Contract v1.0 (`game.contract.json`, `src/headless.py`), Three.js r128 MIT 3D frontend over stdlib HTTP+WebSocket (`src/server.py`, `web/`), 19/19 tests + clean-clone proof.
- **AI Mistakes Caught:** `qwen4-max-preview` caught fail-open `verify.py` phase gate, missing malformed-scenario exit-2 test, missing terminal snapshot on early win, and Y-gate vs pure-XZ v1.0 rule mismatch.

### Phase 2 (`tag: phase-2`)
- **Achieved:** Standardized Ticket-02 numbers & mandatory 12-step tick order, 3 Nights (Đảo Bến, Đảo Cau with bridge & jump pads, Đảo Chuông with 3 tiers, ramps, bell tower & strong wind), Dash, Bùa Gió, Gió Lạc, Pause/Resume, persistent settings, full HUD + off-screen lantern arrow, Test Contract v1.1, 27/27 tests passing including Phase 1 regression.
- **Phase 1 Regression Check:** Phase 1 tests caught two real issues immediately during Phase 2 integration (raw list motes in `_apply_scenario` and Ticket-02's 3D pulse origin `feet + 0.8 m` vs Phase 1's XZ check). Updated Phase 1 tests with explicit reasons in `docs/notes/assumptions.md`.

## Final Project Retro
- *(To be completed after Phase 3 & Phase 4 at Checkpoint 5.)*
