# Qwen4-Max-Preview Independent Review (phase=1)
- Timestamp (UTC): 2026-11-20T09:26:25.485622+00:00
- Audited diff base: `f0b40c3`
- Model: `qwen4-max-preview`
- Token usage: `{"prompt_tokens": 40202, "total_tokens": 46603, "completion_tokens": 6401, "prompt_tokens_details": {"cached_tokens": 1280, "text_tokens": 40202}, "completion_tokens_details": {"reasoning_tokens": 4982}}`

## Review — Phase 1 (`f0b40c3` → `fe15073`)

Architecture is sound (single pure `Simulation` shared by CLI + WS server; AST import-boundary test is a real guard). But several contract deviations were rationalized into `assumptions.md` rather than resolved, and the review gate was widened in the same commit that adds the largest unreviewed artifact.

### 1. Contract mismatches (spec text is explicit)

- **Y-gating violates "All `tuning` radii measured on XZ plane (`distance_xz <= r`)"** (`sim.py:_step_mote_pickup`, `_step_shade_touch`). Spec §B leaves no room for `abs(dy) <= 1.5`. It is *not* harmless dead code: jump apex is `7²/(2·20) = 1.225 m`, so the guard never fires from normal jumps — it only fires for **scenario-supplied `player.pos` with `y > 1.5`** (a legal §D input), where a contract-conformant reference picks the mote and this sim does not. Worse, it's asymmetric: pickup uses `player.y - mote.y`, shade touch uses `abs(player.y)` and ignores `shade.pos[1]` even though spec says shade pos = center. Either implement pure XZ or get the deviation approved — recording it in your own assumptions file is not approval.
- **Scenario `lit` is silently overridden**: `_apply_scenario` ends with `if lan.deposited >= lantern_cost: lan.lit = True`. A scenario `{"id":"L1","lit":false,"deposited":10}` (both fields explicitly supported by §D) comes out lit. Explicit scenario fields must win. Untested.
- **No terminal snapshot on early stop.** Win at tick 26 with default cadence 10 → snapshots `[0,10,20]`, all `"playing"`; the won state appears only in `end`. §E defines `state:"playing|won|lost"` for snapshots, so a grader reading the last snapshot sees the wrong result. `test_headless_cli_determinism...` *codifies* this (`assertEqual(win_snaps,[0,10,20])`) instead of questioning it. Emit a final snapshot at the terminal tick.
- **`end.state` may be `"playing"`** — §E says `"won|lost"`. Documented, but still a literal schema violation; at minimum flag it as an open question to the board, not a settled assumption.
- **Spec §C rotation typo (`z' = -x·sinθ + z·sinθ`) was silently corrected to `cosθ`.** Correct engineering call, but it is *not* in the "Contract nuances recorded" list, and the test asserts only your interpretation. Document it.
- `ready_tick = sim_tick + 1` is dead code (spawns/drops both happen after the pickup phase in the same tick) — an invented rule with no effect; remove it rather than list it as a contract nuance.

### 2. Determinism / coupling
No rendering or wall-clock coupling in `sim.py`; RNG is a single seeded `Random`, all iteration is over lists, JSON key order is insertion-stable. Cross-process byte-identity is genuinely exercised. This part is fine.

### 3. Weak / missing tests
- `test_headless_full_night_performance_budget` asserts only `type=="end"` and `<10 s` — near-tautological; it never asserts 18000 steps ran or the resulting state.
- **Safe-radius test is rigged**: player placed exactly at L1 center, so shade at 6 m can never be within 1 m. The real hole is untested: player at 5.9 m from a lit lantern, shade clamped to 6.0 m on the same bearing → `distance_xz ≈ 0.1` → **player is hit while standing inside the "safe" zone**. Either fix the semantics or test/justify it.
- No test for **loss by `no_flames`** (fall test stops at 1 flame), no test that `shade_spawned` is ever emitted or that the spawn schedule/cap holds, no test for mote auto-spawn/`MOTE_MAX_ACTIVE`, no test rejecting out-of-range `move`, no test for `--snapshot-every 0`, no test for scenario `time_left_s` override arithmetic, no test of the WS `restart` path (the "replay" deliverable).
- Pulse test mutates `sim.shades` / `sim.player.carried` mid-run — white-box patching hides the very cooldown/cost interaction it claims to verify.

### 4. Verification evidence / supply chain
- `tools/qwen_review.py` now excludes `:!web/vendor/`. The single largest new artifact (vendored minified Three.js) is removed from independent review in the same commit that introduces it. Self-serving scope reduction.
- `CREDITS.md` asserts a SHA-256 for `three.min.js`; **nothing verifies it** (no test, no verify step). Add a hash assertion.
- **No Phase-1 clean-clone proof.** README claims offline-capable vendored assets; the only clean-clone evidence in the matrix is CP0. If `web/vendor/` is ignored/untracked, a fresh clone 404s and the local test still passes. Prove it.
- Minor: WS upgrade accepts any `Origin` (cross-origin WS to `127.0.0.1` is not CORS-blocked) and ignores fragmentation/`Sec-WebSocket-Version`. Low risk for a local game, but note it.

### Required before sign-off
1. Remove Y-gating (or obtain explicit spec amendment) and make scenario `lit` authoritative.
2. Emit a terminal snapshot; resolve `end.state` schema with the board.
3. Add tests: `no_flames` loss, `shade_spawned`, safe-radius boundary, scenario `lit:false` + `deposited>=cost`, replay/restart.
4. Restore `web/vendor/` to the review diff (or hash-verify it in `verify.py`) and add a Phase-1 clean-clone log.

VERDICT: BLOCKER - Contract deviations (Y-gated pickup/hit vs explicit XZ-only rule, scenario `lit` overridden, no terminal snapshot) plus vendored `web/vendor/` excluded from review with no hash check or Phase-1 clean-clone proof.
