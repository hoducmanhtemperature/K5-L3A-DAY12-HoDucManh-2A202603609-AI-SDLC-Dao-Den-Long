# Phase 3 Specification — Ticket-03 ("Đèn cạn dầu") & Test Contract v1.2

> Extracted from the Lab Board (`Đảo Đèn Lồng Lab`, Phase 3 tab `#p3`). Tag: `phase-3`.

## 1. Lantern Fuel — [REPLACES] permanent lit lanterns
- `fuel_max = 100`, newly lit / relit lantern starts at `fuel = 100`.
- Decay while lit: `1.0 / s` (`1/60` per tick, stored as integer `fuel_60` in `0..6000`).
- Refuel (`interact` on lit lantern with `fuel < 100`): `used = min(carried, ceil((100 - fuel) / 10))`, `fuel = min(100, fuel + 10 * used)`, `carried -= used`. Full lanterns (`used == 0`) are not selectable, emit no event, award no score.
- Interact target selection: only lanterns that can accept motes (unlit, or lit with `fuel < 100`); closest XZ, tie-break smallest `id`.
- `fuel <= 0`: lantern turns off (`lit = false`, `deposited = 0`, `ever_lit = true`), emits `lantern_out {lantern_id}`.
- Relight cost: `5` motes if `ever_lit`, else `10`.

## 2. Shade Fuel Drain — [REPLACES] unconditional safe zone
- Lit lanterns with `fuel < 30` lose their safe zone (`fuel == 30` keeps safe zone).
- Only `wander` Shades target weak lanterns: nearest lit lantern with `fuel < 30` (tie-break smallest `id`), else nearest unlit lantern. `chase` Shades do not switch.
- Within `<= 2 m` XZ of weak lantern: enter `drain` state, drain `5 fuel/s` (`5/60` per tick, stacks across multiple Shades, lantern also decays `1/s`). Emit `fuel_drain {lantern_id, shade_id, fuel}` every 60 ticks of draining.
- Exit `drain`: -> `chase` if player within `6 m`; -> `stunned` if Pulsed; -> `wander` if lantern goes out, `fuel >= 30`, or distance `> 2 m`.
- Refueling a lantern back to `>= 30` repels any Shades inside `6 m` within 30 ticks without dealing damage.

## 3. Dawn Survival Win Rule — [REPLACES] instant win on all lit
- Night durations: Night 1 `240 s`, Night 2 `270 s`, Night 3 `300 s`.
- Lighting all lanterns does **not** end the night early.
- Win: alive at dawn (`time_left == 0`) AND lit lanterns `>= ceil(0.6 * total)` (`3/5`, `4/6`, `5/7`) -> `game_over {result: "won", reason: "dawn_survived"}`.
- Loss: `flames <= 0` immediately (`no_flames`), or dawn with lit lanterns `< threshold` (`dawn`).
- Tick order: Step 2 applies decay + drain; immediately after Step 2, lanterns with `fuel <= 0` extinguish (`lantern_out`).

## 4. Progressive Carry Capacity
- `capacity = min(20, 10 + 2 * successful_lights)` (counts both first lights and relights during the night; excludes scenario pre-lit lanterns; resets to 0 each night).

## 5. New Scoring — [REPLACES] Phase 1–2 score formula
- `+5` per mote deposited (light, relight, or refuel).
- `+100` first light · `+40` relight.
- Pulse: `+5` per Shade (`+15` total if Shade was in `drain` immediately before Pulse).
- Dawn win bonus: `+50 + floor(fuel)` per lit lantern + `+50` per remaining Flame. Time bonus removed.

## 6. Colorblind Mode
- Saved setting `"Bảng màu dễ phân biệt"`: Shade accent `#7A3CFF -> #00B3FF`, UI danger `#FF5A5F -> #FFFFFF` + `⚠`, unlit lanterns visually shrunk 20% with torn paper marks, low-fuel lanterns blink at 1 Hz.

## 7. Test Contract v1.2
- `contract_version: "1.2"`, `tuning` adds `fuel_max`, `fuel_decay_per_s`, `fuel_per_mote`, `relight_cost`, `win_ratio`, `drain_per_s`, `low_fuel_threshold`, `capacity_max`, and updates `night1_duration_s: 240`, `night2_duration_s: 270`, `night3_duration_s: 300`.
- Snapshot adds `lanterns[].{fuel, ever_lit, relit_count}`, `player.capacity`, shade state `drain`.
- Scenario adds `lanterns[].{lit, fuel, ever_lit}` (`lit: true` without `fuel` defaults to `100`), `player.successful_lights`, `shades[].target_lantern_id`.
- Events: `refuel {lantern_id, amount, fuel}`, `lantern_out {lantern_id}`, `fuel_drain {lantern_id, shade_id, fuel}`, `lantern_lit` adds `relight: true|false`, `game_over.reason` adds `dawn_survived` (`all_lit` removed).
