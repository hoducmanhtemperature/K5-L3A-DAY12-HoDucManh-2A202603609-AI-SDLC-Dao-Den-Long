"""Shared constants and Test Contract v1.1 tuning parameters for Đảo Đèn Lồng (Phase 2)."""

from __future__ import annotations

TICK_RATE = 60
DT = 1.0 / TICK_RATE

# Phase 2 standardized tuning — synchronized 1:1 with game.contract.json (Test Contract v1.1).
CONTRACT_TUNING: dict[str, object] = {
    "player_speed": 6.0,
    "carry_capacity": 10,
    "lantern_cost": 10,
    "lantern_count_night1": 5,
    "pickup_radius": 1.0,
    "interact_radius": 2.0,
    "pulse_cost": 3,
    "pulse_radius": 5.0,
    "night1_duration_s": 300.0,
    "night2_duration_s": 330.0,
    "night3_duration_s": 360.0,
    "dash_speed": 14.0,
    "dash_duration_s": 0.2,
    "dash_cooldown_s": 1.5,
    "flames": 3,
    "invuln_s": 1.5,
    "hit_drop_ratio": 0.5,
    "pulse_stun_s": 2.0,
    "pulse_push_m": 4.0,
    "pulse_cooldown_s": 3.0,
    "safe_radius": 6.0,
    "shade_speed": 4.0,
    "shade_hit_radius": 1.0,
    "fall_enabled": True,
    "score": {
        "per_mote": 10,
        "per_lantern": 100,
        "per_stun": 5,
        "per_second_left": 2,
        "per_flame_left": 50,
    },
}

# Backwards-compatible alias for Phase 1 imports
PHASE1_TUNING = CONTRACT_TUNING

# Standardized physics & gameplay constants (Ticket-02 Part 1 & Part 3)
GRAVITY_MPS2 = -20.0
JUMP_SPEED_MPS = 7.0
FALL_Y_THRESHOLD = -10.0
RESPAWN_DELAY_TICKS = 60
VERTICAL_INTERACT_LIMIT_M = 1.5
PULSE_ORIGIN_Y_OFFSET = 0.8

DASH_DURATION_TICKS = 12
DASH_COOLDOWN_TICKS = 90
CHARM_RUN_SPEED = 7.2
CHARM_DURATION_TICKS = 600
CHARM_RESPAWN_TICKS = 2700

SHADE_DETECT_RADIUS = 12.0
SHADE_LOSE_RADIUS = 18.0
SHADE_WANDER_SPEED = 2.0
SHADE_RECOIL_TICKS = 60
SHADE_RECOIL_PUSH_M = 2.0
SHADE_FIRST_SPAWN_TICK = 300
SHADE_MIN_SPAWN_PLAYER_DIST = 15.0
PULSE_PUSH_TICKS = 15
SAFE_REPEL_MAX_TICKS = 30
VALID_SHADE_STATES = {"spawning", "wander", "chase", "recoil", "stunned"}

MOTE_INITIAL_COUNT = 20
MOTE_MAX_ACTIVE = 30
MOTE_SPAWN_INTERVAL_TICKS = 240
DROPPED_MOTE_TTL_TICKS = 480

DRIFTER_SPEED = 7.0
DRIFTER_IDLE_SPEED = 2.0
DRIFTER_MAX_ACTIVE = 2
DRIFTER_SPAWN_INTERVAL_TICKS = 1200
DRIFTER_CHASE_MIN_CARRIED = 5
DRIFTER_CHASE_RADIUS = 15.0
DRIFTER_STEAL_RADIUS = 1.2
DRIFTER_STEAL_MAX = 3
DRIFTER_FLEE_TICKS = 240
DRIFTER_DROP_FLEE_TICKS = 120

WIND_PERIOD_TICKS = 1800   # 30 s
WIND_DURATION_TICKS = 300  # 5 s
WIND_PUSH_SPEED = 2.0      # m/s
