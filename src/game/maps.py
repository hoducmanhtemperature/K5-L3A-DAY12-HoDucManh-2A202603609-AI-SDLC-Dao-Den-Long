"""Standard map definitions, terrain elevation, ramps, jump pads, and obstacle helpers (Nights 1–3)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def _ring(
    radius: float,
    count: int,
    offset_deg: float = 0.0,
    cx: float = 0.0,
    cz: float = 0.0,
    y: float = 0.0,
) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    step = 360.0 / count
    for i in range(count):
        ang = math.radians(offset_deg + i * step)
        pts.append((round(cx + radius * math.cos(ang), 3), y, round(cz + radius * math.sin(ang), 3)))
    return pts


@dataclass(frozen=True)
class JumpPad:
    pos: tuple[float, float, float]
    radius: float
    vy: float
    vh: float
    dir_xz: tuple[float, float]


@dataclass(frozen=True)
class NightConfig:
    night: int
    name: str
    duration_s: float
    shade_speed: float
    shade_spawn_interval_ticks: int
    shade_max_active: int
    lanterns: list[dict[str, Any]]
    mote_spawns: list[tuple[float, float, float]]
    shade_spawns: list[tuple[float, float, float]]
    charms: list[dict[str, Any]]
    jump_pads: list[JumpPad]
    has_drifters: bool
    has_wind: bool


def _unit_dir_xz(src: tuple[float, float, float], dst: tuple[float, float, float]) -> tuple[float, float]:
    dx = dst[0] - src[0]
    dz = dst[2] - src[2]
    d = math.hypot(dx, dz)
    return (dx / d, dz / d) if d > 1e-6 else (1.0, 0.0)


NIGHT1_CONFIG = NightConfig(
    night=1,
    name="Đêm 1 — Đảo Bến",
    duration_s=300.0,
    shade_speed=4.0,
    shade_spawn_interval_ticks=480,
    shade_max_active=6,
    lanterns=[
        {"id": "L1", "pos": [0.0, 0.0, 25.0]},
        {"id": "L2", "pos": [23.8, 0.0, 7.7]},
        {"id": "L3", "pos": [14.7, 0.0, -20.2]},
        {"id": "L4", "pos": [-14.7, 0.0, -20.2]},
        {"id": "L5", "pos": [-23.8, 0.0, 7.7]},
    ],
    mote_spawns=_ring(12.0, 8, 0.0) + _ring(33.0, 16, 0.0),
    shade_spawns=_ring(37.0, 12, 15.0),
    charms=[],
    jump_pads=[],
    has_drifters=False,
    has_wind=False,
)

NIGHT2_CONFIG = NightConfig(
    night=2,
    name="Đêm 2 — Đảo Cau",
    duration_s=330.0,
    shade_speed=4.0,
    shade_spawn_interval_ticks=420,
    shade_max_active=8,
    lanterns=[
        {"id": "L1", "pos": [0.0, 0.0, 20.0]},
        {"id": "L2", "pos": [17.0, 0.0, -10.0]},
        {"id": "L3", "pos": [-17.0, 0.0, -10.0]},
        {"id": "L4", "pos": [70.0, 0.0, 20.0]},
        {"id": "L5", "pos": [87.0, 0.0, -10.0]},
        {"id": "L6", "pos": [53.0, 0.0, -10.0]},
    ],
    mote_spawns=(
        _ring(10.0, 4, 0.0, cx=0.0)
        + _ring(22.0, 8, 0.0, cx=0.0)
        + _ring(10.0, 4, 0.0, cx=70.0)
        + _ring(22.0, 8, 0.0, cx=70.0)
    ),
    shade_spawns=_ring(26.0, 8, 22.5, cx=0.0) + _ring(26.0, 8, 22.5, cx=70.0),
    charms=[{"id": "C1", "pos": [35.0, 0.0, 0.0]}],
    jump_pads=[
        JumpPad(
            pos=(20.0, 0.0, 18.0),
            radius=1.0,
            vy=14.0,
            vh=24.0,
            dir_xz=_unit_dir_xz((20.0, 0.0, 18.0), (70.0, 0.0, 0.0)),
        ),
        JumpPad(
            pos=(50.0, 0.0, -18.0),
            radius=1.0,
            vy=14.0,
            vh=24.0,
            dir_xz=_unit_dir_xz((50.0, 0.0, -18.0), (0.0, 0.0, 0.0)),
        ),
    ],
    has_drifters=True,
    has_wind=False,
)

# Night 3 mote spawns: 18 on tier 0 (r=34), 8 on tier 1 (r=18, 20..160 deg), 4 on tier 2 (r=5, 45..315 deg)
_N3_T1_MOTES = [
    (round(18.0 * math.cos(math.radians(deg)), 3), 3.0, round(18.0 * math.sin(math.radians(deg)), 3))
    for deg in range(20, 161, 20)
]
_N3_T2_MOTES = _ring(5.0, 4, 45.0, y=6.0)

NIGHT3_CONFIG = NightConfig(
    night=3,
    name="Đêm 3 — Đảo Chuông",
    duration_s=360.0,
    shade_speed=4.5,
    shade_spawn_interval_ticks=360,
    shade_max_active=10,
    lanterns=[
        {"id": "L1", "pos": [0.0, 6.0, 6.0]},
        {"id": "L2", "pos": [18.0, 3.0, 10.0]},
        {"id": "L3", "pos": [-18.0, 3.0, 10.0]},
        {"id": "L4", "pos": [35.0, 0.0, -10.0]},
        {"id": "L5", "pos": [-35.0, 0.0, -10.0]},
        {"id": "L6", "pos": [20.0, 0.0, -35.0]},
        {"id": "L7", "pos": [-20.0, 0.0, -35.0]},
    ],
    mote_spawns=_ring(34.0, 18, 0.0, y=0.0) + _N3_T1_MOTES + _N3_T2_MOTES,
    shade_spawns=_ring(43.0, 16, 0.0, y=0.0),
    charms=[
        {"id": "C1", "pos": [30.0, 0.0, 25.0]},
        {"id": "C2", "pos": [-30.0, 0.0, 25.0]},
    ],
    jump_pads=[
        JumpPad(pos=(0.0, 3.0, 13.0), radius=1.0, vy=12.0, vh=8.0, dir_xz=(0.0, -1.0)),
    ],
    has_drifters=True,
    has_wind=True,
)

NIGHT_CONFIGS: dict[int, NightConfig] = {
    1: NIGHT1_CONFIG,
    2: NIGHT2_CONFIG,
    3: NIGHT3_CONFIG,
}

# Night 3 ramps: straight 3 m wide along radial angles 30 deg and 150 deg, r in [24, 30] -> Y in [3, 0]
_N3_RAMP_ANGLES = (math.radians(30.0), math.radians(150.0))


def _night3_ramp_height(x: float, z: float) -> float | None:
    for ang in _N3_RAMP_ANGLES:
        ux, uz = math.cos(ang), math.sin(ang)
        along = x * ux + z * uz
        perp = abs(-x * uz + z * ux)
        if 24.0 <= along <= 30.0 and perp <= 1.5:
            t = (30.0 - along) / 6.0  # 0 at r=30 -> 1 at r=24
            return 3.0 * t
    return None


def surface_heights(night: int, x: float, z: float) -> list[float]:
    """Return sorted list of valid walkable surface Y heights at (x, z) for the given night."""
    if night == 1:
        return [0.0] if math.hypot(x, z) <= 40.0 else []
    if night == 2:
        on_a = math.hypot(x, z) <= 28.0
        on_b = math.hypot(x - 70.0, z) <= 28.0
        on_bridge = 26.0 <= x <= 44.0 and -2.0 <= z <= 2.0
        return [0.0] if (on_a or on_b or on_bridge) else []
    if night == 3:
        r = math.hypot(x, z)
        if r > 45.0:
            return []
        heights = [0.0]
        if 12.0 <= r <= 24.0 and z > 0.0:
            heights.append(3.0)
        if r <= 8.0:
            heights.append(6.0)
        rh = _night3_ramp_height(x, z)
        if rh is not None:
            heights.append(rh)
        return sorted(heights)
    return []


def support_height_for(night: int, x: float, z: float, current_y: float) -> float | None:
    """Return highest surface <= current_y + 0.65 (allows climbing ramps, blocks vertical cliffs)."""
    candidates = [h for h in surface_heights(night, x, z) if h <= current_y + 0.65]
    return max(candidates) if candidates else None


def resolve_obstacles(
    night: int, x: float, z: float, y: float, prev_x: float, prev_z: float
) -> tuple[float, float]:
    """Block horizontal movement into vertical tier cliffs and Night 3 central bell tower."""
    if night != 3:
        return x, z

    # Bell tower cylinder at (0, 6, 0), radius 2.0 m, height 8.0 m (Y in [6, 14])
    if 5.5 <= y < 14.0:
        r_tower = math.hypot(x, z)
        if r_tower < 2.0:
            if r_tower < 1e-6:
                x, z = 2.0, 0.0
            else:
                x *= 2.0 / r_tower
                z *= 2.0 / r_tower

    # Vertical cliffs: if entering Tier 1 (Y=3) from below (y < 2.35) without being on a ramp, block
    r = math.hypot(x, z)
    if y < 2.35 and 12.0 <= r <= 24.0 and z > 0.0 and _night3_ramp_height(x, z) is None:
        return prev_x, prev_z
    # Vertical cliff into Tier 2 (Y=6) from below (y < 5.35)
    if y < 5.35 and r <= 8.0:
        return prev_x, prev_z
    return x, z


def clamp_ground_entity(night: int, x: float, z: float) -> tuple[float, float]:
    """Keep ground-roaming Shades inside valid island area."""
    if night == 1:
        r = math.hypot(x, z)
        limit = 39.5
        if r > limit and r > 1e-6:
            return x * (limit / r), z * (limit / r)
        return x, z
    if night == 2:
        if surface_heights(2, x, z):
            return x, z
        # Clamp to nearest island A (0,0) or B (70,0)
        da = math.hypot(x, z)
        db = math.hypot(x - 70.0, z)
        if da <= db:
            return (x * 27.5 / da, z * 27.5 / da) if da > 1e-6 else (0.0, 0.0)
        return (70.0 + (x - 70.0) * 27.5 / db, z * 27.5 / db) if db > 1e-6 else (70.0, 0.0)
    # Night 3
    r = math.hypot(x, z)
    limit = 44.5
    if r > limit and r > 1e-6:
        return x * (limit / r), z * (limit / r)
    return x, z
