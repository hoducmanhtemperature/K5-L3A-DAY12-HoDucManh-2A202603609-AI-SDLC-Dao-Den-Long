# Qwen4-Max-Preview Independent Review (phase=4)
- Timestamp (UTC): 2026-11-20T10:12:37.666849+00:00
- Audited diff base: `phase-3`
- Model: `qwen4-max-preview`
- Token usage: `{"prompt_tokens": 32225, "total_tokens": 38075, "completion_tokens": 5850, "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 32225}, "completion_tokens_details": {"reasoning_tokens": 3442}}`

# Independent Review — Phase 4 (Ticket-04 / Contract v1.3)

## 1. Benchmark mode does not benchmark the game (evidence integrity)

`src/bench.py` never opens a window, never creates a GL context, never renders a frame, and never calls `sim.step()`. Per "frame" it:

- re-implements Shade wander inline (`sh.wander_angle += 0.4*DT`, cos/sin, `clamp_ground_entity`),
- calls the private `sim._enforce_safe_radius()`,
- computes camera x/y/z and **discards them** (`return` value unused),
- calls `sim.snapshot()` and throws the result away (`_ = sim.snapshot()`).

So the measured workload is a Python loop over 200 shades + a dict serialization — not the 3D game. Consequences:

- `bench.json` reports `avg_fps: 1871.08`, `p1_low_fps: 568.72`, `vsync_off: true`, `renderer: "... Three.js r128 WebGL ..."`. **No WebGL was involved and no vsync was toggled.** These are false fields in committed evidence, not conservative estimates. `avg_fps >= 60` / `p1_low >= 30` are satisfied by construction, i.e. the perf gate is unrunnable-as-specified and reported as passed.
- Spec §1 explicitly requires a 1280×720 non-fullscreen window, vsync off, and disabling *specific* subsystems (spawn/damage/pickup/fuel decay/night end) **while the game runs**. Bypassing `sim.step()` entirely satisfies those clauses vacuously and also removes chase AI, collision, pulse, wind, and the whole render path from the measurement.
- The browser `?bench=1` path is closer to spec but is a *second, divergent* implementation: hardcoded lantern positions, `2.0` shade speed literal, `39 m` clamp instead of `clamp_ground_entity`, no safe-radius enforcement, `vsync_off: false`, `peak_mem_mb: null`, and it never writes `bench.json` (only `window.__BENCH_RESULT__`). It is not `bench_cmd` and cannot produce the committed artifact.

The assumption note ("no GPU/browser in CI") is a legitimate constraint, but the honest response is a headless-render or sim-only benchmark that **labels itself sim-only** (`renderer: "headless-sim"`, `vsync_off: null/false`) and records the threshold as *not verified on grading hardware*. Claiming WebGL + vsync_off + 1871 FPS is exactly the "output sửa tay / always-pass evidence" class RULES forbids.

Also: bench shades/motes use a golden-angle spiral, not the game's seeded spawn distribution, and `contract_version` is hardcoded `"1.3"` instead of read from `game.contract.json`.

## 2. Soak evidence is near-tautological

`soak.json`: 10 nights, **all `"lost"`, `duration_s: 0.62`**. Ten full nights ≈ 186k ticks; 0.62 s is not credible for that. The random walk almost certainly drives Mây off the island repeatedly, so each night terminates in a few hundred ticks. Net effect: the "10-night soak" exercises well under a second of simulation, and `mem_end <= 1.2 * mem_start` passes trivially. Additional issues:

- `results.append(sim.state if sim.state in ("won","lost") else "lost")` **silently relabels a non-terminal/timeout night as `"lost"`** — a real failure mode (night never terminates) is masked as a normal result.
- `mem_start_mb` is sampled *after* Night 1's `Simulation` is constructed, `mem_end_mb` *after* `del sim; gc.collect()`. The baseline is biased upward and the end downward; the ratio is structurally flattered.
- No assertion anywhere that a soak night actually reached dawn, refueled, or exercised `drain`/`won` paths. `results` being uniformly `"lost"` should have been treated as a red flag, not committed as PASS.

## 3. Accessibility requirements not met / not verified

- **Font size ≥ 18 px:** base is 18px, but the new UI ships `.rebind-row {0.85rem}` (15.3px), `.rebind-error {0.85rem}`, `.small-btn {0.9rem}` (15.3px), `.lb-table {0.9rem}` (16.2px). These are UI text below the mandated floor at 1280×720. The test only asserts the literal string `"font-size: 18px"` exists in CSS — it cannot catch this.
- **Low-fuel lantern indicator (`fuel < 30`):** spec §4 lists four indicators. The diff implements spawn subtitle+arrow, wind warning, and 10 s countdown. I see **no low-fuel subtitle/indicator** added, and no assumption recording its omission. CHANGELOG quietly lists only three.
- **Reduced Motion:** implemented as a blanket `animation:none; transition:none` plus zeroing pulse-ring opacity. Spec requires disabling *camera shake and screen flashes*; neither is shown guarded in the diff. Unverified — and zeroing the pulse ring removes gameplay feedback rather than motion.
- **Shade arrow** depends on `ev.data.pos` in the `shade_spawned` event; nothing in the diff or tests confirms the sim emits `pos` there. If it doesn't, the arrow is dead code that still "passes" the string-presence test.

## 4. Key rebinding: conflict detection has real holes

Hardcoded keys remain live alongside the rebind map: `ArrowUp/Down/Left/Right`, `KeyF` (pulse), `ShiftRight` (dash), `KeyP` (pause). Therefore:

- Rebinding interact/pulse to `KeyP` or `KeyF` is **accepted** by the duplicate check (those codes aren't in `keybinds`) but double-fires pause/pulse.
- Rebinding dash away from Shift, or move away from WASD, does not actually unbind ShiftRight / arrows — "rebinding" is partial.

No test covers rebinding at all (only `btn-reset-keys` string presence).

## 5. Leaderboard correctness

- **Tie-break is lexicographic on raw ISO strings** (`str(entry["achieved_at"])`). With mixed timezone offsets this is wrong: `11:00+00:00` sorts before `12:00+07:00` despite being later. The test uses only `+07:00` offsets, so it passes while the bug ships. Parse to aware `datetime`/UTC.
- **Score inflation on replay:** `totalGameScore` and `nightsWon` are reset only by `btnMenu`. After Dawn Victory, "Chơi lại từ Đêm 1" restarts Night 1 without resetting, so a second run posts an accumulated score. Spec defines `score` as sum of won nights' scores for *that* run.
- `nights_won = Math.max(nightsWon, currentNight)` conflates "highest night won" with "count of nights won" — only coincidentally equal.
- `seed` stored is the last night's seed, not a run seed; `load_entries` accepts on-disk entries with only `name`/`score` (no name re-validation), and `refreshLeaderboard` injects `e.name` via `innerHTML` → local-file-driven HTML injection. Low severity, but validate on load and use `textContent`.
- `NAME_RE` `\u00C0-\u024F` admits `×` (U+00D7) and `÷` (U+00F7) as "Vietnamese letters".
- Dockerfile binds `0.0.0.0` with an unauthenticated write endpoint; fine for a lab, worth a note.

## 6. Test quality / evidence

- `test_bench_cli_...` runs `--duration 0.4 --warmup 0.1` (not 30/3) and asserts `avg_fps >= 60` on a non-rendering loop: always-pass.
- `test_soak_cli_...` runs **2** nights, not 10, and asserts a ratio that cannot fail at that scale.
- `test_web_accessibility_...` is six `assertIn` string checks on HTML/CSS. It verifies nothing about behavior, computed font sizes, conflict detection, or Reduced Motion.
- `test_contract_v1_3_has_bench_and_soak_cmds` asserts file *existence* for Dockerfile/LICENSE/CREDITS/CHANGELOG — packaging is not actually exercised (no `docker build`, no clean-clone run shown in this diff).
- `docs/notes/verification-matrix.md` cites `docs/proof/phase-4/verify.log` for all five P4 rows, but that file appears **neither in the diff nor in the untracked list** (only `clean-clone.log`). The cited evidence for P4-1…P4-5 is missing.
- Verification log shows **dirty tree (25 uncommitted paths)**; no evidence of `phase-4` tag or `v1.0.0` Release. Secret scan PASS is fine; sim purity test still present and sim untouched — that part is genuinely good.

## What must change before this can pass

1. Make `bench_cmd` measure the real frame pipeline (or clearly-labeled sim-only mode with `vsync_off: false/null`, honest `renderer`, and an explicit "render thresholds unverified" note). Regenerate `bench.json`; do not ship WebGL/vsync claims from a headless Python loop.
2. Fix soak so nights actually run to dawn/win/loss (constrain random input to the island or record why nights end early), stop mapping non-terminal → `"lost"`, and sample `mem_start` before any night loads.
3. Raise all UI text to ≥18px effective; add the `fuel < 30` indicator; verify Reduced Motion against actual shake/flash code paths.
4. Remove hardcoded key fallbacks or include them in conflict detection; add behavioral rebind tests.
5. Parse timestamps for tie-break; reset run score/nights_won on replay; add a mixed-offset tie test.
6. Produce the missing `docs/proof/phase-4/verify.log`, commit the tree, and show tag/Release evidence.

VERDICT: BLOCKER - bench_cmd never renders or steps the sim yet bench.json claims WebGL/vsync_off/1871 FPS (fabricated perf evidence); soak runs ~0.6s with all nights relabeled "lost"; sub-18px UI, missing low-fuel indicator, broken timezone tie-break, and cited phase-4 verify.log absent.
