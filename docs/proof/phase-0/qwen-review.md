# Qwen4-Max-Preview Independent Review (phase=0)
- Timestamp (UTC): 2026-11-20T09:06:11.966442+00:00
- Audited diff base: `9818fc1`
- Model: `qwen4-max-preview`
- Token usage: `{"prompt_tokens": 22339, "total_tokens": 29341, "completion_tokens": 7002, "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 22339}, "completion_tokens_details": {"reasoning_tokens": 5512}}`

## Scope / Requirements (CP0)

CP0 asks for a ready repo, a hello 3D **or** headless run, a notes location, and a clean-clone check. All four are present. No Test Contract exists yet, so no contract mismatch is possible — but two things overclaim:

- `tools/hello_3d.html` is named "3D" and contains an unused `<canvas>` plus `window.__CP0_READY__ = true`. No WebGL context, no renderer, no Three.js. The smoke test asserts only `HTTP 200` + substring presence. This proves *static file serving*, not 3D readiness. Fine under CP0's "or headless" clause, but rename it or stop treating it as 3D evidence — right now `http_static_status: 200 → status: "ready"` is a confidence-inflating tautology.
- CP0 is budgeted ~10 minutes. You built a 289-line gate, 256-line reviewer, CI, 287-line test suite and burned 12 reviewer runs (~250k cumulative tokens) before Phase 1. `ai-log.md` bragging about "AGENTS.md under 35 lines to minimize tokens" while doing this is inconsistent. Token efficiency is an explicit CP5 grading item; account for this honestly in the retro.

## Evidence integrity (most substantive findings)

1. **Proof HEADs disagree.** `verify.log` → `23c0828`; `clean-clone.log` → `721da96`. The clean-clone proof therefore does **not** cover the audited commit. Re-run the clean clone against the final HEAD, or state explicitly which commit each artifact attests to.
2. **`docs/proof/` is excluded from `get_git_diff()`** (`path_filter = ["--", ".", ":!docs/proof/"]`). The only artifacts that constitute "real evidence" are structurally invisible to the independent reviewer, except `verify.log` which is injected as trusted context. You have built a review pipeline that cannot audit its own proof. At minimum, hash-list the proof directory into the prompt.
3. **`qwen-review.md` is overwritten every run.** `ai-log.md` claims 11 BLOCKER reviews; none of them survive on disk. The lab explicitly grades "AI sai ở đâu, phát hiện thế nào" — hand-transcribed summaries in a markdown table are not raw evidence. Append per-run files (`qwen-review-01.md`, …) or fail-closed on overwrite.
4. **Untracked files are reviewed by filename only.** `get_git_diff` appends `git ls-files --others` names, never contents. New uncommitted source can pass strict review unseen. Not triggered here (everything is committed), but it is a live fail-open path for Phase 1+.

## Security / scanner gaps

No secrets in the diff; `.env.example` is a placeholder; `scan_text_for_secrets` returns the *pattern*, not the match, so outbound prompts and `verify.log` don't leak values. `check_outbound_prompt` covering the injected proof log is a genuinely good catch. Remaining holes:

- **No history scan.** `check_secrets` reads index + worktree + staged only. A key committed at any earlier commit and later removed passes forever. CP5 requires "lịch sử git" clean — add a `git log -p` / `git rev-list --objects` scan at least once before submission.
- **`.gitignore` blanket-ignores `dist/` and `build/`.** Those are exactly where the Phase 4 static web release will live. Ignored ⇒ absent from `ls-files --others --exclude-standard` ⇒ never scanned ⇒ a key baked into a bundle is invisible to gate and hook. Also means the release artifact may never get committed. Decide the release path now.
- **Binary detection is `b"\x00" in raw` only.** A UTF-16/UTF-32 text file with no nulls in the scanned region, or a key split across a line boundary in the staged `-U0` diff, evades the regexes. Low likelihood, but the "fail-closed" claim in `assumptions.md` is stronger than the implementation.
- `MAX_BINARY_ASSET_BYTES = 100_000_00` + `raw.decode("latin-1")` + 8 regexes means a ~100 MB `demo.mp4` (CP5) will allocate a ~100 MB str and regex-scan it. Chunk it.
- CI selects the phase by *spec-file presence*. Deleting `docs/specs/phase-3.md` silently downgrades the gate to phase 2. Derive the phase from the tag/branch instead.

## Test quality

Better than typical — the fail-closed assertions (staged-blob-vs-sanitized-worktree, `.env.EXAMPLE` casing, `Ran 0 tests`, skipped tests, non-ASCII `khóa.pem`, oversized diff, invalid base ref) are real and would catch regressions. Gaps:

- No test that a secret in an **already-committed** file is caught (only staged/worktree). That is the CP5 requirement.
- `run_unit_tests` uses `re.search(r"Ran (\d+) test")` on combined stdout — first match wins. A test printing `Ran 5 tests` masks a genuine 0-test discovery. Anchor to the summary line (`^Ran \d+ tests? in `).
- No guard against assertion-free tests. `assertEqual(1+1, 2)` in the temp fixture is fine; nothing stops the same pattern appearing in `tests/` later.
- `test_secret_scanner_boundaries_and_filenames` negative case `lantern_key = 'great_lantern_01'` is 16 chars — below the 20-char threshold, so it passes for the wrong reason. It does not demonstrate a game-identifier allowlist exists. Use a ≥20-char identifier to make that assertion meaningful.
- `check_outbound_prompt` is tested only with an `Authorization:` string; no test that `ENV` content or a `--files ENV` argument is refused end-to-end.

## Determinism / coupling

Nothing to fault yet — no simulation exists. `hello_headless.py` embeds `platform.python_version()` and is correctly quarantined in `tools/` and documented as non-contract. Keep that separation: the HTTP-server-inside-the-headless-check pattern must not migrate into Phase 1's contract runner.

## Required before Phase 1

Reconcile the two proof HEADs, stop overwriting review artifacts, and add a history scan + a decision on the ignored release directory. None of these block CP0 sign-off; all of them will block later checkpoints if deferred.

VERDICT: PASS
