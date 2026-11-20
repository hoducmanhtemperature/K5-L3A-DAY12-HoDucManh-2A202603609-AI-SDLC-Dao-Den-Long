# Assumptions & Design Decisions

Record every ambiguity in the phase specifications, the chosen concrete values/rules, and any design updates when later tickets override earlier rules.

## Checkpoint 0 (Preparation)
- **Language & Engine Choice:** Python 3.13 (minimum Python ≥ 3.10) standard library (`unittest`, deterministic simulation, headless CLI) + browser **Three.js** (3D interactive renderer served locally by Python), ensuring clean clones run in 1 command without third-party Python/Node build failures. In Phase 1, the MIT-licensed `three.min.js` bundle will be vendored locally (attributed in `CREDITS.md`) so the 3D view also runs completely offline.
- **CP0 Spec Basis & Smoke vs. Test Contract:** Phase 0 (`--phase 0`) checks against `CHECKPOINTS.md` CP0 + `RULES.md` (no separate `docs/specs/phase-0.md` is needed). `tools/hello_headless.py` lives in `tools/` (not `src/`) and is strictly a CP0 environment check (not the Test Contract format). Phase 1+ headless contract output will be 100% deterministic with no environment/version/timestamp fields.
- **Secret Filename & Binary Asset Policy:** `tools/verify.py` forbids `ENV`, `.env`, `ENV.*`, `.env.*` (strictly exempting only exact lowercase `.env.example`), `id_rsa`, `id_ed25519`, and `*.key`/`*.pem`/`*.pfx`/`*.p12`. Allowlisted media extensions are still ASCII-scanned for embedded keys; non-allowlisted binary files and text files > 1 MB fail closed.
- **Independent Reviewer:** `qwen4-max-preview` via Alibaba Cloud Bailian Token Plan (`ENV` local only, never committed). Note: `docs/proof/` is excluded from `qwen_review.py` diff to avoid recursive self-diffs, while `docs/proof/phase-<N>/verify.log` is passed directly in context.

## Phase 1 (PRD-0)
- **Architecture:** Single authoritative pure-Python 60-Hz simulation (`src/game/sim.py`) used identically by both the headless CLI (`src/headless.py`) and the interactive 3D browser server (`src/server.py` + `web/`). Zero logic duplication between 3D view and headless contract.
- **3D Rendering:** Browser Three.js (`r128`, MIT-licensed, vendored locally in `web/vendor/` so clean clones run completely offline) connected via a stdlib RFC 6455 WebSocket + HTTP server (`src/server.py`).
- **Night 1 Island & Chosen Constants (matching `game.contract.json` v1.0):**
  - Circular island center `(0, 0, 0)`, radius `40.0` m; falling below `Y < -10.0` (`fall_enabled: true`) deducts 1 Flame, drops all carried fireflies, and respawns Mây at `(0, 0, 0)` with invulnerability (unless Flames reach `0`, which loses immediately).
  - 5 Great Lanterns (`L1`..`L5`) placed symmetrically on a 25 m ring: `(0,0,25)`, `(23.8,0,7.7)`, `(14.7,0,-20.2)`, `(-14.7,0,-20.2)`, `(-23.8,0,7.7)`.
  - Movement & physics: `player_speed = 6.0` m/s, jump velocity `7.0` m/s, gravity `-20.0` m/s².
  - Fireflies: `carry_capacity = 10`, `pickup_radius = 1.0` m, 20 initial motes on 12 m & 33 m rings (cap 30, +1 every 240 ticks if under cap).
  - Lanterns: `lantern_cost = 10`, `interact_radius = 2.0` m, `safe_radius = 6.0` m (lit lanterns repel Ink Shadows outside 6 m).
  - Pulse (`Tỏa Sáng`): `pulse_cost = 3`, `pulse_radius = 5.0` m, `pulse_cooldown_s = 3.0` s (`180` ticks), `pulse_stun_s = 2.0` s (`120` ticks), `pulse_push_m = 4.0` m (applied over 15 ticks).
  - Ink Shadows: `shade_speed = 4.0` m/s, `shade_hit_radius = 1.0` m, detect at `12.0` m, drop chase at `18.0` m; 2 spawn at tick `300` (5 s), then 1 every `480` ticks (8 s), max 6 active, on a 37 m perimeter ring ≥ 15 m from player.
  - Health & Time: `flames = 3`, `invuln_s = 1.5` s (`90` ticks), `hit_drop_ratio = 0.5` (`floor(carried * 0.5)` dropped around player with `480`-tick TTL), `night1_duration_s = 300.0` s (`18000` ticks).
  - Score: `per_mote = 10` (per mote deposited), `per_lantern = 100`, `per_stun = 5`, `per_second_left = 2`, `per_flame_left = 50`.
- **Creative Additions (`Sáng tạo của tôi`):** Visual/audio polish only in `web/` (procedural Web Audio fairy-tale chimes/ambience, glowing firefly trails, conical hat *nón lá* with dangling warm lantern, progressive sky/fog brightening as lanterns light). Zero extra gameplay entities that could affect headless contract output.

## Phase 2 (Ticket-02)
- *(Pending Ticket-02)*

## Phase 3 (Ticket-03)
- *(Pending Ticket-03)*

## Phase 4 (Ticket-04)
- *(Pending Ticket-04)*
