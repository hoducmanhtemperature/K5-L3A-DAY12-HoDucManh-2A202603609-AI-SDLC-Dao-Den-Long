"""Shared constants, tuning parameters, and Night 1 map layout for Đảo Đèn Lồng (Phase 1)."""

from __future__ import annotations

import math

TICK_RATE = 60
DT = 1.0 / TICK_RATE

# Phase 1 tuning — synchronized 1:1 with game.contract.json (Test Contract v1.0).
PHASE1_TUNING: dict[str, object] = {
    "player_speed": 6.0,
    "carry_capacity": 10,
    "lantern_cost": 10,
    "lantern_count_night1": 5,
    "pickup_radius": 1.0,
    "interact_radius": 2.0,
    "pulse_cost": 3,
    "pulse_radius": 5.0,
    "night1_duration_s": 300.0,
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

# Physics & spawn constants documented in docs/notes/assumptions.md
ISLAND_RADIUS_M = 40.0
GRAVITY_MPS2 = -20.0
JUMP_SPEED_MPS = 7.0
FALL_Y_THRESHOLD = -10.0
RESPAWN_DELAY_TICKS = 60

SHADE_DETECT_RADIUS = 12.0
SHADE_LOSE_RADIUS = 18.0
SHADE_WANDER_SPEED = 2.0
SHADE_RECOIL_TICKS = 60
SHADE_RECOIL_PUSH_M = 2.0
SHADE_FIRST_SPAWN_TICK = 300
SHADE_SPAWN_INTERVAL_TICKS = 480
SHADE_MAX_ACTIVE = 6
SHADE_MIN_SPAWN_PLAYER_DIST = 15.0
PULSE_PUSH_TICKS = 15
SAFE_REPEL_MAX_TICKS = 30

MOTE_INITIAL_COUNT = 20
MOTE_MAX_ACTIVE = 30
MOTE_SPAWN_INTERVAL_TICKS = 240
DROPPED_MOTE_TTL_TICKS = 480

NIGHT1_LANTERNS: list[dict[str, object]] = [
    {"id": "L1", "pos": [0.0, 0.0, 25.0]},
    {"id": "L2", "pos": [23.8, 0.0, 7.7]},
    {"id": "L3", "pos": [14.7, 0.0, -20.2]},
    {"id": "L4", "pos": [-14.7, 0.0, -20.2]},
    {"id": "L5", "pos": [-23.8, 0.0, 7.7]},
]


def _ring_points(radius: float, count: int, offset_deg: float = 0.0) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    step = 360.0 / count
    for i in range(count):
        ang = math.radians(offset_deg + i * step)
        pts.append((round(radius * math.cos(ang), 3), 0.0, round(radius * math.sin(ang), 3)))
    return pts


NIGHT1_MOTE_SPAWNS: list[tuple[float, float, float]] = (
    _ring_points(12.0, 8, 0.0) + _ring_points(33.0, 16, 0.0)
)

NIGHT1_SHADE_SPAWNS: list[tuple[float, float, float]] = _ring_points(37.0, 12, 15.0)
