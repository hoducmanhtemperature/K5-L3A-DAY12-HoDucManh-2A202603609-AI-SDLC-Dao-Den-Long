# Verification Traceability Matrix

| Phase | Req ID | Requirement Summary | Verification Method | Proof Artifact | Status |
|---|---|---|---|---|---|
| CP0 | CP0-1 | `ENV` & API keys protected from git tracking/commits | `tools/verify.py` secret scan + `.githooks/pre-commit` + `TestHarnessSmoke` | `docs/proof/phase-0/verify.log` | PASS |
| CP0 | CP0-2 | Independent `qwen4-max-preview` reviewer operational & strict audit | `python3 tools/qwen_review.py --phase 0 --base 9818fc1 --strict` | `docs/proof/phase-0/qwen-review.md`, `docs/notes/token-log.jsonl` | PASS |
| CP0 | CP0-3 | Headless & local static HTTP server smoke check runs without display | `python3 tools/hello_headless.py` + `test_hello_headless_and_local_http_serve` | `docs/proof/phase-0/verify.log` | PASS |
| CP0 | CP0-4 | Fresh clone runs smoke check & verification gate | `git clone . /tmp/cp0-clean-clone` + `hello_headless.py` + `verify.py --ci --require-clean` | `docs/proof/phase-0/clean-clone.log` | PASS |
| Phase 1 | P1-1 | Pure sim decoupled from rendering/IO + `game.contract.json` v1.0 sync | `test_contract_json_matches_phase1_tuning` + `test_sim_module_is_decoupled_from_io_and_rendering` | `docs/proof/phase-1/verify.log` | PASS |
| Phase 1 | P1-2 | Movement, `cam_yaw_deg` rotation, diagonal normalization, fall & respawn | `test_movement_cam_yaw_and_diagonal_normalization` + `test_fall_off_island_deducts_flame_and_respawns_or_loses` | `docs/proof/phase-1/verify.log` | PASS |
| Phase 1 | P1-3 | Motes, rising-edge lantern deposit, 5-lantern win & score bonuses | `test_mote_pickup_capacity_and_lantern_deposit_rising_edge_win` + `test_interact_held_does_not_retrigger_without_false_transition` | `docs/proof/phase-1/verify.log` | PASS |
| Phase 1 | P1-4 | Pulse stun/push/cooldown & Shade chase/hit/drop/safe-radius | `test_pulse_stuns_pushes_and_respects_cooldown_and_cost` + `test_shade_hit_drops_motes_grants_invuln_and_safe_radius_blocks_shades` | `docs/proof/phase-1/verify.log` | PASS |
| Phase 1 | P1-5 | Headless CLI, exit code 2 on malformed JSON, determinism, <10s full night | `test_headless_cli_determinism_jsonl_contract_and_exit_code_2` + `test_headless_full_night_performance_budget` + `verify.py --phase 1` | `docs/proof/phase-1/verify.log` | PASS |
| Phase 1 | P1-6 | 3D Three.js web client & WebSocket simulation server | `test_3d_http_and_websocket_server_drives_live_simulation` | `docs/proof/phase-1/verify.log`, `docs/proof/phase-1/clean-clone.log` | PASS |
| Phase 2 | P2-1 | Contract v1.1 tuning, snapshot fields & Phase 1 regression | `test_contract_v1_1_snapshot_and_tuning_fields` + `TestPhase1Simulation` | `docs/proof/phase-2/verify.log` | PASS |
| Phase 2 | P2-2 | Dash (`Lướt`), air-Y hold, cooldown & Bùa Gió speed/0-cd boost | `test_dash_air_elevation_hold_and_cooldown` + `test_charm_boosts_speed_removes_dash_cooldown_and_respawns` | `docs/proof/phase-2/verify.log` | PASS |
| Phase 2 | P2-3 | Gió Lạc (`Drifter`) steal, flee, pulse drop & Pause/Resume freeze | `test_drifter_steal_and_pulse_drop` + `test_pause_freezes_sim_tick_and_time_then_resumes` | `docs/proof/phase-2/verify.log` | PASS |
| Phase 2 | P2-4 | Night 2 (Đảo Cau) islands/bridge/jump pads & Night 3 (Đảo Chuông) 3 tiers/ramps/tower/wind | `test_night2_jump_pad_launches_across_to_island_b` + `test_night3_ramps_jump_pad_bell_tower_and_wind` | `docs/proof/phase-2/verify.log` | PASS |
| Phase 2 | P2-5 | Full 21,600-tick Night 3 headless ≤ 30 s & determinism double-run | `test_night3_full_21600_ticks_performance_and_determinism` + `verify.py --phase 2` | `docs/proof/phase-2/verify.log` | PASS |
