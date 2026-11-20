# Phase 1 Specification — PRD-0 & Test Contract v1.0

> Extracted from the Lab Board (`Đảo Đèn Lồng Lab`, Phase 1 tab `#p1`).

## 1. Overview & Concept
- **Title:** Đảo Đèn Lồng (3D third-person game).
- **Protagonist:** **Mây**, young lantern keeper wearing a conical hat (*nón lá*) with a small hanging lantern.
- **Core Loop (Đêm 1 – Đảo Bến):**
  - Circular island with **5 Great Lanterns** (`L1`..`L5`).
  - Mây moves, jumps, collects scattered **fireflies (đom đóm)**, and deposits light into Great Lanterns to relight them.
  - **Ink Shadows (Bóng Mực)** appear in the dark fog and chase Mây; touching Mây removes 1 Flame (health).
  - **Pulse (Tỏa Sáng)** spends carried fireflies to stun and push back nearby Ink Shadows.
  - Ink Shadows fear lit Great Lanterns (safe radius).
  - Lighting all lanterns wins; losing all Flames or running out of time loses. Score is tracked; replay is available after win or loss.

## 2. Visual & Atmospheric Direction
- Simple, clean, non-violent fairy-tale night aesthetic.
- Island brightens progressively as Great Lanterns are lit.
- Warm golden-amber light for fireflies/lanterns; deep purple-black for Ink Shadows.
- Creative additions are allowed **only** if they do not alter headless Test Contract outputs (disable creative-only entities in headless mode).

## 3. Deliverables (`tag: phase-1`)
1. Playable Night 1 3D game from start through win/loss + replay.
2. `README.md`: install/run instructions (≤ 3 commands), controls, scoring rules, and "Sáng tạo của tôi" (if any).
3. `game.contract.json` at repo root + headless mode conforming to **Test Contract v1.0**.
4. Verification proof, assumptions, and AI log.
5. Updated AI harness (`AGENTS.md`, skills, hooks, independent reviewer).

---

## 4. Test Contract v1.0 (Mandatory)

### A. `game.contract.json` (repo root)
Must declare:
- `contract_version`: `"1.0"`
- `team`, `build_cmd`, `run_cmd`, `headless_cmd`
- `tuning`: exact constants used by simulation (`player_speed`, `carry_capacity`, `lantern_cost`, `lantern_count_night1=5`, `pickup_radius`, `interact_radius`, `pulse_cost`, `pulse_radius`, `night1_duration_s`, `flames`, `invuln_s`, `hit_drop_ratio`, `pulse_stun_s`, `pulse_push_m`, `pulse_cooldown_s`, `safe_radius`, `shade_speed`, `shade_hit_radius`, `fall_enabled`, `score.{per_mote, per_lantern, per_stun, per_second_left, per_flame_left}`).

### B. Headless CLI & Tick Model
Command:
```text
<headless_cmd> --seed <int> --night 1 [--scenario <file.json>] [--inputs <file.json>]
               --ticks <int> --out <file.jsonl> [--snapshot-every <int, default 10>]
```
- Fixed **60 ticks/sec** (`1 tick = 1/60 s`), **no display/window/GPU**.
- Stops after `--ticks N` steps or immediately on `won`/`lost`. Exit code `0`.
- Malformed `--inputs` or `--scenario` → exit code **`2`** (errors to stderr). Other errors → non-zero exit code.
- Length unit: meters; **+Y up**; ground `Y = 0`; player spawns at `(0, 0, 0)`.
- Snapshot tick `0` = state after scenario setup, before any input.
- Step `k` (`0 .. N-1`) reads input at tick `k` and produces state `k+1` (events in that step record `tick = k+1`).
- `time_left_s = night1_duration_s - steps_executed / 60`.
- `player.pos` = feet; `shade.pos` = center; `lantern.pos` = base; mote pos = ground point. All `tuning` radii measured on XZ plane (`distance_xz <= r`).

### C. Input Schema (`--inputs`)
- `{"frames": [{"tick": int, "move": [x, z], "cam_yaw_deg": float, "jump": bool, "interact": bool, "pulse": bool}]}`
- Defaults before frame 0: `move [0, 0]`, `cam_yaw_deg 0`, all buttons `false`.
- Partial frames preserve omitted fields; `tick` must strictly increase.
- `move` components in `[-1, 1]`; rotated by `θ = radians(cam_yaw_deg)`: `x' = x·cosθ + z·sinθ`, `z' = -x·sinθ + z·sinθ`; normalized to length 1 if `> 1`.
- Buttons trigger on `false -> true` edge.

### D. Scenario Schema (`--scenario`)
- `player`: `{pos, carried, flames}`
- `random_motes`, `random_shades` (booleans): `false` disables auto-spawning.
- `lanterns`: update matching IDs (`L1`..`L5`); supports `pos`, `lit`, `deposited`.
- `motes`, `shades`: replace initial lists (`shades[]` may include `id`).
- Scenario setup emits **no events** and **no score**.

### E. Output JSONL
- **Snapshot** every `--snapshot-every` ticks starting at tick `0`:
  `{"type":"snapshot","tick":...,"sim_tick":...,"state":"playing|won|lost","time_left_s":...,"score":...,"player":{"pos":[x,y,z],"flames":n,"carried":n},"lanterns":[...],"shades":[{"id":"S1","pos":[x,y,z],"state":"..."}],"motes_active":n,"motes":[{"id":"M1","pos":[x,y,z]}]}`
- **Event** on occurrence: `mote_picked`, `deposit`, `lantern_lit`, `pulse`, `player_hit`, `shade_spawned`, `game_over`.
- **End** (last line): `{"type":"end","ticks":...,"state":"won|lost","score":...}`
- Coordinates rounded to 3 decimal places.
- **Strict determinism:** identical `--seed`, `--scenario`, `--inputs` → byte-identical output.
