# Evaluation & Retrospective — Đảo Đèn Lồng (Phases 0–4 / v1.0.0)

## 1. Phase-by-Phase Evaluation Summary

| Phase | Tag | Contract | Tests Passing | Key Deliverables |
|---|---|---|---:|---|
| Checkpoint 0 | *(init)* | — | 7 / 7 | AI SDLC harness (`AGENTS.md`, skills, `.githooks/pre-commit`, CI, `tools/verify.py`, independent `qwen4-max-preview` reviewer `tools/qwen_review.py`), secret scanning, clean-clone proof. |
| Phase 1 | `phase-1` | v1.0 | 19 / 19 | Decoupled pure Python 60-Hz simulation (`src/game/sim.py`), headless CLI (`src/headless.py`), vendored Three.js r128 MIT 3D browser renderer over stdlib HTTP+WebSocket (`src/server.py`, `web/`). |
| Phase 2 | `phase-2` | v1.1 | 28 / 28 | Standardized 12-step tick order, 3 Nights (Đảo Bến, Đảo Cau w/ bridge & jump pads, Đảo Chuông w/ 3 tiers, ramps, bell tower & wind), Dash, Bùa Gió, Gió Lạc, Pause/Resume, TA clarifications (`spawning` 60 ticks, Night 3 start `(0,0,-15)`, `night_start` tick 1). |
| Phase 3 | `phase-3` | v1.2 | 35 / 35 | Breaking redesign (`ADR-001`): exact integer `fuel_60` (`1/60` units) decay/refuel/relight, safe-zone loss at `fuel < 30`, Shade `drain` (`5/s`, `fuel_drain`), Dawn Survival win (`dawn_survived`), progressive capacity (`10..20`), Colorblind mode. |
| Phase 4 | `phase-4` / `v1.0.0` | v1.3 | 40 / 40 | Benchmark mode (`src/bench.py` + `?bench=1` WebGL), 10-night Soak test (`src/soak.py`), persistent Top-10 Leaderboard (`--export-leaderboard` + HTTP API + UI), Accessibility (key rebind, subtitles, Shade arrow, Reduced Motion, `>=18px` + Large Text), `Dockerfile`, `bench.json` & `soak.json`. |

## 2. What Worked Well vs. What Did Not Work Well with AI
- **Worked well:**
  - **Strict decoupling (`src/game/sim.py` pure stdlib, zero I/O or rendering imports):** Enforced by an AST unit test from Phase 1 onward. This made adding Nights 2–3, integer `fuel_60` arithmetic, Dawn Survival, headless soak testing, and deterministic replay fast and bug-free without ever desyncing the 3D view.
  - **Single-command verification gate (`tools/verify.py`):** Running unit tests, secret scanning, and headless determinism checks in one fail-closed script caught regressions immediately.
  - **Recording explicit ADRs and assumption updates (`ADR-001`, `docs/notes/assumptions.md`):** Prevented silent drift when Ticket-02 and Ticket-03 intentionally broke earlier rules (e.g., pure-XZ → 3D pulse origin; early `all_lit` win → Dawn Survival).
- **Did not work as smoothly:**
  - **Over-iterating CP0 harness early:** Spending ~11 independent Qwen review cycles on CP0 edge cases consumed disproportionate tokens before any game code existed. Switching to targeted, phase-boundary reviews in Phases 1–4 saved significant token budget.
  - **Implicit tick-order interactions:** Even with a written 12-step tick order, Step 2 (`fuel_60 -= 1`) running before Step 5 (`interact`) caused a subtle bug where a `fuel == 100.0` lantern decayed to `5999/60` before refuel ran. Automated unit tests caught this immediately.

## 3. Concrete AI Mistakes & How They Were Caught
1. **Fail-open phase verification & missing malformed-scenario exit-2 test (Phase 1):** Caught by independent `qwen4-max-preview` review (`tools/qwen_review.py --strict`), which flagged that missing `docs/specs/phase-N.md` or malformed scenario JSON was not strictly rejected.
2. **Phase 1 regression on raw list motes & 3D Pulse origin (Phase 2):** Caught by running `tests/test_phase1_sim.py` immediately after Phase 2 edits — `_apply_scenario` assumed dict motes and broke raw `[[x,y,z]]` motes.
3. **Full-lantern refuel off-by-1/60 bug (Phase 3):** Caught by `test_refuel_exact_ceil_motes_and_full_lantern_skipped` — Step 2 decayed `fuel_60` from `6000` to `5999` before Step 5 checked `< 6000`. Fixed cleanly with `fuel_60 < FUEL_MAX_60 - FUEL_DECAY_PER_TICK_60`.
4. **C-quoted Unicode filenames in `git ls-files` (CP0):** Caught by `TestHarnessSmoke` when testing non-ASCII filenames in secret scanning; fixed with `-z` NUL-delimited git output.

## 4. Which Harness Pieces Helped Most
1. **`tools/verify.py` + `.githooks/pre-commit`:** Highest ROI. Prevented accidental secret leaks (`ENV`), caught skipped/broken tests, and proved byte-identical headless determinism on every phase.
2. **`AGENTS.md` + `docs/notes/assumptions.md`:** Kept contract rules, tick order, and breaking-change test updates explicit across long sessions and context compactions.
3. **`tools/qwen_review.py` (`qwen4-max-preview`):** Valuable independent second pair of eyes at phase boundaries (catching fail-open paths and contract nuances that the author model overlooked).

## 5. Estimated AI Token Usage & Token-Saving Practices
- **Independent Reviewer (`qwen4-max-preview`) logged in `docs/notes/token-log.jsonl`:** ~11 CP0 audit calls + Phase 1 & Phase 4 strict diff audits (exact per-call prompt/completion/total token counts are recorded in `docs/notes/token-log.jsonl` and `docs/notes/ai-log.md`).
- **Token-saving practices applied:**
  - Zero-dependency Python stdlib + vendored Three.js architecture avoided long build/dependency debug loops.
  - Filtered `docs/proof/` out of review diffs and ran `qwen_review.py` only after local `verify.py` passed.
  - Reused the same `Simulation` engine for headless CLI, WebSocket 3D server, Soak test, and Benchmark CLI instead of maintaining duplicate game logic.

## 6. What We Would Change If Starting Over
- Cap CP0 harness polishing to 2 review iterations so more budget goes to gameplay & polish.
- Add a headless-browser screenshot/WebGL harness (e.g., Playwright/Chromium) in CI if available on the host so browser WebGL `bench.json` and visual UI regressions are captured automatically alongside the Python simulation tests.
