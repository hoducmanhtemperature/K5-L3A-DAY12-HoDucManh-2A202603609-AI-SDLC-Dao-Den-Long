"""Pure deterministic 60-Hz simulation for Đảo Đèn Lồng (Phase 2 / Test Contract v1.1)."""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from typing import Any

from src.game.constants import (
    CHARM_DURATION_TICKS,
    CHARM_RESPAWN_TICKS,
    CHARM_RUN_SPEED,
    CONTRACT_TUNING,
    DASH_COOLDOWN_TICKS,
    DASH_DURATION_TICKS,
    DRIFTER_CHASE_MIN_CARRIED,
    DRIFTER_CHASE_RADIUS,
    DRIFTER_DROP_FLEE_TICKS,
    DRIFTER_FLEE_TICKS,
    DRIFTER_IDLE_SPEED,
    DRIFTER_MAX_ACTIVE,
    DRIFTER_SPAWN_INTERVAL_TICKS,
    DRIFTER_SPEED,
    DRIFTER_STEAL_MAX,
    DRIFTER_STEAL_RADIUS,
    DROPPED_MOTE_TTL_TICKS,
    DT,
    FALL_Y_THRESHOLD,
    GRAVITY_MPS2,
    JUMP_SPEED_MPS,
    MOTE_INITIAL_COUNT,
    MOTE_MAX_ACTIVE,
    MOTE_SPAWN_INTERVAL_TICKS,
    PULSE_ORIGIN_Y_OFFSET,
    PULSE_PUSH_TICKS,
    RESPAWN_DELAY_TICKS,
    SAFE_REPEL_MAX_TICKS,
    SHADE_DETECT_RADIUS,
    SHADE_FIRST_SPAWN_TICK,
    SHADE_LOSE_RADIUS,
    SHADE_MIN_SPAWN_PLAYER_DIST,
    SHADE_RECOIL_PUSH_M,
    SHADE_RECOIL_TICKS,
    SHADE_WANDER_SPEED,
    TICK_RATE,
    VALID_SHADE_STATES,
    VERTICAL_INTERACT_LIMIT_M,
    WIND_DURATION_TICKS,
    WIND_PERIOD_TICKS,
    WIND_PUSH_SPEED,
)
from src.game.maps import (
    NIGHT_CONFIGS,
    clamp_ground_entity,
    resolve_obstacles,
    support_height_for,
)


class ContractInputError(ValueError):
    """Raised when --inputs, --scenario, or --night fails schema validation (exit code 2)."""


def _r3(val: float) -> float:
    rounded = round(float(val), 3)
    return 0.0 if rounded == 0.0 else rounded


def _pos3(pos: list[float] | tuple[float, float, float]) -> list[float]:
    return [_r3(pos[0]), _r3(pos[1]), _r3(pos[2])]


def _dist_xz(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _dist_3d(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _is_nonneg_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _parse_vec3(val: Any, label: str) -> list[float]:
    if not isinstance(val, (list, tuple)) or len(val) != 3 or not all(_is_num(x) for x in val):
        raise ContractInputError(f"Invalid 3D vector for {label}: {val!r}")
    return [float(val[0]), float(val[1]), float(val[2])]


def parse_inputs_dict(data: Any) -> dict[int, dict[str, Any]]:
    """Validate --inputs JSON (Contract v1.1) and return frame map indexed by tick."""
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise ContractInputError("Input JSON must be an object containing a 'frames' list.")
    frames_by_tick: dict[int, dict[str, Any]] = {}
    prev_tick = -1
    for idx, raw in enumerate(data["frames"]):
        if not isinstance(raw, dict):
            raise ContractInputError(f"Frame {idx} must be an object.")
        tick = raw.get("tick")
        if not _is_nonneg_int(tick):
            raise ContractInputError(f"Frame {idx} has invalid 'tick': {tick!r}")
        if tick <= prev_tick:
            raise ContractInputError(f"Frame ticks must strictly increase ({tick} <= {prev_tick}).")
        prev_tick = tick

        parsed: dict[str, Any] = {}
        if "move" in raw:
            mv = raw["move"]
            if (
                not isinstance(mv, (list, tuple))
                or len(mv) != 2
                or not _is_num(mv[0])
                or not _is_num(mv[1])
            ):
                raise ContractInputError(f"Frame tick={tick} has invalid 'move': {mv!r}")
            mx, mz = float(mv[0]), float(mv[1])
            if not (-1.0 <= mx <= 1.0 and -1.0 <= mz <= 1.0):
                raise ContractInputError(f"Frame tick={tick} 'move' components must be in [-1, 1].")
            parsed["move"] = [mx, mz]
        if "cam_yaw_deg" in raw:
            if not _is_num(raw["cam_yaw_deg"]):
                raise ContractInputError(f"Frame tick={tick} has invalid 'cam_yaw_deg'.")
            parsed["cam_yaw_deg"] = float(raw["cam_yaw_deg"])
        for btn in ("jump", "interact", "pulse", "dash", "pause"):
            if btn in raw:
                if not isinstance(raw[btn], bool):
                    raise ContractInputError(f"Frame tick={tick} button {btn!r} must be boolean.")
                parsed[btn] = raw[btn]
        frames_by_tick[tick] = parsed
    return frames_by_tick


def parse_scenario_dict(data: Any) -> dict[str, Any]:
    """Validate --scenario JSON (Contract v1.1) and normalize fields."""
    if not isinstance(data, dict):
        raise ContractInputError("Scenario JSON must be an object.")
    out: dict[str, Any] = {}

    if "player" in data:
        p = data["player"]
        if not isinstance(p, dict):
            raise ContractInputError("Scenario 'player' must be an object.")
        p_out: dict[str, Any] = {}
        if "pos" in p:
            p_out["pos"] = _parse_vec3(p["pos"], "player.pos")
        for key in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks", "charm_ticks"):
            if key in p:
                if not _is_nonneg_int(p[key]):
                    raise ContractInputError(f"Scenario 'player.{key}' must be an int >= 0.")
                p_out[key] = int(p[key])
        out["player"] = p_out

    for flag in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
        if flag in data:
            if not isinstance(data[flag], bool):
                raise ContractInputError(f"Scenario {flag!r} must be a boolean.")
            out[flag] = data[flag]

    if "motes" in data:
        if not isinstance(data["motes"], list):
            raise ContractInputError("Scenario 'motes' must be a list.")
        motes: list[dict[str, Any]] = []
        for idx, item in enumerate(data["motes"]):
            if isinstance(item, dict) and "pos" in item:
                m_out: dict[str, Any] = {"pos": _parse_vec3(item["pos"], f"motes[{idx}].pos")}
                if "kind" in item:
                    m_out["kind"] = str(item["kind"])
                if "ttl_ticks" in item and item["ttl_ticks"] is not None:
                    if not _is_nonneg_int(item["ttl_ticks"]):
                        raise ContractInputError(f"Scenario 'motes[{idx}].ttl_ticks' must be int >= 0.")
                    m_out["ttl_ticks"] = int(item["ttl_ticks"])
                motes.append(m_out)
            else:
                motes.append({"pos": _parse_vec3(item, f"motes[{idx}]")})
        out["motes"] = motes

    if "shades" in data:
        if not isinstance(data["shades"], list):
            raise ContractInputError("Scenario 'shades' must be a list.")
        shades: list[dict[str, Any]] = []
        for idx, item in enumerate(data["shades"]):
            if not isinstance(item, dict) or "pos" not in item:
                raise ContractInputError(f"Scenario 'shades[{idx}]' must be an object with 'pos'.")
            s_out: dict[str, Any] = {"pos": _parse_vec3(item["pos"], f"shades[{idx}].pos")}
            if "id" in item:
                if not isinstance(item["id"], str) or not item["id"]:
                    raise ContractInputError(f"Scenario 'shades[{idx}].id' must be a non-empty string.")
                s_out["id"] = item["id"]
            if "state" in item:
                if item["state"] not in VALID_SHADE_STATES:
                    raise ContractInputError(f"Invalid shade state: {item['state']!r}")
                s_out["state"] = item["state"]
            if "state_ticks_left" in item:
                if not _is_nonneg_int(item["state_ticks_left"]):
                    raise ContractInputError(f"Scenario 'shades[{idx}].state_ticks_left' must be int >= 0.")
                s_out["state_ticks_left"] = int(item["state_ticks_left"])
            shades.append(s_out)
        out["shades"] = shades

    if "drifters" in data:
        if not isinstance(data["drifters"], list):
            raise ContractInputError("Scenario 'drifters' must be a list.")
        drifters: list[dict[str, Any]] = []
        for idx, item in enumerate(data["drifters"]):
            if not isinstance(item, dict) or "pos" not in item:
                raise ContractInputError(f"Scenario 'drifters[{idx}]' must have 'pos'.")
            d_out: dict[str, Any] = {"pos": _parse_vec3(item["pos"], f"drifters[{idx}].pos")}
            if "id" in item:
                d_out["id"] = str(item["id"])
            if "state" in item:
                if item["state"] not in ("idle", "chase", "flee"):
                    raise ContractInputError(f"Invalid drifter state: {item['state']!r}")
                d_out["state"] = item["state"]
            if "stolen" in item:
                if not _is_nonneg_int(item["stolen"]):
                    raise ContractInputError(f"Invalid drifter stolen count: {item['stolen']!r}")
                d_out["stolen"] = int(item["stolen"])
            drifters.append(d_out)
        out["drifters"] = drifters

    if "charms" in data:
        if not isinstance(data["charms"], list):
            raise ContractInputError("Scenario 'charms' must be a list.")
        charms: list[dict[str, Any]] = []
        for idx, item in enumerate(data["charms"]):
            if not isinstance(item, dict) or "pos" not in item:
                raise ContractInputError(f"Scenario 'charms[{idx}]' must have 'pos'.")
            c_out: dict[str, Any] = {"pos": _parse_vec3(item["pos"], f"charms[{idx}].pos")}
            if "id" in item:
                c_out["id"] = str(item["id"])
            if "available" in item:
                if not isinstance(item["available"], bool):
                    raise ContractInputError(f"Scenario 'charms[{idx}].available' must be bool.")
                c_out["available"] = item["available"]
            if "respawn_ticks" in item:
                if not _is_nonneg_int(item["respawn_ticks"]):
                    raise ContractInputError(f"Scenario 'charms[{idx}].respawn_ticks' must be int >= 0.")
                c_out["respawn_ticks"] = int(item["respawn_ticks"])
            charms.append(c_out)
        out["charms"] = charms

    if "lanterns" in data:
        if not isinstance(data["lanterns"], list):
            raise ContractInputError("Scenario 'lanterns' must be a list.")
        lanterns: list[dict[str, Any]] = []
        for idx, item in enumerate(data["lanterns"]):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ContractInputError(f"Scenario 'lanterns[{idx}]' must have string 'id'.")
            l_out: dict[str, Any] = {"id": item["id"]}
            if "pos" in item:
                l_out["pos"] = _parse_vec3(item["pos"], f"lanterns[{idx}].pos")
            if "lit" in item:
                if not isinstance(item["lit"], bool):
                    raise ContractInputError(f"Scenario 'lanterns[{idx}].lit' must be boolean.")
                l_out["lit"] = item["lit"]
            if "deposited" in item:
                if not _is_nonneg_int(item["deposited"]):
                    raise ContractInputError(f"Scenario 'lanterns[{idx}].deposited' must be int >= 0.")
                l_out["deposited"] = int(item["deposited"])
            lanterns.append(l_out)
        out["lanterns"] = lanterns

    if "time_left_s" in data:
        if not _is_num(data["time_left_s"]) or float(data["time_left_s"]) < 0:
            raise ContractInputError("Scenario 'time_left_s' must be a number >= 0.")
        out["time_left_s"] = float(data["time_left_s"])

    return out


@dataclass
class Lantern:
    id: str
    pos: list[float]
    lit: bool = False
    deposited: int = 0


@dataclass
class Mote:
    id: str
    pos: list[float]
    kind: str = "random"
    ttl_ticks: int | None = None


@dataclass
class Shade:
    id: str
    pos: list[float]
    state: str = "wander"
    stun_ticks: int = 0
    recoil_ticks: int = 0
    spawning_ticks: int = 0
    push_ticks: int = 0
    push_dir: list[float] = field(default_factory=lambda: [1.0, 0.0])
    push_speed: float = 0.0
    wander_angle: float = 0.0
    safe_repel_ticks: int = 0


@dataclass
class Drifter:
    id: str
    pos: list[float]
    state: str = "idle"
    stolen: int = 0
    has_stolen: bool = False
    flee_ticks: int = 0
    wander_angle: float = 0.0


@dataclass
class Charm:
    id: str
    pos: list[float]
    available: bool = True
    respawn_ticks: int = 0


@dataclass
class Player:
    pos: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    vel: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    yaw_deg: float = 0.0
    grounded: bool = True
    flames: int = 3
    carried: int = 0
    invuln_ticks: int = 0
    pulse_cd_ticks: int = 0
    dash_ticks: int = 0
    dash_cd_ticks: int = 0
    dash_dir: list[float] = field(default_factory=lambda: [0.0, 1.0])
    charm_ticks: int = 0
    launched: bool = False
    respawn_ticks: int = 0
    fall_hit_pending: bool = False


class Simulation:
    """Authoritative 60-Hz simulation for Nights 1–3 (Test Contract v1.1)."""

    def __init__(self, seed: int = 1, night: int = 1, scenario: dict[str, Any] | None = None) -> None:
        if night not in NIGHT_CONFIGS:
            raise ContractInputError(f"Unsupported night={night} (expected 1, 2, or 3).")
        self.seed = int(seed)
        self.night = night
        self.cfg = NIGHT_CONFIGS[night]
        self.rng = random.Random(self.seed)
        self.tuning = copy.deepcopy(CONTRACT_TUNING)

        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.score = 0
        self.time_left_ticks = int(round(self.cfg.duration_s * TICK_RATE))

        self.player = Player(pos=list(self.cfg.start_pos), flames=int(self.tuning["flames"]))
        self.lanterns: list[Lantern] = [
            Lantern(id=str(item["id"]), pos=list(item["pos"])) for item in self.cfg.lanterns
        ]
        self.motes: list[Mote] = []
        self.shades: list[Shade] = []
        self.drifters: list[Drifter] = []
        self.charms: list[Charm] = [
            Charm(id=str(c["id"]), pos=list(c["pos"])) for c in self.cfg.charms
        ]
        self._mote_seq = 0
        self._shade_seq = 0
        self._drifter_seq = 0

        self.random_motes = True
        self.random_shades = True
        self.random_drifters = self.cfg.has_drifters
        self.wind_enabled = self.cfg.has_wind
        self.wind_ticks = 0
        self.wind_dir_deg = 0.0

        self._input_state: dict[str, Any] = {
            "move": [0.0, 0.0],
            "cam_yaw_deg": 0.0,
            "jump": False,
            "interact": False,
            "pulse": False,
            "dash": False,
            "pause": False,
        }
        self._prev_buttons = {
            "jump": False,
            "interact": False,
            "pulse": False,
            "dash": False,
            "pause": False,
        }

        self._apply_scenario(scenario or {})

    def _next_mote_id(self) -> str:
        self._mote_seq += 1
        return f"M{self._mote_seq}"

    def _next_shade_id(self) -> str:
        self._shade_seq += 1
        return f"S{self._shade_seq}"

    def _next_drifter_id(self) -> str:
        self._drifter_seq += 1
        return f"D{self._drifter_seq}"

    def _apply_scenario(self, sc: dict[str, Any]) -> None:
        if "random_motes" in sc:
            self.random_motes = sc["random_motes"]
        if "random_shades" in sc:
            self.random_shades = sc["random_shades"]
        if "random_drifters" in sc:
            self.random_drifters = sc["random_drifters"]
        if "wind_enabled" in sc:
            self.wind_enabled = sc["wind_enabled"]

        if "player" in sc:
            p = sc["player"]
            if "pos" in p:
                self.player.pos = list(p["pos"])
            for attr in ("carried", "flames", "invuln_ticks", "dash_cd_ticks", "pulse_cd_ticks", "charm_ticks"):
                if attr in p:
                    setattr(self.player, attr, int(p[attr]))

        if "time_left_s" in sc:
            self.time_left_ticks = int(round(float(sc["time_left_s"]) * TICK_RATE))

        if "lanterns" in sc:
            by_id = {lan.id: lan for lan in self.lanterns}
            for patch in sc["lanterns"]:
                lan = by_id.get(patch["id"])
                if lan is None:
                    raise ContractInputError(f"Unknown lantern id in scenario: {patch['id']!r}")
                if "pos" in patch:
                    lan.pos = list(patch["pos"])
                if "deposited" in patch:
                    lan.deposited = int(patch["deposited"])
                if "lit" in patch:
                    lan.lit = bool(patch["lit"])
                    if lan.lit and "deposited" not in patch:
                        lan.deposited = int(self.tuning["lantern_cost"])
                elif lan.deposited >= int(self.tuning["lantern_cost"]):
                    lan.lit = True

        if "motes" in sc:
            for m in sc["motes"]:
                if isinstance(m, dict):
                    self.motes.append(
                        Mote(
                            id=self._next_mote_id(),
                            pos=list(m["pos"]),
                            kind=m.get("kind", "random"),
                            ttl_ticks=m.get("ttl_ticks"),
                        )
                    )
                else:
                    self.motes.append(Mote(id=self._next_mote_id(), pos=list(m), kind="random"))
        elif self.random_motes:
            indices = list(range(len(self.cfg.mote_spawns)))
            self.rng.shuffle(indices)
            for idx in indices[:MOTE_INITIAL_COUNT]:
                self.motes.append(
                    Mote(id=self._next_mote_id(), pos=list(self.cfg.mote_spawns[idx]), kind="random")
                )

        if "shades" in sc:
            for item in sc["shades"]:
                sid = item.get("id") or self._next_shade_id()
                if sid.startswith("S") and sid[1:].isdigit():
                    self._shade_seq = max(self._shade_seq, int(sid[1:]))
                st = item.get("state", "wander")
                tl = int(item.get("state_ticks_left", 0))
                sh = Shade(
                    id=sid,
                    pos=list(item["pos"]),
                    state=st,
                    stun_ticks=tl if st == "stunned" else 0,
                    recoil_ticks=tl if st == "recoil" else 0,
                    spawning_ticks=tl if st == "spawning" else 0,
                    wander_angle=self.rng.uniform(0.0, math.tau),
                )
                self.shades.append(sh)

        if "drifters" in sc:
            self.drifters = []
            for item in sc["drifters"]:
                did = item.get("id") or self._next_drifter_id()
                if did.startswith("D") and did[1:].isdigit():
                    self._drifter_seq = max(self._drifter_seq, int(did[1:]))
                st = item.get("state", "idle")
                stolen = int(item.get("stolen", 0))
                self.drifters.append(
                    Drifter(
                        id=did,
                        pos=list(item["pos"]),
                        state=st,
                        stolen=stolen,
                        has_stolen=stolen > 0 or st == "flee",
                        flee_ticks=DRIFTER_FLEE_TICKS if st == "flee" else 0,
                        wander_angle=self.rng.uniform(0.0, math.tau),
                    )
                )

        if "charms" in sc:
            self.charms = []
            for idx, item in enumerate(sc["charms"], start=1):
                cid = item.get("id") or f"C{idx}"
                self.charms.append(
                    Charm(
                        id=cid,
                        pos=list(item["pos"]),
                        available=bool(item.get("available", True)),
                        respawn_ticks=int(item.get("respawn_ticks", 0)),
                    )
                )

    @property
    def time_left_s(self) -> float:
        return _r3(max(0.0, self.time_left_ticks / float(TICK_RATE)))

    def snapshot(self) -> dict[str, Any]:
        """Build Test Contract v1.1 snapshot dictionary."""
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "night": self.night,
            "state": self.state,
            "time_left_s": self.time_left_s,
            "score": self.score,
            "wind": {
                "active": self.wind_ticks > 0,
                "dir_deg": _r3(self.wind_dir_deg),
            },
            "player": {
                "pos": _pos3(self.player.pos),
                "vel": _pos3(self.player.vel),
                "grounded": self.player.grounded,
                "flames": self.player.flames,
                "carried": self.player.carried,
                "invuln": self.player.invuln_ticks > 0,
                "dash_cd_s": _r3(self.player.dash_cd_ticks / float(TICK_RATE)),
                "pulse_cd_s": _r3(self.player.pulse_cd_ticks / float(TICK_RATE)),
                "charm_s": _r3(self.player.charm_ticks / float(TICK_RATE)),
            },
            "lanterns": [
                {
                    "id": lan.id,
                    "pos": _pos3(lan.pos),
                    "lit": lan.lit,
                    "deposited": lan.deposited,
                }
                for lan in self.lanterns
            ],
            "shades": [
                {
                    "id": sh.id,
                    "pos": _pos3(sh.pos),
                    "state": sh.state,
                }
                for sh in self.shades
            ],
            "motes_active": len(self.motes),
            "motes": [
                {
                    "id": m.id,
                    "pos": _pos3(m.pos),
                    "kind": m.kind,
                    "ttl_s": None if m.ttl_ticks is None else _r3(m.ttl_ticks / float(TICK_RATE)),
                }
                for m in self.motes
            ],
            "drifters": [
                {
                    "id": d.id,
                    "pos": _pos3(d.pos),
                    "state": d.state,
                    "stolen": d.stolen,
                }
                for d in self.drifters
            ],
            "charms": [
                {
                    "id": c.id,
                    "pos": _pos3(c.pos),
                    "available": c.available,
                    "respawn_s": _r3(c.respawn_ticks / float(TICK_RATE)),
                }
                for c in self.charms
            ],
        }

    def render_state(self) -> dict[str, Any]:
        """Extended state for the 3D frontend (never emitted in headless JSONL)."""
        snap = self.snapshot()
        snap["night_name"] = self.cfg.name
        snap["player_extra"] = {
            "yaw_deg": _r3(self.player.yaw_deg),
            "dashing": self.player.dash_ticks > 0,
            "respawn_ticks": self.player.respawn_ticks,
        }
        snap["jump_pads"] = [{"pos": list(jp.pos), "radius": jp.radius} for jp in self.cfg.jump_pads]
        snap["wind_warning"] = (
            self.wind_enabled
            and self.wind_ticks == 0
            and self.sim_tick > 0
            and (WIND_PERIOD_TICKS - (self.sim_tick % WIND_PERIOD_TICKS)) <= 120
        )
        return snap

    def end_record(self) -> dict[str, Any]:
        return {
            "type": "end",
            "ticks": self.tick,
            "state": self.state,
            "score": self.score,
        }

    def _emit(self, events: list[dict[str, Any]], name: str, data: dict[str, Any]) -> None:
        events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def step(self, frame_patch: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute mandatory 12-step tick order (Ticket-02 Part 1)."""
        if self.state in ("won", "lost"):
            return []

        # 1. Read input (pause handled first)
        if frame_patch:
            for key in ("move", "cam_yaw_deg", "jump", "interact", "pulse", "dash", "pause"):
                if key in frame_patch:
                    self._input_state[key] = (
                        list(frame_patch[key]) if key == "move" else frame_patch[key]
                    )

        self.tick += 1
        events: list[dict[str, Any]] = []
        if self.tick == 1:
            self._emit(events, "night_start", {"night": self.night})

        pause_edge = bool(self._input_state["pause"]) and not self._prev_buttons["pause"]
        self._prev_buttons["pause"] = bool(self._input_state["pause"])

        if self.state == "paused":
            if pause_edge:
                self.state = "playing"
                self._emit(events, "resumed", {})
            else:
                return events
        elif pause_edge:
            self.state = "paused"
            self._emit(events, "paused", {})
            return events

        jump_edge = bool(self._input_state["jump"]) and not self._prev_buttons["jump"]
        interact_edge = bool(self._input_state["interact"]) and not self._prev_buttons["interact"]
        pulse_edge = bool(self._input_state["pulse"]) and not self._prev_buttons["pulse"]
        dash_edge = bool(self._input_state["dash"]) and not self._prev_buttons["dash"]
        self._prev_buttons["jump"] = bool(self._input_state["jump"])
        self._prev_buttons["interact"] = bool(self._input_state["interact"])
        self._prev_buttons["pulse"] = bool(self._input_state["pulse"])
        self._prev_buttons["dash"] = bool(self._input_state["dash"])

        self.sim_tick += 1

        # 2. Decrement timers
        self._step_timers()

        # 3. Move player (jump, dash, jump pads, wind) then check fall
        self._step_player(jump_edge, dash_edge, events)

        if self.player.flames > 0:
            # 4. Pick up motes and charms
            if self.player.respawn_ticks == 0:
                self._step_pickups(events)

            # 5. Lantern interact
            if interact_edge and self.player.respawn_ticks == 0:
                self._step_lantern_interact(events)

            # 6. Safe zones
            self._enforce_safe_radius()

            # 7. Pulse (Tỏa Sáng)
            if pulse_edge and self.player.respawn_ticks == 0:
                self._step_pulse(events)

            # 8. Move Shades and Drifters
            self._step_shades()
            self._step_drifters()

            # 9. Touch: Drifters steal first, then Shades hit (ascending id)
            if self.player.respawn_ticks == 0:
                self._step_drifter_steal(events)
                if self.player.invuln_ticks == 0:
                    self._step_shade_touch(events)

            # 10. Scheduled spawns (interactable starting next tick)
            self._step_spawns(events)

        # 11. Win / Loss evaluation
        self._evaluate_outcome(events)
        return events

    def _step_timers(self) -> None:
        if self.time_left_ticks > 0:
            self.time_left_ticks -= 1
        if self.player.dash_cd_ticks > 0:
            self.player.dash_cd_ticks -= 1
        if self.player.pulse_cd_ticks > 0:
            self.player.pulse_cd_ticks -= 1
        if self.player.invuln_ticks > 0:
            self.player.invuln_ticks -= 1
        if self.player.charm_ticks > 0:
            self.player.charm_ticks -= 1

        for sh in self.shades:
            if sh.spawning_ticks > 0:
                sh.spawning_ticks -= 1
                if sh.spawning_ticks == 0 and sh.state == "spawning":
                    sh.state = "wander"
            if sh.stun_ticks > 0:
                sh.stun_ticks -= 1
                if sh.stun_ticks == 0 and sh.state == "stunned":
                    sh.state = "wander"
            if sh.recoil_ticks > 0:
                sh.recoil_ticks -= 1
                if sh.recoil_ticks == 0 and sh.state == "recoil":
                    sh.state = "wander"
            if sh.safe_repel_ticks > 0:
                sh.safe_repel_ticks -= 1

        kept_motes: list[Mote] = []
        for m in self.motes:
            if m.ttl_ticks is not None:
                m.ttl_ticks -= 1
                if m.ttl_ticks <= 0:
                    continue
            kept_motes.append(m)
        self.motes = kept_motes

        for c in self.charms:
            if not c.available and c.respawn_ticks > 0:
                c.respawn_ticks -= 1
                if c.respawn_ticks == 0:
                    c.available = True

        if self.wind_enabled:
            if self.wind_ticks > 0:
                self.wind_ticks -= 1
            elif self.sim_tick > 0 and self.sim_tick % WIND_PERIOD_TICKS == 0:
                self.wind_ticks = WIND_DURATION_TICKS
                self.wind_dir_deg = round(self.rng.uniform(0.0, 360.0), 1)

    def _step_player(self, jump_edge: bool, dash_edge: bool, events: list[dict[str, Any]]) -> None:
        p = self.player
        if p.respawn_ticks > 0:
            p.respawn_ticks -= 1
            if p.respawn_ticks == 0:
                p.pos = list(self.cfg.start_pos)
                p.vel = [0.0, 0.0, 0.0]
                p.grounded = True
                p.launched = False
                p.dash_ticks = 0
                p.invuln_ticks = int(round(float(self.tuning["invuln_s"]) * TICK_RATE))
            return

        mx, mz = float(self._input_state["move"][0]), float(self._input_state["move"][1])
        theta = math.radians(float(self._input_state["cam_yaw_deg"]))
        wx = mx * math.cos(theta) + mz * math.sin(theta)
        wz = -mx * math.sin(theta) + mz * math.cos(theta)
        mag = math.hypot(wx, wz)
        if mag > 1.0:
            wx /= mag
            wz /= mag
        if mag > 1e-4:
            p.yaw_deg = math.degrees(math.atan2(wx, wz))

        # Dash activation (Ticket-02 Part 1 & Bùa Gió)
        if dash_edge and p.dash_ticks == 0 and (p.dash_cd_ticks == 0 or p.charm_ticks > 0):
            p.dash_ticks = DASH_DURATION_TICKS
            p.dash_cd_ticks = 0 if p.charm_ticks > 0 else DASH_COOLDOWN_TICKS
            p.launched = False
            if mag > 1e-4:
                p.dash_dir = [wx / mag, wz / mag]
            else:
                yr = math.radians(p.yaw_deg)
                p.dash_dir = [math.sin(yr), math.cos(yr)]
            self._emit(events, "dash", {})

        if p.dash_ticks > 0:
            dash_speed = float(self.tuning["dash_speed"])
            p.vel[0] = p.dash_dir[0] * dash_speed
            p.vel[2] = p.dash_dir[1] * dash_speed
            p.vel[1] = 0.0  # Air dash holds elevation
            p.dash_ticks -= 1
        else:
            if not p.launched:
                run_speed = CHARM_RUN_SPEED if p.charm_ticks > 0 else float(self.tuning["player_speed"])
                p.vel[0] = wx * run_speed
                p.vel[2] = wz * run_speed

            if jump_edge and p.grounded:
                p.vel[1] = JUMP_SPEED_MPS
                p.grounded = False
                p.launched = False

            if not p.grounded:
                p.vel[1] += GRAVITY_MPS2 * DT

        # Strong wind horizontal push (Night 3)
        wind_dx = 0.0
        wind_dz = 0.0
        if self.wind_ticks > 0:
            wrad = math.radians(self.wind_dir_deg)
            wind_dx = math.cos(wrad) * WIND_PUSH_SPEED * DT
            wind_dz = math.sin(wrad) * WIND_PUSH_SPEED * DT

        prev_x, prev_y, prev_z = p.pos[0], p.pos[1], p.pos[2]
        cand_x = prev_x + p.vel[0] * DT + wind_dx
        cand_z = prev_z + p.vel[2] * DT + wind_dz
        cand_y = prev_y + p.vel[1] * DT

        cand_x, cand_z = resolve_obstacles(self.night, cand_x, cand_z, prev_y, prev_x, prev_z)
        p.pos[0], p.pos[2] = cand_x, cand_z

        ground_y = support_height_for(self.night, cand_x, cand_z, prev_y)
        if ground_y is not None and p.vel[1] <= 0.0 and cand_y <= ground_y + 0.05:
            p.pos[1] = ground_y
            p.vel[1] = 0.0
            p.grounded = True
            p.launched = False
        else:
            p.pos[1] = cand_y
            if ground_y is None or p.pos[1] > ground_y + 0.05:
                p.grounded = False

        # Jump pad trigger (Nights 2 & 3)
        if not p.launched and p.dash_ticks == 0:
            for jp in self.cfg.jump_pads:
                if _dist_xz(p.pos, jp.pos) <= jp.radius and abs(p.pos[1] - jp.pos[1]) <= 0.6:
                    p.vel[0] = jp.dir_xz[0] * jp.vh
                    p.vel[1] = jp.vy
                    p.vel[2] = jp.dir_xz[1] * jp.vh
                    p.grounded = False
                    p.launched = True
                    break

        # Fall check (Y < -10, once, ignores invuln)
        if bool(self.tuning["fall_enabled"]) and p.pos[1] < FALL_Y_THRESHOLD and not p.fall_hit_pending:
            p.flames = max(0, p.flames - 1)
            lost = p.carried
            p.carried = 0
            p.vel = [0.0, 0.0, 0.0]
            p.dash_ticks = 0
            p.launched = False
            p.fall_hit_pending = True
            self._emit(
                events,
                "player_hit",
                {"by": "fall", "flames": p.flames, "dropped": lost, "lost": lost},
            )
            if p.flames > 0:
                p.respawn_ticks = RESPAWN_DELAY_TICKS
                p.fall_hit_pending = False

    def _step_pickups(self, events: list[dict[str, Any]]) -> None:
        cap = int(self.tuning["carry_capacity"])
        radius = float(self.tuning["pickup_radius"])
        remaining: list[Mote] = []
        for m in self.motes:
            if (
                self.player.carried < cap
                and _dist_xz(self.player.pos, m.pos) <= radius
                and abs(self.player.pos[1] - m.pos[1]) <= VERTICAL_INTERACT_LIMIT_M
            ):
                self.player.carried += 1
                self._emit(events, "mote_picked", {"carried": self.player.carried})
            else:
                remaining.append(m)
        self.motes = remaining

        for c in self.charms:
            if (
                c.available
                and _dist_xz(self.player.pos, c.pos) <= radius
                and abs(self.player.pos[1] - c.pos[1]) <= VERTICAL_INTERACT_LIMIT_M
            ):
                c.available = False
                c.respawn_ticks = CHARM_RESPAWN_TICKS
                self.player.charm_ticks = CHARM_DURATION_TICKS
                self.player.dash_cd_ticks = 0
                self._emit(events, "charm_picked", {"charm_id": c.id, "charm_ticks": CHARM_DURATION_TICKS})

    def _step_lantern_interact(self, events: list[dict[str, Any]]) -> None:
        if self.player.carried <= 0:
            return
        ir = float(self.tuning["interact_radius"])
        cost = int(self.tuning["lantern_cost"])
        candidates = [
            (_dist_xz(self.player.pos, lan.pos), lan.id, lan)
            for lan in self.lanterns
            if not lan.lit
            and _dist_xz(self.player.pos, lan.pos) <= ir
            and abs(self.player.pos[1] - lan.pos[1]) <= VERTICAL_INTERACT_LIMIT_M
        ]
        if not candidates:
            return
        candidates.sort(key=lambda item: (item[0], item[1]))
        _, _, target = candidates[0]
        needed = max(0, cost - target.deposited)
        amount = min(self.player.carried, needed)
        if amount <= 0:
            return
        self.player.carried -= amount
        target.deposited += amount
        self.score += amount * int(self.tuning["score"]["per_mote"])
        self._emit(
            events,
            "deposit",
            {"lantern_id": target.id, "amount": amount, "deposited": target.deposited},
        )
        if target.deposited >= cost and not target.lit:
            target.lit = True
            self.score += int(self.tuning["score"]["per_lantern"])
            self._emit(events, "lantern_lit", {"lantern_id": target.id})
            sr = float(self.tuning["safe_radius"])
            for sh in self.shades:
                if _dist_xz(sh.pos, target.pos) < sr:
                    sh.safe_repel_ticks = SAFE_REPEL_MAX_TICKS

    def _enforce_safe_radius(self) -> None:
        sr = float(self.tuning["safe_radius"])
        for lan in self.lanterns:
            if not lan.lit:
                continue
            for sh in self.shades:
                dx = sh.pos[0] - lan.pos[0]
                dz = sh.pos[2] - lan.pos[2]
                dist = math.hypot(dx, dz)
                if dist < sr:
                    nx, nz = (1.0, 0.0) if dist < 1e-6 else (dx / dist, dz / dist)
                    sh.pos[0] = lan.pos[0] + nx * sr
                    sh.pos[2] = lan.pos[2] + nz * sr

    def _step_pulse(self, events: list[dict[str, Any]]) -> None:
        cost = int(self.tuning["pulse_cost"])
        if self.player.pulse_cd_ticks > 0 or self.player.carried < cost:
            return
        self.player.carried -= cost
        self.player.pulse_cd_ticks = int(round(float(self.tuning["pulse_cooldown_s"]) * TICK_RATE))

        pr = float(self.tuning["pulse_radius"])
        stun_ticks = int(round(float(self.tuning["pulse_stun_s"]) * TICK_RATE))
        push_m = float(self.tuning["pulse_push_m"])
        per_stun = int(self.tuning["score"]["per_stun"])
        origin = [self.player.pos[0], self.player.pos[1] + PULSE_ORIGIN_Y_OFFSET, self.player.pos[2]]

        stunned_ids: list[str] = []
        for sh in self.shades:
            if _dist_3d(origin, sh.pos) <= pr:
                dx = sh.pos[0] - self.player.pos[0]
                dz = sh.pos[2] - self.player.pos[2]
                dist_h = math.hypot(dx, dz)
                nx, nz = (1.0, 0.0) if dist_h < 1e-6 else (dx / dist_h, dz / dist_h)
                sh.state = "stunned"
                sh.stun_ticks = stun_ticks
                sh.recoil_ticks = 0
                sh.push_ticks = PULSE_PUSH_TICKS
                sh.push_dir = [nx, nz]
                sh.push_speed = push_m / (PULSE_PUSH_TICKS * DT)
                stunned_ids.append(sh.id)
                self.score += per_stun
        self._emit(events, "pulse", {"stunned_ids": stunned_ids})

        # Pulse also affects Drifters (Gió Lạc)
        for d in self.drifters:
            if _dist_3d(origin, d.pos) <= pr:
                if d.state == "chase":
                    d.state = "flee"
                    d.flee_ticks = DRIFTER_FLEE_TICKS
                elif d.state == "flee" and d.stolen > 0:
                    amt = d.stolen
                    d.stolen = 0
                    d.flee_ticks = DRIFTER_DROP_FLEE_TICKS
                    ground_y = support_height_for(self.night, d.pos[0], d.pos[2], d.pos[1]) or 0.0
                    for _ in range(amt):
                        self.motes.append(
                            Mote(
                                id=self._next_mote_id(),
                                pos=[d.pos[0], ground_y, d.pos[2]],
                                kind="dropped",
                                ttl_ticks=DROPPED_MOTE_TTL_TICKS,
                            )
                        )
                    self._emit(events, "drifter_drop", {"drifter_id": d.id, "amount": amt})

    def _step_shades(self) -> None:
        chase_speed = self.cfg.shade_speed
        for sh in self.shades:
            if sh.state == "spawning":
                continue
            if sh.stun_ticks > 0 or sh.recoil_ticks > 0:
                if sh.push_ticks > 0:
                    nx = sh.pos[0] + sh.push_dir[0] * sh.push_speed * DT
                    nz = sh.pos[2] + sh.push_dir[1] * sh.push_speed * DT
                    nx, nz = resolve_obstacles(self.night, nx, nz, sh.pos[1], sh.pos[0], sh.pos[2])
                    sh.pos[0], sh.pos[2] = clamp_ground_entity(self.night, nx, nz)
                    sh.push_ticks -= 1
                continue

            dist_p = _dist_xz(sh.pos, self.player.pos)
            if dist_p <= SHADE_DETECT_RADIUS:
                sh.state = "chase"
            elif dist_p > SHADE_LOSE_RADIUS:
                sh.state = "wander"

            if sh.state == "chase":
                dx = self.player.pos[0] - sh.pos[0]
                dz = self.player.pos[2] - sh.pos[2]
                if dist_p > 1e-5:
                    nx = sh.pos[0] + (dx / dist_p) * chase_speed * DT
                    nz = sh.pos[2] + (dz / dist_p) * chase_speed * DT
                    nx, nz = resolve_obstacles(self.night, nx, nz, sh.pos[1], sh.pos[0], sh.pos[2])
                    sh.pos[0], sh.pos[2] = clamp_ground_entity(self.night, nx, nz)
            else:
                sh.wander_angle += 0.4 * DT
                nx = sh.pos[0] + math.cos(sh.wander_angle) * SHADE_WANDER_SPEED * DT
                nz = sh.pos[2] + math.sin(sh.wander_angle) * SHADE_WANDER_SPEED * DT
                sh.pos[0], sh.pos[2] = clamp_ground_entity(self.night, nx, nz)

        self._enforce_safe_radius()

    def _step_drifters(self) -> None:
        kept: list[Drifter] = []
        for d in self.drifters:
            if d.state == "flee":
                d.flee_ticks -= 1
                if d.flee_ticks <= 0:
                    continue  # Removed
                dx = d.pos[0] - self.player.pos[0]
                dz = d.pos[2] - self.player.pos[2]
                dist = math.hypot(dx, dz)
                nx, nz = (1.0, 0.0) if dist < 1e-5 else (dx / dist, dz / dist)
                d.pos[0] += nx * DRIFTER_SPEED * DT
                d.pos[2] += nz * DRIFTER_SPEED * DT
                kept.append(d)
                continue

            dist_p = _dist_xz(d.pos, self.player.pos)
            if not d.has_stolen and self.player.carried >= DRIFTER_CHASE_MIN_CARRIED and dist_p <= DRIFTER_CHASE_RADIUS:
                d.state = "chase"
            else:
                d.state = "idle"

            if d.state == "chase":
                dx = self.player.pos[0] - d.pos[0]
                dz = self.player.pos[2] - d.pos[2]
                if dist_p > 1e-5:
                    d.pos[0] += (dx / dist_p) * DRIFTER_SPEED * DT
                    d.pos[2] += (dz / dist_p) * DRIFTER_SPEED * DT
            else:
                d.wander_angle += 0.5 * DT
                d.pos[0] += math.cos(d.wander_angle) * DRIFTER_IDLE_SPEED * DT
                d.pos[2] += math.sin(d.wander_angle) * DRIFTER_IDLE_SPEED * DT
            kept.append(d)
        self.drifters = kept

    def _step_drifter_steal(self, events: list[dict[str, Any]]) -> None:
        for d in sorted(self.drifters, key=lambda x: x.id):
            if d.has_stolen or d.state != "chase":
                continue
            if _dist_xz(d.pos, self.player.pos) <= DRIFTER_STEAL_RADIUS:
                amt = min(DRIFTER_STEAL_MAX, self.player.carried)
                self.player.carried -= amt
                d.stolen = amt
                d.has_stolen = True
                d.state = "flee"
                d.flee_ticks = DRIFTER_FLEE_TICKS
                self._emit(
                    events,
                    "drifter_steal",
                    {"drifter_id": d.id, "amount": amt, "carried": self.player.carried},
                )

    def _step_shade_touch(self, events: list[dict[str, Any]]) -> None:
        hr = float(self.tuning["shade_hit_radius"])
        drop_ratio = float(self.tuning["hit_drop_ratio"])
        invuln_ticks = int(round(float(self.tuning["invuln_s"]) * TICK_RATE))

        for sh in sorted(self.shades, key=lambda s: s.id):
            if sh.state not in ("wander", "chase") or sh.safe_repel_ticks > 0:
                continue
            if _dist_xz(sh.pos, self.player.pos) <= hr and abs(self.player.pos[1] - sh.pos[1]) <= VERTICAL_INTERACT_LIMIT_M:
                self.player.flames = max(0, self.player.flames - 1)
                dropped = int(math.floor(self.player.carried * drop_ratio))
                self.player.carried -= dropped
                self.player.invuln_ticks = invuln_ticks

                for _ in range(dropped):
                    ang = self.rng.uniform(0.0, math.tau)
                    rad = self.rng.uniform(1.5, 2.5)
                    mx, mz = clamp_ground_entity(
                        self.night,
                        self.player.pos[0] + rad * math.cos(ang),
                        self.player.pos[2] + rad * math.sin(ang),
                    )
                    my = support_height_for(self.night, mx, mz, self.player.pos[1]) or 0.0
                    self.motes.append(
                        Mote(
                            id=self._next_mote_id(),
                            pos=[mx, my, mz],
                            kind="dropped",
                            ttl_ticks=DROPPED_MOTE_TTL_TICKS,
                        )
                    )

                dx = sh.pos[0] - self.player.pos[0]
                dz = sh.pos[2] - self.player.pos[2]
                d = math.hypot(dx, dz)
                nx, nz = (1.0, 0.0) if d < 1e-6 else (dx / d, dz / d)
                sh.state = "recoil"
                sh.recoil_ticks = SHADE_RECOIL_TICKS
                sh.push_ticks = PULSE_PUSH_TICKS
                sh.push_dir = [nx, nz]
                sh.push_speed = SHADE_RECOIL_PUSH_M / (PULSE_PUSH_TICKS * DT)

                self._emit(
                    events,
                    "player_hit",
                    {"by": "shade", "flames": self.player.flames, "dropped": dropped},
                )
                break

    def _step_spawns(self, events: list[dict[str, Any]]) -> None:
        if self.random_motes and self.sim_tick % MOTE_SPAWN_INTERVAL_TICKS == 0:
            if len(self.motes) < MOTE_MAX_ACTIVE:
                free_pts = [
                    pt
                    for pt in self.cfg.mote_spawns
                    if all(_dist_xz(pt, m.pos) > 1.0 for m in self.motes)
                ]
                if free_pts:
                    chosen = self.rng.choice(free_pts)
                    self.motes.append(Mote(id=self._next_mote_id(), pos=list(chosen), kind="random"))

        if self.random_shades and len(self.shades) < self.cfg.shade_max_active:
            to_spawn = 0
            if self.sim_tick == SHADE_FIRST_SPAWN_TICK:
                to_spawn = 2
            elif (
                self.sim_tick > SHADE_FIRST_SPAWN_TICK
                and (self.sim_tick - SHADE_FIRST_SPAWN_TICK) % self.cfg.shade_spawn_interval_ticks == 0
            ):
                to_spawn = 1

            sr = float(self.tuning["safe_radius"])
            for _ in range(to_spawn):
                if len(self.shades) >= self.cfg.shade_max_active:
                    break
                valid_pts = [
                    pt
                    for pt in self.cfg.shade_spawns
                    if _dist_xz(pt, self.player.pos) >= SHADE_MIN_SPAWN_PLAYER_DIST
                    and all(_dist_xz(pt, lan.pos) >= sr for lan in self.lanterns if lan.lit)
                ]
                if not valid_pts:
                    break
                pt = self.rng.choice(valid_pts)
                sh = Shade(
                    id=self._next_shade_id(),
                    pos=list(pt),
                    state="spawning",
                    spawning_ticks=60,
                    wander_angle=self.rng.uniform(0.0, math.tau),
                )
                self.shades.append(sh)
                self._emit(events, "shade_spawned", {"id": sh.id})

        if (
            self.random_drifters
            and self.sim_tick > 0
            and self.sim_tick % DRIFTER_SPAWN_INTERVAL_TICKS == 0
            and len(self.drifters) < DRIFTER_MAX_ACTIVE
        ):
            pt = self.rng.choice(self.cfg.shade_spawns)
            self.drifters.append(
                Drifter(
                    id=self._next_drifter_id(),
                    pos=[pt[0], pt[1] + 1.5, pt[2]],
                    state="idle",
                    wander_angle=self.rng.uniform(0.0, math.tau),
                )
            )

    def _evaluate_outcome(self, events: list[dict[str, Any]]) -> None:
        if self.player.flames <= 0:
            self.state = "lost"
            self._emit(events, "game_over", {"result": "lost", "reason": "no_flames"})
            return
        if all(lan.lit for lan in self.lanterns):
            self.state = "won"
            bonus_t = int(math.floor(self.time_left_s)) * int(self.tuning["score"]["per_second_left"])
            bonus_f = self.player.flames * int(self.tuning["score"]["per_flame_left"])
            self.score += bonus_t + bonus_f
            self._emit(events, "game_over", {"result": "won", "reason": "all_lit"})
            return
        if self.time_left_ticks <= 0:
            self.state = "lost"
            self._emit(events, "game_over", {"result": "lost", "reason": "dawn"})
            return


def run_headless(
    seed: int,
    night: int,
    ticks: int,
    snapshot_every: int = 10,
    scenario_data: Any | None = None,
    inputs_data: Any | None = None,
) -> list[dict[str, Any]]:
    """Run headless simulation (Contract v1.1) and return ordered JSONL records."""
    if ticks < 0:
        raise ContractInputError(f"--ticks must be >= 0, got {ticks}")
    if snapshot_every < 1:
        raise ContractInputError(f"--snapshot-every must be >= 1, got {snapshot_every}")

    scenario = parse_scenario_dict(scenario_data) if scenario_data is not None else None
    frames = parse_inputs_dict(inputs_data) if inputs_data is not None else {}

    sim = Simulation(seed=seed, night=night, scenario=scenario)
    records: list[dict[str, Any]] = [sim.snapshot()]

    for step_idx in range(ticks):
        if sim.state in ("won", "lost"):
            break
        patch = frames.get(step_idx)
        events = sim.step(patch)
        records.extend(events)
        if sim.tick % snapshot_every == 0 or sim.state in ("won", "lost"):
            records.append(sim.snapshot())

    records.append(sim.end_record())
    return records
