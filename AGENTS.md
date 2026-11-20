# AGENTS.md — Đảo Đèn Lồng (AI SDLC Harness)

## Project
3D third-person game "Đảo Đèn Lồng" built across 4 phases (`phase-1` .. `phase-4`, Release `v1.0.0`) with a deterministic headless Test Contract.

## Architecture Rule
- **Decouple pure simulation/logic from 3D rendering.** Headless mode and tests must run without a display/window.
- **Strict Test Contract compliance:** never alter headless I/O format or add extra entities that leak into headless output.

## Commands
- Enable commit gate once per clone: `git config core.hooksPath .githooks`
- Verify & record proof: `python3 tools/verify.py --phase <N>`
- Independent AI review (`qwen4-max-preview`): `python3 tools/qwen_review.py --phase <N>`
- Run tests directly: `python3 -m unittest discover -s tests -v`

## Phase Workflow
1. **Requirements:** Copy phase spec to `docs/specs/phase-<N>.md`. Record ambiguities & chosen constants in `docs/notes/assumptions.md`.
2. **Plan:** Define acceptance criteria & verification tests *before* writing code.
3. **Build:** Small, focused commits. Never invent unrequested requirements.
4. **Verify:** Run `python3 tools/verify.py --phase <N>`. Do not claim pass without real output in `docs/proof/phase-<N>/`.
5. **Review:** Run `python3 tools/qwen_review.py --phase <N>` for an independent diff + contract audit; log tokens in `docs/notes/ai-log.md`.
6. **Release:** Update notes, tag `phase-<N>` (`git tag phase-<N>`).

## Hard Rules
- Never commit `ENV`, `.env`, or any API key/token.
- Never write tautological ("always true") tests or hand-edit proof outputs.
- When a new phase invalidates an old test, update or remove that test with an explicit reason in `docs/notes/assumptions.md` and commit message.
