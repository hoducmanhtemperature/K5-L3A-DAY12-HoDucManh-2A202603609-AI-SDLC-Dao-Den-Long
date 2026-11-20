# Assumptions & Design Decisions

Record every ambiguity in the phase specifications, the chosen concrete values/rules, and any design updates when later tickets override earlier rules.

## Checkpoint 0 (Preparation)
- **Language & Engine Choice:** Python 3.13 (minimum Python ≥ 3.10) standard library (`unittest`, deterministic simulation, headless CLI) + browser **Three.js** (3D interactive renderer served locally by Python), ensuring clean clones run in 1 command without third-party Python/Node build failures. In Phase 1, the MIT-licensed `three.min.js` bundle will be vendored locally (attributed in `CREDITS.md`) so the 3D view also runs completely offline.
- **CP0 Spec Basis & Smoke vs. Test Contract:** Phase 0 (`--phase 0`) checks against `CHECKPOINTS.md` CP0 + `RULES.md` (no separate `docs/specs/phase-0.md` is needed). `tools/hello_headless.py` lives in `tools/` (not `src/`) and is strictly a CP0 environment check (not the Test Contract format). Phase 1+ headless contract output will be 100% deterministic with no environment/version/timestamp fields.
- **Secret Filename & Binary Asset Policy:** `tools/verify.py` forbids `ENV`, `.env`, `ENV.*`, `.env.*` (strictly exempting only exact lowercase `.env.example`), `id_rsa`, `id_ed25519`, and `*.key`/`*.pem`/`*.pfx`/`*.p12`. Allowlisted media extensions are still ASCII-scanned for embedded keys; non-allowlisted binary files and text files > 1 MB fail closed.
- **Independent Reviewer:** `qwen4-max-preview` via Alibaba Cloud Bailian Token Plan (`ENV` local only, never committed). Note: `docs/proof/` is excluded from `qwen_review.py` diff to avoid recursive self-diffs, while `docs/proof/phase-<N>/verify.log` is passed directly in context.

## Phase 1 (PRD-0)
- *(Pending PRD-0 release from Lab Board)*

## Phase 2 (Ticket-02)
- *(Pending Ticket-02)*

## Phase 3 (Ticket-03)
- *(Pending Ticket-03)*

## Phase 4 (Ticket-04)
- *(Pending Ticket-04)*
