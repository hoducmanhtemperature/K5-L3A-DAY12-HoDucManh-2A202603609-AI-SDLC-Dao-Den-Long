---
name: qwen-review
description: Run an independent code, spec-compliance, and test-quality review using qwen4-max-preview (key in ENV) after verification passes.
---

# Independent Qwen4-Max-Preview Review Skill

Use this after `python3 tools/verify.py --phase <N>` passes, so an independent model (not the coding agent) audits the diff against the phase spec.

## Commands
- Audit uncommitted diff against `HEAD`:
  ```bash
  python3 tools/qwen_review.py --phase <N> --strict
  ```
- Audit committed changes from a base ref (required when working tree is clean, since empty diffs fail closed):
  ```bash
  python3 tools/qwen_review.py --phase <N> --base <base_commit_or_prev_tag> --strict
  ```
- Audit a plan or spec before writing code:
  ```bash
  python3 tools/qwen_review.py --phase <N> --prompt "Audit this Phase <N> plan against the spec" --files docs/specs/phase-<N>.md docs/notes/assumptions.md
  ```

## Outputs
- Saves the review to `docs/proof/phase-<N>/qwen-review.md`.
- Appends exact prompt/completion/reasoning token counts to `docs/notes/token-log.jsonl`.
- If `VERDICT: BLOCKER`, fix the flagged issue and re-run `tools/verify.py` + `tools/qwen_review.py`.
