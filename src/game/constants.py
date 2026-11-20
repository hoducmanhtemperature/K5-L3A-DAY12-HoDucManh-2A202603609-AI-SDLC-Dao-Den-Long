"""Shared constants and Test Contract v1.2 tuning parameters for Đảo Đèn Lồng (Phase 3)."""

from __future__ import annotations

TICK_RATE = 60
DT = 1.0 / TICK_RATE

# Phase 3 standardized tuning — synchronized 1:1 with game.contract.json (Test Contract v1.2).
CONTRACT_TUNING: dict[str, object] = {
    "player_speed": 6.0,
    "carry_capacity": 10,
    "capacity_max": 20,
    "lantern_cost": 10,
    "relight_cost": 5,
    "lantern_count_night1": 5,
    "fuel_max": 100,
    "fuel_decay_per_s": 1.0,
    "fuel_per_mote": 10,
    "low_fuel_threshold": 30,
    "drain_per_s": 5,
    "win_ratio": 0.6,
    "pickup_radius": 1.0,
    "interact_radius": 2.0,
    "pulse_cost": 3,
    "pulse_radius": 5.0,
    "night1_duration_s": 240.0,
    "night2_duration_s": 270.0,
    "night3_duration_s": 300.0,
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
        "per_mote": 5,
        "per_lantern": 100,
        "per_relight": 40,
        "per_stun": 5,
        "per_stun_drain": 15,
        "per_second_left": 0,
        "per_flame_left": 50,
        "per_lit_at_dawn": 50,
    },
}

PHASE1_TUNING = CONTRACT_TUNING

# Integer fuel units (1/60 fuel per unit) for exact deterministic arithmetic
FUEL_MAX_60 = 6000
LOW_FUEL_60 = 1800
FUEL_PER_MOTE_60 = 600
FUEL_DECAY_PER_TICK_60 = 1
FUEL_DRAIN_PER_TICK_60 = 5
DRAIN_RADIUS_M = 2.0
DRAIN_EXIT_CHASE_RADIUS_M = 6.0
DRAIN_EVENT_INTERVAL_TICKS = 60

# Standardized physics & gameplay constants
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
VALID_SHADE_STATES = {"spawning", "wander", "chase", "recoil", "stunned", "drain"}

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

WIND_PERIOD_TICKS = 1800
WIND_DURATION_TICKS = 300
WIND_PUSH_SPEED = 2.0
