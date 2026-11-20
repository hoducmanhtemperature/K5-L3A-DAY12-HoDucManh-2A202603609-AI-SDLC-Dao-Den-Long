"""Pure deterministic 60-Hz simulation for Đảo Đèn Lồng (Phase 1 / Test Contract v1.0)."""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from typing import Any

from src.game.constants import (
    DROPPED_MOTE_TTL_TICKS,
    DT,
    FALL_Y_THRESHOLD,
    GRAVITY_MPS2,
    ISLAND_RADIUS_M,
    JUMP_SPEED_MPS,
    MOTE_INITIAL_COUNT,
    MOTE_MAX_ACTIVE,
    MOTE_SPAWN_INTERVAL_TICKS,
    NIGHT1_LANTERNS,
    NIGHT1_MOTE_SPAWNS,
    NIGHT1_SHADE_SPAWNS,
    PHASE1_TUNING,
    PULSE_PUSH_TICKS,
    RESPAWN_DELAY_TICKS,
    SAFE_REPEL_MAX_TICKS,
    SHADE_DETECT_RADIUS,
    SHADE_FIRST_SPAWN_TICK,
    SHADE_LOSE_RADIUS,
    SHADE_MAX_ACTIVE,
    SHADE_MIN_SPAWN_PLAYER_DIST,
    SHADE_RECOIL_PUSH_M,
    SHADE_RECOIL_TICKS,
    SHADE_SPAWN_INTERVAL_TICKS,
    SHADE_WANDER_SPEED,
    TICK_RATE,
)


class ContractInputError(ValueError):
    """Raised when --inputs or --scenario fails schema validation (maps to exit code 2)."""


def _r3(val: float) -> float:
    rounded = round(float(val), 3)
    return 0.0 if rounded == 0.0 else rounded


def _pos3(pos: list[float] | tuple[float, float, float]) -> list[float]:
    return [_r3(pos[0]), _r3(pos[1]), _r3(pos[2])]


def _dist_xz(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _parse_vec3(val: Any, label: str) -> list[float]:
    if not isinstance(val, (list, tuple)) or len(val) != 3 or not all(_is_num(x) for x in val):
        raise ContractInputError(f"Invalid 3D vector for {label}: {val!r}")
    return [float(val[0]), float(val[1]), float(val[2])]


def parse_inputs_dict(data: Any) -> dict[int, dict[str, Any]]:
    """Validate --inputs JSON and return frame map indexed by tick."""
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise ContractInputError("Input JSON must be an object containing a 'frames' list.")
    frames_by_tick: dict[int, dict[str, Any]] = {}
    prev_tick = -1
    for idx, raw in enumerate(data["frames"]):
        if not isinstance(raw, dict):
            raise ContractInputError(f"Frame {idx} must be an object.")
        tick = raw.get("tick")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
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
        for btn in ("jump", "interact", "pulse"):
            if btn in raw:
                if not isinstance(raw[btn], bool):
                    raise ContractInputError(f"Frame tick={tick} button {btn!r} must be boolean.")
                parsed[btn] = raw[btn]
        frames_by_tick[tick] = parsed
    return frames_by_tick


def parse_scenario_dict(data: Any) -> dict[str, Any]:
    """Validate --scenario JSON and normalize fields."""
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
        if "carried" in p:
            if not isinstance(p["carried"], int) or isinstance(p["carried"], bool) or p["carried"] < 0:
                raise ContractInputError("Scenario 'player.carried' must be a non-negative int.")
            p_out["carried"] = p["carried"]
        if "flames" in p:
            if not isinstance(p["flames"], int) or isinstance(p["flames"], bool) or p["flames"] < 0:
                raise ContractInputError("Scenario 'player.flames' must be a non-negative int.")
            p_out["flames"] = p["flames"]
        out["player"] = p_out

    for flag in ("random_motes", "random_shades"):
        if flag in data:
            if not isinstance(data[flag], bool):
                raise ContractInputError(f"Scenario {flag!r} must be a boolean.")
            out[flag] = data[flag]

    if "motes" in data:
        if not isinstance(data["motes"], list):
            raise ContractInputError("Scenario 'motes' must be a list.")
        motes: list[list[float]] = []
        for idx, item in enumerate(data["motes"]):
            if isinstance(item, dict) and "pos" in item:
                motes.append(_parse_vec3(item["pos"], f"motes[{idx}].pos"))
            else:
                motes.append(_parse_vec3(item, f"motes[{idx}]"))
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
            shades.append(s_out)
        out["shades"] = shades

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
                if (
                    not isinstance(item["deposited"], int)
                    or isinstance(item["deposited"], bool)
                    or item["deposited"] < 0
                ):
                    raise ContractInputError(f"Scenario 'lanterns[{idx}].deposited' must be int >= 0.")
                l_out["deposited"] = item["deposited"]
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
    ready_tick: int = 0


@dataclass
class Shade:
    id: str
    pos: list[float]
    state: str = "wander"
    stun_ticks: int = 0
    recoil_ticks: int = 0
    push_ticks: int = 0
    push_dir: list[float] = field(default_factory=lambda: [1.0, 0.0])
    push_speed: float = 0.0
    wander_angle: float = 0.0
    safe_repel_ticks: int = 0


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
    respawn_ticks: int = 0
    fall_hit_pending: bool = False


class Simulation:
    """Authoritative 60-Hz game state machine shared by headless CLI and 3D server."""

    def __init__(self, seed: int = 1, night: int = 1, scenario: dict[str, Any] | None = None) -> None:
        if night != 1:
            raise ContractInputError(f"Unsupported night={night} in Phase 1 (expected 1).")
        self.seed = int(seed)
        self.night = night
        self.rng = random.Random(self.seed)
        self.tuning = copy.deepcopy(PHASE1_TUNING)

        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.score = 0
        self.time_left_ticks = int(round(float(self.tuning["night1_duration_s"]) * TICK_RATE))

        self.player = Player(flames=int(self.tuning["flames"]))
        self.lanterns: list[Lantern] = [
            Lantern(id=str(item["id"]), pos=list(item["pos"])) for item in NIGHT1_LANTERNS
        ]
        self.motes: list[Mote] = []
        self.shades: list[Shade] = []
        self._mote_seq = 0
        self._shade_seq = 0

        self.random_motes = True
        self.random_shades = True

        # Active held input state (for edge detection and partial frames)
        self._input_state: dict[str, Any] = {
            "move": [0.0, 0.0],
            "cam_yaw_deg": 0.0,
            "jump": False,
            "interact": False,
            "pulse": False,
        }
        self._prev_buttons = {"jump": False, "interact": False, "pulse": False}

        self._apply_scenario(scenario or {})

    def _next_mote_id(self) -> str:
        self._mote_seq += 1
        return f"M{self._mote_seq}"

    def _next_shade_id(self) -> str:
        self._shade_seq += 1
        return f"S{self._shade_seq}"

    def _apply_scenario(self, sc: dict[str, Any]) -> None:
        if "random_motes" in sc:
            self.random_motes = sc["random_motes"]
        if "random_shades" in sc:
            self.random_shades = sc["random_shades"]

        if "player" in sc:
            p = sc["player"]
            if "pos" in p:
                self.player.pos = list(p["pos"])
            if "carried" in p:
                self.player.carried = int(p["carried"])
            if "flames" in p:
                self.player.flames = int(p["flames"])

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
                if lan.deposited >= int(self.tuning["lantern_cost"]):
                    lan.lit = True

        if "motes" in sc:
            for pos in sc["motes"]:
                self.motes.append(Mote(id=self._next_mote_id(), pos=list(pos), kind="random"))
        elif self.random_motes:
            indices = list(range(len(NIGHT1_MOTE_SPAWNS)))
            self.rng.shuffle(indices)
            for idx in indices[:MOTE_INITIAL_COUNT]:
                self.motes.append(
                    Mote(id=self._next_mote_id(), pos=list(NIGHT1_MOTE_SPAWNS[idx]), kind="random")
                )

        if "shades" in sc:
            for item in sc["shades"]:
                sid = item.get("id") or self._next_shade_id()
                if sid.startswith("S") and sid[1:].isdigit():
                    self._shade_seq = max(self._shade_seq, int(sid[1:]))
                self.shades.append(
                    Shade(
                        id=sid,
                        pos=list(item["pos"]),
                        state="wander",
                        wander_angle=self.rng.uniform(0.0, math.tau),
                    )
                )

    @property
    def time_left_s(self) -> float:
        return _r3(max(0.0, self.time_left_ticks / float(TICK_RATE)))

    def snapshot(self) -> dict[str, Any]:
        """Build Test Contract v1.0 snapshot dictionary."""
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "state": self.state,
            "time_left_s": self.time_left_s,
            "score": self.score,
            "player": {
                "pos": _pos3(self.player.pos),
                "flames": self.player.flames,
                "carried": self.player.carried,
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
            "motes": [{"id": m.id, "pos": _pos3(m.pos)} for m in self.motes],
        }

    def render_state(self) -> dict[str, Any]:
        """Extended state for the 3D frontend (never emitted in headless JSONL)."""
        snap = self.snapshot()
        snap["player_extra"] = {
            "yaw_deg": _r3(self.player.yaw_deg),
            "vel": _pos3(self.player.vel),
            "grounded": self.player.grounded,
            "invuln_ticks": self.player.invuln_ticks,
            "pulse_cd_s": _r3(self.player.pulse_cd_ticks / float(TICK_RATE)),
            "respawn_ticks": self.player.respawn_ticks,
        }
        snap["tuning"] = {
            "carry_capacity": self.tuning["carry_capacity"],
            "lantern_cost": self.tuning["lantern_cost"],
            "pulse_cost": self.tuning["pulse_cost"],
            "pulse_cooldown_s": self.tuning["pulse_cooldown_s"],
            "interact_radius": self.tuning["interact_radius"],
            "safe_radius": self.tuning["safe_radius"],
            "island_radius": ISLAND_RADIUS_M,
        }
        return snap

    def end_record(self) -> dict[str, Any]:
        return {
            "type": "end",
            "ticks": self.tick,
            "state": self.state,
            "score": self.score,
        }

    def step(self, frame_patch: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Advance simulation by exactly 1 tick (1/60 s) and return emitted event dicts."""
        if self.state != "playing":
            return []

        if frame_patch:
            for key in ("move", "cam_yaw_deg", "jump", "interact", "pulse"):
                if key in frame_patch:
                    self._input_state[key] = (
                        list(frame_patch[key]) if key == "move" else frame_patch[key]
                    )

        self.tick += 1
        self.sim_tick += 1
        events: list[dict[str, Any]] = []

        jump_edge = bool(self._input_state["jump"]) and not self._prev_buttons["jump"]
        interact_edge = bool(self._input_state["interact"]) and not self._prev_buttons["interact"]
        pulse_edge = bool(self._input_state["pulse"]) and not self._prev_buttons["pulse"]
        self._prev_buttons["jump"] = bool(self._input_state["jump"])
        self._prev_buttons["interact"] = bool(self._input_state["interact"])
        self._prev_buttons["pulse"] = bool(self._input_state["pulse"])

        # 2. Decrement timers
        if self.time_left_ticks > 0:
            self.time_left_ticks -= 1
        if self.player.pulse_cd_ticks > 0:
            self.player.pulse_cd_ticks -= 1
        if self.player.invuln_ticks > 0:
            self.player.invuln_ticks -= 1
        for sh in self.shades:
            if sh.stun_ticks > 0:
                sh.stun_ticks -= 1
                if sh.stun_ticks == 0:
                    sh.state = "wander"
            if sh.recoil_ticks > 0:
                sh.recoil_ticks -= 1
                if sh.recoil_ticks == 0 and sh.state == "recoil":
                    sh.state = "wander"
            if sh.safe_repel_ticks > 0:
                sh.safe_repel_ticks -= 1

        # Expire dropped motes whose TTL hits 0
        kept_motes: list[Mote] = []
        for m in self.motes:
            if m.ttl_ticks is not None:
                m.ttl_ticks -= 1
                if m.ttl_ticks <= 0:
                    continue
            kept_motes.append(m)
        self.motes = kept_motes

        # 3. Player movement & fall check
        self._step_player(jump_edge, events)

        if self.player.flames > 0:
            # 4. Mote pickup
            if self.player.respawn_ticks == 0:
                self._step_mote_pickup(events)

            # 5. Lantern deposit
            if interact_edge and self.player.respawn_ticks == 0:
                self._step_lantern_interact(events)

            # 6. Safe radius enforcement (and push out newly-enclosed shades)
            self._enforce_safe_radius()

            # 7. Pulse (Tỏa Sáng)
            if pulse_edge and self.player.respawn_ticks == 0:
                self._step_pulse(events)

            # 8. Move Shades
            self._step_shades()

            # 9. Shade touch
            if self.player.respawn_ticks == 0 and self.player.invuln_ticks == 0:
                self._step_shade_touch(events)

            # 10. Scheduled spawns (active starting next tick)
            self._step_spawns(events)

        # 11. Win / Loss evaluation
        self._evaluate_outcome(events)
        return events

    def _emit(self, events: list[dict[str, Any]], name: str, data: dict[str, Any]) -> None:
        events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def _step_player(self, jump_edge: bool, events: list[dict[str, Any]]) -> None:
        p = self.player
        if p.respawn_ticks > 0:
            p.respawn_ticks -= 1
            if p.respawn_ticks == 0:
                p.pos = [0.0, 0.0, 0.0]
                p.vel = [0.0, 0.0, 0.0]
                p.grounded = True
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
        speed = float(self.tuning["player_speed"])
        p.vel[0] = wx * speed
        p.vel[2] = wz * speed
        if mag > 1e-4:
            p.yaw_deg = math.degrees(math.atan2(wx, wz))

        if jump_edge and p.grounded:
            p.vel[1] = JUMP_SPEED_MPS
            p.grounded = False

        if not p.grounded:
            p.vel[1] += GRAVITY_MPS2 * DT

        prev_y = p.pos[1]
        p.pos[0] += p.vel[0] * DT
        p.pos[1] += p.vel[1] * DT
        p.pos[2] += p.vel[2] * DT

        on_island = math.hypot(p.pos[0], p.pos[2]) <= ISLAND_RADIUS_M
        if on_island and p.vel[1] <= 0.0 and prev_y >= -0.05 and p.pos[1] <= 0.0:
            p.pos[1] = 0.0
            p.vel[1] = 0.0
            p.grounded = True
        elif not on_island and p.pos[1] <= 0.0:
            p.grounded = False

        if bool(self.tuning["fall_enabled"]) and p.pos[1] < FALL_Y_THRESHOLD and not p.fall_hit_pending:
            p.flames = max(0, p.flames - 1)
            dropped = p.carried
            p.carried = 0
            p.vel = [0.0, 0.0, 0.0]
            p.fall_hit_pending = True
            self._emit(events, "player_hit", {"by": "fall", "flames": p.flames, "dropped": dropped})
            if p.flames > 0:
                p.respawn_ticks = RESPAWN_DELAY_TICKS
                p.fall_hit_pending = False

    def _step_mote_pickup(self, events: list[dict[str, Any]]) -> None:
        cap = int(self.tuning["carry_capacity"])
        radius = float(self.tuning["pickup_radius"])
        remaining: list[Mote] = []
        for m in self.motes:
            if (
                self.player.carried < cap
                and m.ready_tick <= self.sim_tick
                and _dist_xz(self.player.pos, m.pos) <= radius
                and abs(self.player.pos[1] - m.pos[1]) <= 1.5
            ):
                self.player.carried += 1
                self._emit(events, "mote_picked", {"carried": self.player.carried})
            else:
                remaining.append(m)
        self.motes = remaining

    def _step_lantern_interact(self, events: list[dict[str, Any]]) -> None:
        if self.player.carried <= 0:
            return
        ir = float(self.tuning["interact_radius"])
        cost = int(self.tuning["lantern_cost"])
        candidates = [
            (_dist_xz(self.player.pos, lan.pos), lan.id, lan)
            for lan in self.lanterns
            if not lan.lit and _dist_xz(self.player.pos, lan.pos) <= ir
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
            # Shades caught inside a newly lit lantern's safe zone are pushed out cleanly
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

        stunned_ids: list[str] = []
        for sh in self.shades:
            dx = sh.pos[0] - self.player.pos[0]
            dz = sh.pos[2] - self.player.pos[2]
            dist = math.hypot(dx, dz)
            if dist <= pr:
                nx, nz = (1.0, 0.0) if dist < 1e-6 else (dx / dist, dz / dist)
                sh.state = "stunned"
                sh.stun_ticks = stun_ticks
                sh.recoil_ticks = 0
                sh.push_ticks = PULSE_PUSH_TICKS
                sh.push_dir = [nx, nz]
                sh.push_speed = push_m / (PULSE_PUSH_TICKS * DT)
                stunned_ids.append(sh.id)
                self.score += per_stun
        self._emit(events, "pulse", {"stunned_ids": stunned_ids})

    def _clamp_shade_to_island(self, sh: Shade) -> None:
        r = math.hypot(sh.pos[0], sh.pos[2])
        limit = ISLAND_RADIUS_M - 0.5
        if r > limit and r > 1e-6:
            sh.pos[0] *= limit / r
            sh.pos[2] *= limit / r

    def _step_shades(self) -> None:
        chase_speed = float(self.tuning["shade_speed"])
        for sh in self.shades:
            if sh.stun_ticks > 0:
                if sh.push_ticks > 0:
                    sh.pos[0] += sh.push_dir[0] * sh.push_speed * DT
                    sh.pos[2] += sh.push_dir[1] * sh.push_speed * DT
                    sh.push_ticks -= 1
                    self._clamp_shade_to_island(sh)
                continue

            if sh.recoil_ticks > 0:
                if sh.push_ticks > 0:
                    sh.pos[0] += sh.push_dir[0] * sh.push_speed * DT
                    sh.pos[2] += sh.push_dir[1] * sh.push_speed * DT
                    sh.push_ticks -= 1
                    self._clamp_shade_to_island(sh)
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
                    sh.pos[0] += (dx / dist_p) * chase_speed * DT
                    sh.pos[2] += (dz / dist_p) * chase_speed * DT
            else:
                sh.wander_angle += 0.4 * DT
                sh.pos[0] += math.cos(sh.wander_angle) * SHADE_WANDER_SPEED * DT
                sh.pos[2] += math.sin(sh.wander_angle) * SHADE_WANDER_SPEED * DT
                self._clamp_shade_to_island(sh)

        self._enforce_safe_radius()

    def _step_shade_touch(self, events: list[dict[str, Any]]) -> None:
        hr = float(self.tuning["shade_hit_radius"])
        drop_ratio = float(self.tuning["hit_drop_ratio"])
        invuln_ticks = int(round(float(self.tuning["invuln_s"]) * TICK_RATE))

        for sh in sorted(self.shades, key=lambda s: s.id):
            if sh.state not in ("wander", "chase") or sh.safe_repel_ticks > 0:
                continue
            if _dist_xz(sh.pos, self.player.pos) <= hr and abs(self.player.pos[1]) <= 1.5:
                self.player.flames = max(0, self.player.flames - 1)
                dropped = int(math.floor(self.player.carried * drop_ratio))
                self.player.carried -= dropped
                self.player.invuln_ticks = invuln_ticks

                for _ in range(dropped):
                    ang = self.rng.uniform(0.0, math.tau)
                    rad = self.rng.uniform(1.5, 2.5)
                    mx = self.player.pos[0] + rad * math.cos(ang)
                    mz = self.player.pos[2] + rad * math.sin(ang)
                    mr = math.hypot(mx, mz)
                    if mr > ISLAND_RADIUS_M - 1.0 and mr > 1e-6:
                        mx *= (ISLAND_RADIUS_M - 1.0) / mr
                        mz *= (ISLAND_RADIUS_M - 1.0) / mr
                    self.motes.append(
                        Mote(
                            id=self._next_mote_id(),
                            pos=[mx, 0.0, mz],
                            kind="dropped",
                            ttl_ticks=DROPPED_MOTE_TTL_TICKS,
                            ready_tick=self.sim_tick + 1,
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
                    for pt in NIGHT1_MOTE_SPAWNS
                    if all(_dist_xz(pt, m.pos) > 1.0 for m in self.motes)
                ]
                if free_pts:
                    chosen = self.rng.choice(free_pts)
                    self.motes.append(
                        Mote(
                            id=self._next_mote_id(),
                            pos=list(chosen),
                            kind="random",
                            ready_tick=self.sim_tick + 1,
                        )
                    )

        if not self.random_shades or len(self.shades) >= SHADE_MAX_ACTIVE:
            return
        to_spawn = 0
        if self.sim_tick == SHADE_FIRST_SPAWN_TICK:
            to_spawn = 2
        elif (
            self.sim_tick > SHADE_FIRST_SPAWN_TICK
            and (self.sim_tick - SHADE_FIRST_SPAWN_TICK) % SHADE_SPAWN_INTERVAL_TICKS == 0
        ):
            to_spawn = 1

        sr = float(self.tuning["safe_radius"])
        for _ in range(to_spawn):
            if len(self.shades) >= SHADE_MAX_ACTIVE:
                break
            valid_pts = [
                pt
                for pt in NIGHT1_SHADE_SPAWNS
                if _dist_xz(pt, self.player.pos) >= SHADE_MIN_SPAWN_PLAYER_DIST
                and all(_dist_xz(pt, lan.pos) >= sr for lan in self.lanterns if lan.lit)
            ]
            if not valid_pts:
                break
            pt = self.rng.choice(valid_pts)
            sh = Shade(
                id=self._next_shade_id(),
                pos=list(pt),
                state="wander",
                wander_angle=self.rng.uniform(0.0, math.tau),
            )
            self.shades.append(sh)
            self._emit(events, "shade_spawned", {"id": sh.id})

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
    """Run headless simulation and return ordered JSONL records."""
    if ticks < 0:
        raise ContractInputError(f"--ticks must be >= 0, got {ticks}")
    if snapshot_every < 1:
        raise ContractInputError(f"--snapshot-every must be >= 1, got {snapshot_every}")

    scenario = parse_scenario_dict(scenario_data) if scenario_data is not None else None
    frames = parse_inputs_dict(inputs_data) if inputs_data is not None else {}

    sim = Simulation(seed=seed, night=night, scenario=scenario)
    records: list[dict[str, Any]] = [sim.snapshot()]

    for step_idx in range(ticks):
        if sim.state != "playing":
            break
        patch = frames.get(step_idx)
        events = sim.step(patch)
        records.extend(events)
        if sim.tick % snapshot_every == 0:
            records.append(sim.snapshot())

    records.append(sim.end_record())
    return records
