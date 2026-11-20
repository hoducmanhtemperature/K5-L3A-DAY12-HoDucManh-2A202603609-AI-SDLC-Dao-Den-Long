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
  - Contract nuances recorded: (1) all Phase 1 tuning radii use pure horizontal XZ distance (`distance_xz <= r`) per Test Contract v1.0 §B; (2) explicit `scenario.lanterns[].lit` takes precedence over `deposited`; (3) a terminal snapshot is emitted on early `won`/`lost` termination; (4) if `--ticks N` finishes while still playing, `end.state` reports `"playing"`; (5) `scenario.time_left_s` (from Test Contract v1.0 §D) overrides initial timer when specified.
- **Creative Additions (`Sáng tạo của tôi`):** Visual/audio polish only in `web/` (procedural Web Audio fairy-tale chimes/ambience, glowing firefly trails, conical hat *nón lá* with dangling warm lantern, progressive sky/fog brightening as lanterns light). Zero extra gameplay entities that could affect headless contract output.

## Phase 2 (Ticket-02)
- **Contract v1.1 Rule Updates (overriding Phase 1 v1.0):**
  - **Vertical check re-enabled by Ticket-02 Part 1:** Mote pickup & Shade touch now explicitly require `dist_xz <= 1.0` AND `abs(dy) <= 1.5` (replacing Phase 1's pure-XZ rule so multi-tier Night 3 behaves accurately). Phase 1 tests updated/kept consistent with this explicit Ticket-02 rule.
  - **Pulse 3D distance:** Ticket-02 Part 1 specifies Pulse center = `player.feet + 0.8 m` with 3D distance `<= 5.0 m` to Shade center (`shade.pos`). For Shades on ground (`y = 0` or `y = 1.0`), `0.8` vs `1.0` has `dy = 0.2`, matching 3D radius cleanly.
  - **Fall `player_hit` event:** Emits both `"dropped": lost` (Phase 1 compatibility) and `"lost": lost` (Contract v1.1 requirement).
  - **Spawned entities ready next tick:** Ticket-02 Step 10 explicitly states newly spawned motes, Shades, and Drifters only interact starting the next tick (naturally guaranteed because spawns occur in Step 10 after pickup/touch).
  - **Night 3 ramps:** Straight ramps of width `3 m` along radial angles `30°` and `150°` linearly interpolate ground height from `Y = 0` at `r = 30 m` to `Y = 3` at `r = 24 m`.
  - **Pause semantics:** Pressing `pause` (`false -> true`) toggles paused state (`paused` / `resumed` events). While paused, `tick` advances, `sim_tick` and all timers/physics/spawns freeze, and snapshot reports `state: "paused"`.
  - **Night 3 Wind:** Triggers every `1800` ticks (`30 s`) for `300` ticks (`5 s`) in a deterministic RNG angle `dir_deg`, pushing player `2.0 m/s` horizontally (disabled when `scenario.wind_enabled == false`).
  - **Phase 1 Test Updates:** `test_contract_json_matches_phase1_tuning` updated to verify Contract v1.1 tuning keys (superset of v1.0); `test_pulse_stuns_pushes_and_respects_cooldown_and_cost` updated shade Y from `0.0` to `0.8` to match Ticket-02's explicit 3D pulse origin (`feet + 0.8 m`); `test_fall_off_island_deducts_flame_and_respawns_or_loses` updated to also assert Contract v1.1's `lost` field.

## Phase 3 (Ticket-03)
- *(Pending Ticket-03)*

## Phase 4 (Ticket-04)
- *(Pending Ticket-04)*
