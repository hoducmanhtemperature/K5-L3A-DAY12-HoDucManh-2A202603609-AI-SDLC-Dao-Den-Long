---
name: verify-phase
description: Run single-command verification gate, headless scenarios, determinism checks, and save proof for the current phase. Use before claiming any phase task is done or before tagging phase-N.
---

# Verify Phase Skill

1. Ensure the phase specification is saved in `docs/specs/phase-<N>.md` (for Phase 0, `CHECKPOINTS.md` CP0 is the reference) and assumptions are updated in `docs/notes/assumptions.md`.
2. Run the verification gate (`python3 tools/verify.py --phase <N>`). In Phase 0 this runs secret scans, hook/security checks, and smoke tests; starting Phase 1 it also runs headless Test Contract scenarios and determinism double-runs.
3. Inspect `docs/proof/phase-<N>/verify.log` and confirm `OVERALL: PASS`.
4. Update `docs/notes/verification-matrix.md` mapping every required item in `phase-<N>` to its test/scenario and proof artifact.
5. Do not commit or tag `phase-<N>` while `tools/verify.py` exits non-zero (the `.githooks/pre-commit` hook enforces this automatically).
