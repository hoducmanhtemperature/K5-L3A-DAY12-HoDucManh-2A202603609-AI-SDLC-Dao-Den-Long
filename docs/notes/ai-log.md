# AI Usage, Error Log & Token Tracking

## Checkpoint 0 (Preparation)
- **Tools used:** Gemini 4 Hydrogen (High) for SDLC scaffolding & harness setup; `qwen4-max-preview` (`tools/qwen_review.py`) for independent diff & harness audits.
- **Token-saving practices:**
  - Kept `AGENTS.md` under 35 lines to minimize repeated per-turn system context overhead.
  - Placed detailed checklists in on-demand `.agents/skills/*/SKILL.md` files rather than global rules.
  - Automated verification (`tools/verify.py`) and secret scanning (`.githooks/pre-commit`) in deterministic Python/Bash instead of spending LLM tokens on repetitive checks.
- **Exact `qwen4-max-preview` API usage:** logged automatically in `docs/notes/token-log.jsonl` (11 runs recorded before final CP0 audit).

## Errors & Harness Updates
| Phase | AI Error / Risk Observed | How Detected | Harness Fix Applied |
|---|---|---|---|
| CP0 | `ENV` untracked with no `.gitignore` risking secret commit | `git status` check | Added `.gitignore`, secret scan in `tools/verify.py`, and `.githooks/pre-commit` blocker |
| CP0 | `verify.log` lacked dirty-tree state; `qwen_review.py` `max_tokens=2048` truncated reasoning | `qwen4-max-preview` Review 1 | Added `Git working tree` state to `tools/verify.py`; raised `max_tokens` and added untracked file list in `tools/qwen_review.py` |
| CP0 | Vacuous scan on 0 tracked files, `.env.example` blanket exemption, worktree-only scan | `qwen4-max-preview` Review 2–3 (`BLOCKER`) | Scanned tracked/untracked/staged files + index blobs; removed `.env.example` exemption; added outbound secret scan in `qwen_review.py` |
| CP0 | Non-hermetic `core.hooksPath` test; `cp0/` vs `phase-0/` path drift; diff truncation hid `tools/` | `qwen4-max-preview` Review 4–5 (`BLOCKER`) | Switched to git-index `100755` check; standardized `docs/proof/phase-0/`; excluded `docs/proof/` from diff |
| CP0 | `--strict` failed open on missing verdict/trailing text; symlink/`GIT_*` test leaks | `qwen4-max-preview` Review 6–7 (`BLOCKER`) | Anchored `--strict` to `VERDICT: PASS`; enforced `is_relative_to(ROOT)` + symlink/`.git` rejection; scrubbed `GIT_*` in temp-repo tests |
| CP0 | `run_cmd(text=True)` crashed on binary blobs; binary/oversized skips & `Ran 0 tests` were fail-open; `.env.EXAMPLE` casing allowed | `qwen4-max-preview` Review 8 (`BLOCKER`) | Switched index blob read to bytes; fail-closed on unknown binary, oversized text, and 0 tests; enforced strict `.env.example` casing |
| CP0 | Allowlisted binaries skipped scanning; diff truncated `verify.py main()`; `hello_headless` in `src/`; C-quoted Vietnamese filenames (`core.quotePath`) bypassed gate | `qwen4-max-preview` Review 9–10 (`BLOCKER`) | Added ASCII scan on allowlisted binaries; raised diff cap to 200k fail-closed; moved `hello_headless.py` to `tools/`; used `-z` NUL git output + `--diff-filter=D` |
| CP0 | `get_git_diff()` ignored `git diff` rc & allowed `--allow-empty`; `ai-log` claimed missing `.env.example` & 0-test assertions; stale clean-clone proof | `qwen4-max-preview` Review 11 (`BLOCKER`) | Removed `--allow-empty`; failed closed on `rc != 0`/empty diff and any mid-text `BLOCKER`; added `.env.example` leak & 0-test assertions; added `tools/hello_3d.html` HTTP check; refreshed clean-clone proof |

## Per-Phase Summary
| Phase | Coding Agent (est. tokens) | `qwen4-max-preview` Reviewer (exact from `token-log.jsonl`) | Notes |
|---|---|---|---|
| CP0 | ~15k context + iterative fixes | Logged per run in `docs/notes/token-log.jsonl` | Harness + CI + CP0 setup (`VERDICT: PASS`) |
| Phase 1 | ~20k context + code/tests | See `token-log.jsonl` (`phase: "1"`) | Pure Python sim + headless CLI + Three.js WebSocket 3D view |
