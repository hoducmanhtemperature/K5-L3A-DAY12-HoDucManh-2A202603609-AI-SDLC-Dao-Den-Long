# Qwen4-Max-Preview Independent Review (phase=0)
- Timestamp (UTC): 2026-11-20T09:01:10.627631+00:00
- Audited diff base: `9818fc1`
- Model: `qwen4-max-preview`
- Token usage: `{"prompt_tokens": 22331, "total_tokens": 29685, "completion_tokens": 7354, "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 22331}, "completion_tokens_details": {"reasoning_tokens": 5883}}`

## Scope check (CP0)

CP0 asks for: repo ready, engine/language chosen, a hello 3D **or headless** run, notes scaffolding, and a clean-clone re-run. All are present in some form. No game logic exists yet, so there is no sim/render coupling or Test Contract to violate — good, and `assumptions.md` correctly quarantines `hello_headless.py` output (which contains `platform.python_version()`) from the future deterministic contract.

Concern: the diff is ~1,400 lines of harness for a checkpoint budgeted at ~10 minutes, and ten prior review rounds were spent hardening the *scanner*, not the product. That is scope inflation relative to CP0, and it has produced the problems below.

## Evidence integrity (material)

1. **`ai-log.md` claims tests that do not exist.** Row 9 states it added tests for "`.env.example` key leak". The only `.env.example` assertions in `tests/test_harness_smoke.py` are the *opposite*: that the placeholder yields **no** hits and that the filename is **not** forbidden. There is no test that a real key placed in `.env.example` is caught. Similarly, the comment `# Red test, skipped test, and 0-test suite fail closed` is followed by red + skipped cases only — the `Ran 0 tests` guard in `run_unit_tests()` is never exercised. The lab treats overstated evidence as a violation; these are two concrete instances.
2. **CP0-4 proof is stale.** `clean-clone.log` records `Git HEAD: 33114b2`; the gate log records `c8631ae`. The matrix marks CP0-4 PASS against a commit that is not the audited tree. Re-run the clean clone at the final HEAD.
3. **CP0-2 is self-admittedly "Pending final strict run"**, and `docs/proof/` is excluded from the review diff (`:!docs/proof/`). Only `verify.log` is injected as context; `qwen-review.md` and `clean-clone.log` are not. The one artifact class whose authenticity the reviewer must check is the one class hidden from the diff. Send at least a proof file inventory + hashes.
4. **Token log vs. narrative mismatch:** 11 API calls in `token-log.jsonl`, 10 documented rounds in `ai-log.md`, and the round numbering jumps fifth → "Seventh". One review's finding is unrecorded.

## Fail-open / weak gates

5. **`--allow-empty` contradicts its own help text.** Help says "only with `--prompt`", but nothing enforces it, and with `--prompt` the diff is never fetched — so the flag's *only* reachable effect is to let an empty diff through and log it as `purpose: "diff-review"`. That is exactly the vacuous-review path the ai-log claims was closed. Either delete the flag or hard-reject it outside `--prompt`.
6. **`Phase gate: PASS` for N>0 is a file-existence check.** `check_phase_requirements()` only stats `docs/specs/phase-N.md`. Printing `PASS` for that in Phases 1–4 is a tautological gate wearing a compliance label. Rename to `spec present` and make the real gate assert requirement→test coverage from the matrix.
7. **`is_strict_pass()` only inspects the last line.** A completion containing `VERDICT: BLOCKER - …` mid-text and `VERDICT: PASS` at the end passes. Reject any BLOCKER token anywhere.
8. **Allowlisted-binary ASCII scan is trivially bypassable.** `_scan_raw_blob` decodes latin-1 and regex-matches; UTF-16, base64, or any compressed payload inside a `.png`/`.glb` walks through. Fine as a heuristic, but do not describe it as "keys inside assets are caught". Also `.woff`, `.ico`, `.fbx`, `.blend` are not allowlisted and will hard-fail Phase 1–4 assets; and a ~99 MB `demo.mp4` (CP5) will be latin-1-decoded and run through 8 regexes — expect a memory/latency problem.

## Test quality

9. The hook's green control commits a temp repo whose only test is `assertEqual(1 + 1, 2)`. Acceptable as a fixture, but it proves the gate *executes*, not that it evaluates anything; the red-test case is what carries the weight. Keep both, and don't cite the green case as coverage.
10. `test_env_ignored_and_hook_executable_in_index` runs against the real `ROOT` index — it fails outside a git checkout (tarball/CI artifact run). Minor non-hermeticity.
11. `test_hello_headless_and_local_http_serve` binds a real socket with a 5 s timeout; it is the only network-dependent test and will be the first flake in a restricted runner. Also, `hello_3d.html` is an empty `<canvas>` with a JS flag — HTTP 200 on it verifies static serving, **not** any 3D/WebGL capability. The matrix wording is honest about this; do not let it later be cited as "3D environment verified".

## Forward risk

12. `assumptions.md` commits to browser Three.js with "no external CDN dependency", but nothing is vendored and there is no fetch step. The CP4 "clean clone, ≤3 commands" requirement will fail unless `three.module.js` is committed or a documented offline step exists. Decide now, in writing.

## Required before tagging phase-0

- Correct rows in `ai-log.md` (remove or actually implement the `.env.example`-leak and 0-test assertions); fix the misleading test comment.
- Add the two missing fail-closed tests; add a `.env.example`-with-real-key case.
- Remove/enforce `--allow-empty`; relabel the N>0 phase gate.
- Re-run clean clone at the final HEAD; update CP0-2/CP0-4 rows with the actual artifacts.

Secret hygiene itself is sound: no key material in the diff, `ENV`/`.env` ignored, index-blob scanning with staged-vs-worktree precedence is correctly tested, `.githooks/pre-commit` is mode `100755`, CI is least-privilege. That part I accept.

VERDICT: BLOCKER - ai-log/tests claim guards that are not tested (.env.example key leak, 0-test suite), CP0-4 clean-clone proof is from a stale commit, and --allow-empty re-opens the vacuous-review path.
