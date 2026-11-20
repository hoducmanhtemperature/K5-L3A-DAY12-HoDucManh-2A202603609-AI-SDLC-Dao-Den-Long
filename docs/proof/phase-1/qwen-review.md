# Qwen4-Max-Preview Independent Review (phase=1)
- Timestamp (UTC): 2026-11-20T09:19:06.826279+00:00
- Audited diff base: `f0b40c3`
- Model: `qwen4-max-preview`
- Token usage: `{"prompt_tokens": 37245, "total_tokens": 45435, "completion_tokens": 8190, "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 37245}, "completion_tokens_details": {"reasoning_tokens": 6338}}`

# Independent Review — Phase 1 (`f0b40c3` → `4ca5dd5`)

Overall the architecture is right: one pure `Simulation` shared by CLI and WS server, no rendering imports in `src/game/`, seeded `random.Random`, no wall-clock/hash-order dependence in the sim. But the *verification* around it is materially weaker than the log claims, and several contract clauses are simply untested.

## 1. Requirement / Contract mismatches & invented features

- **`scenario.time_left_s` is an invented schema field** (`sim.py parse_scenario_dict`, `_apply_scenario`). Spec §D lists exactly `player / random_motes / random_shades / lanterns / motes / shades`. Worse, it breaks the §B invariant `time_left_s = night1_duration_s - steps_executed/60` — the shipped fixture `p1_win_night1.json` sets `120.0`, so the "proof" scenario runs under a *different* time model than the contract. Not documented in `assumptions.md`.
- **Vertical gates on XZ radii.** §B: "All `tuning` radii measured on XZ plane (`distance_xz <= r`)". `_step_mote_pickup` adds `abs(player.y - mote.y) <= 1.5`; `_step_shade_touch` adds `abs(player.y) <= 1.5`. Latent in normal play (jump apex = 7²/40 = 1.225 m < 1.5), but reachable via `scenario.player.pos[1]` — a spec-conformant reference would pick up / hit, this one won't. Undocumented.
- **`Mote.ready_tick = sim_tick + 1`** for spawned motes is another invented, undocumented rule that shifts pickup by one tick.
- Spec §C has a typo (`z' = -x·sinθ + z·sinθ`); the sim uses `cos`. Correct choice, but this is exactly the kind of ambiguity `assumptions.md` is supposed to record — it doesn't.
- §E `end.state` is `"won|lost"`, yet a `--ticks`-bounded run emits `"playing"` (the 360-tick test does this). Defensible, but unrecorded.
- No terminal snapshot is emitted when the run ends on a tick not divisible by `--snapshot-every`; the last snapshot can be 9 ticks stale at `won`/`lost`.

## 2. Coupling / determinism

- Sim boundary is clean; `render_state()` is additive and never in JSONL. Good.
- **The WS server bypasses contract validation entirely**: `latest_input` is fed raw into `sim.step()` without `parse_inputs_dict`. `int(msg.get("seed", ...))` on a non-numeric client value raises inside `reader()`, killing the thread *without* `stop_flag.set()` (the trailing `set()` is skipped on exception) → main loop spins on a dead socket. `sim.__init__(...)` re-init on a live object is a hack, not a reset API.
- `read_ws_frame` has no payload-length cap; a declared 2^64 length drives an unbounded `recv_exact` allocation. No `Origin` check on `/ws` (any page in the user's browser can drive the local sim). Localhost-only, so low severity — but unbounded allocation + no origin check should be noted, not ignored.

## 3. Weak / missing tests (the core problem)

Mandatory §B/§C/§E clauses with **zero assertions anywhere**:
- **Malformed `--scenario` → exit 2.** Only malformed *inputs* is tested. Spec requires both.
- **Event `tick = k+1`.** Tests check `e["name"]` only, never `e["tick"]`. Off-by-one in event ticks would pass everything.
- **Snapshot cadence / default `--snapshot-every 10`.** Never asserted (the CLI test passes `30` explicitly and only checks line 0 and line -1).
- **`time_left_s` formula**, coordinate 3-dp rounding, `motes_active`, early-stop-on-win via the CLI (`end.ticks < --ticks`), `--ticks 0`, `random_motes:false` actually suppressing spawns over a long run.

Tests that are near-tautological or conflated:
- `test_shade_hit_..._safe_radius`: asserts `dist >= 5.999` immediately after `_enforce_safe_radius` hard-teleports the shade to exactly `sr`. It tests the clamp against itself.
- `test_pulse_...cooldown_and_cost`: after 15 ticks, `carried == 1 < 3` **and** cooldown active — the negative assertion can't distinguish them. Pulse is never re-fired after cooldown expiry, and `pulse_radius` boundary (5.0 vs 5.01) is untested.
- `test_headless_full_night_performance_budget`: 18,000 ticks, asserts only `type == "end"` and wall-clock < 10 s. A sim that does nothing passes. Also a flaky timing assertion in CI.
- `test_contract_json_matches_phase1_tuning`: equality against the same-authored `PHASE1_TUNING`. If a required key is missing from *both*, it passes. Assert the spec's key set explicitly.
- `test_sim_module_is_decoupled...`: blocklist misses `subprocess`, `importlib`, `json`, `pathlib`, `numpy`; `__import__("socket")` is invisible to it.
- **Dead/garbage code** in `test_interact_held_...`: `sim.motes.append(... type(sim.lanterns[0])("M9", [...]))` constructs a **`Lantern`** into the motes list, then the very next line overwrites `sim.motes`. Remove it; it's evidence of code the agent didn't re-read.
- No golden/expected JSONL fixture is committed. Two identical runs prove determinism, not correctness.

## 4. Harness / evidence

- **`verify.py check_phase_requirements` fails open.** The new determinism gate is wrapped in `if root == ROOT:` *and* `if sc_path.is_file() and in_path.is_file():`. Delete/rename either fixture → gate silently returns `True, []`. It also hardcodes phase-1 fixtures for **any** phase > 1, and never validates `contract_version` or the tuning key set. Because of `root == ROOT`, the hermetic smoke test never executes the new branch at all — the added gate has **no test coverage**. This is precisely the "always pass" pattern.
- `tools/qwen_review.py` now excludes `web/vendor/` on top of `docs/proof/`. A ~600 KB minified third-party blob is therefore unreviewed, with **no LICENSE text and no integrity checksum** committed. CREDITS asserts MIT r128; nothing in-repo substantiates it. Add `web/vendor/LICENSE.three.txt` + a SHA-256 pin.
- Secret scan: no keys/ENV in the diff. `docs/proof/phase-1/verify.log` is referenced by the matrix but excluded from the diff by design — accepted on the strength of the pasted log only.

## Required before re-review
1. Make the phase gate fail closed (missing fixtures = failure), cover it in a hermetic test, and key fixtures to the actual phase.
2. Add tests for: malformed scenario → 2, event `tick == k+1`, snapshot cadence + default 10, `time_left_s` formula, CLI early-stop on win, pulse re-fire after cooldown with sufficient motes, radius boundaries (`<=` vs `<`).
3. Remove the invented `scenario.time_left_s` (or document it and stop using it in the proof fixture); document or drop the Y-gates and `ready_tick`.
4. Delete the dead `Lantern`-into-motes line; route WS input through `parse_inputs_dict` and fix the reader-thread exception path.
5. Vendor license + checksum for `three.min.js`.

VERDICT: BLOCKER - verification gate fails open/untested and mandatory contract clauses (scenario exit 2, event tick=k+1, snapshot cadence, time_left formula) are unasserted; invented `scenario.time_left_s` breaks the §B time invariant in the shipped proof fixture.
