# Phase 2 Specification — Ticket-02 ("Ba hòn đảo") & Test Contract v1.1

> Extracted from the Lab Board (`Đảo Đèn Lồng Lab`, Phase 2 tab `#p2`). Tag: `phase-2`.

## 1. Standardized Constants (60 ticks/s, meters, seconds, +Y up)
- **Movement:** `6.0 m/s` (with Bùa Gió: `7.2 m/s`); jump `7.0 m/s`, gravity `-20.0 m/s²`, grounded-only jump.
- **Dash (`Lướt`):** `14.0 m/s`, `0.2 s` (12 ticks), cooldown `1.5 s` (90 ticks from dash start; `0` with Bùa Gió). Direction = move dir (or facing dir if idle). Air dash holds Y. Not invulnerable.
- **Fireflies:** capacity `10`; auto-pickup at `dist_xz <= 1.0` AND `abs(player_y - ground_y) <= 1.5`; 20 initial at distinct spawns, cap 30, +1 every 240 ticks.
- **Lanterns:** cost `10` (partial deposit remembered), interact `<= 2.0 m` (unlit, closest then smallest `id`), lit `safe_radius = 6.0 m` (pushes enclosed shades out within 30 ticks without damage).
- **Pulse (`Tỏa Sáng`):** cost `3`, radius `5.0 m` (3D from `feet + 0.8 m` to shade center), cooldown `3.0 s` (180 ticks). Stuns 120 ticks, pushes `4.0 m` over 15 ticks (stops at obstacles, `+X` if coincident).
- **Ink Shadows (`Bóng Mực`):** `4.0 m/s` (Night 3: `4.5 m/s`), detect `12 m` / drop `18 m`, touch `dist_xz <= 1.0` & `abs(dy) <= 1.5`, recoil `2 m` / `60` ticks, spawn 2 at tick 300 then 1 per interval (Night 1: 8s max 6; Night 2: 7s max 8; Night 3: 6s max 10). Exact states: `spawning`, `wander`, `chase`, `recoil`, `stunned`.
- **Hit / Fall:** Shade hit = `-1` Flame, drop `floor(carried/2)` motes (ring `1.5..2.5 m`, TTL 480 ticks), invuln 90 ticks. Fall (`Y < -10`) = once ignoring invuln, `-1` Flame, loses all carried (`lost`), wait 60 ticks, respawn at start with invuln 90 ticks (or lose immediately at 0 Flames).
- **Health & Durations:** 3 Flames (refilled each Night). Night 1/2/3 = `300 / 330 / 360 s`.
- **Scoring:** `+10`/mote deposited, `+100`/lantern lit, `+5`/shade pulsed, win bonus `+ floor(time_left_s)*2 + 50*flames`.
- **Mandatory 12-Step Tick Order:** Input (`pause` first) → Timers → Move/Jump/Dash/Pad/Wind & Fall → Pickup Motes/Charms → Lantern Interact → Safe Zones → Pulse → Move Shades/Drifters → Touch (Drifters then Shades by ascending `id`) → Scheduled Spawns → Win/Loss → Snapshot.

## 2. Standard Maps (3 Nights)
- **Night 1 — Đảo Bến:** Circle `R=40 m` at `(0,0,0)`, 5 lanterns `L1..L5`.
- **Night 2 — Đảo Cau:** Two circles `R=28 m` at `(0,0,0)` & `(70,0,0)` + bamboo bridge `x∈[26,44], z∈[-2,2]`; jump pads `R=1 m` at `(20,0,18)` and `(50,0,-18)` (`vy=14`, `vh=24` toward other island center); 6 lanterns `L1..L6`; Charm `C1` at `(35,0,0)`.
- **Night 3 — Đảo Chuông:** Circle `R=45 m`, 3 tiers (`Y=0` full, `Y=3` annulus `r∈[12,24], z>0`, `Y=6` disk `r<=8`), 2 ramps (width `3 m`, angles `30°`/`150°`, `r=30→24`), jump pad at `(0,3,13)` (`vy=12`, `vh=8` toward `-Z`), central bell tower cylinder `R=2 m` height `8 m` on Tier 2, 7 lanterns `L1..L7`, Charms `C1 (30,0,25)` & `C2 (-30,0,25)`, Strong Wind every `30 s` for `5 s` pushing `2 m/s`.

## 3. New Features
1. **Gió Lạc (Drifters, Nights 2–3):** `7 m/s`, max 2, spawn at ticks `1200, 2400, ...`, IDs `D1, D2, ...`; `idle (2 m/s)` ↔ `chase` (`carried>=5` & `dist<=15 m`) → touch (`<=1.2 m`) steals `min(3, carried)` → `flee` (240 ticks) → `removed`. Pulse turns `chase`→`flee`; pulsing `flee` with stolen motes drops them as dropped motes and removes after 120 ticks.
2. **Bùa Gió (Charms, Nights 2–3):** `600` ticks (`7.2 m/s`, 0 dash cooldown), respawns after `2700` ticks.
3. **3-Night Progression, Pause (Esc/P), Persistent Settings (volume & mouse sensitivity), Full Audio, Full HUD + Off-Screen Lantern Arrow, Standard Palette, Ambient Light `0.15 + 0.55*(lit/total)`.**

## 4. Test Contract v1.1 Changes
- `contract_version: "1.1"`, `tuning` adds `dash_speed`, `dash_duration_s`, `dash_cooldown_s`, `night2_duration_s`, `night3_duration_s`.
- `--night` supports `1`, `2`, `3`.
- Snapshot adds `night`, `wind {active, dir_deg}`, `player.{vel, grounded, invuln, dash_cd_s, pulse_cd_s, charm_s}`, `motes[{id,pos,kind,ttl_s}]`, `drifters[{id,pos,state,stolen}]`, `charms[{id,available,respawn_s}]`.
- Scenario adds `player.{invuln_ticks, dash_cd_ticks, pulse_cd_ticks, charm_ticks}`, `shades[].{state, state_ticks_left}`, `drifters`, `charms`, `random_drifters`, `wind_enabled`.
- Inputs add `dash` and `pause` (rising edge).
- New events: `dash`, `charm_picked`, `drifter_steal`, `drifter_drop`, `night_start`, `paused`, `resumed`; fall `player_hit` includes `lost`.
- Full night (≤ 21,600 ticks) headless runtime ≤ 30 s.
