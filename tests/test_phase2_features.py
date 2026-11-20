"""Unit, scenario, and Test Contract v1.1 tests for Phase 2 (Ticket-02: Ba hòn đảo)."""

from __future__ import annotations

import json
import math
import pathlib
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.sim import Simulation, run_headless  # noqa: E402


class TestPhase2Features(unittest.TestCase):
    """Verify Dash, Bùa Gió, Gió Lạc, Pause, Night 2 & Night 3 maps, Wind, and Contract v1.1."""

    def test_contract_v1_1_snapshot_and_tuning_fields(self) -> None:
        contract = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contract_version"], "1.1")
        for k in ("dash_speed", "dash_duration_s", "dash_cooldown_s", "night2_duration_s", "night3_duration_s"):
            self.assertIn(k, contract["tuning"])

        snap = Simulation(seed=1, night=2).snapshot()
        self.assertEqual(snap["night"], 2)
        self.assertIn("wind", snap)
        for pk in ("pos", "vel", "grounded", "flames", "carried", "invuln", "dash_cd_s", "pulse_cd_s", "charm_s"):
            self.assertIn(pk, snap["player"])
        self.assertIn("drifters", snap)
        self.assertIn("charms", snap)
        self.assertEqual(len(snap["lanterns"]), 6)
        self.assertEqual(len(snap["charms"]), 1)

    def test_dash_air_elevation_hold_and_cooldown(self) -> None:
        sim = Simulation(seed=1, night=1, scenario={"random_motes": False, "random_shades": False})
        # Jump first so player is airborne
        sim.step({"jump": True, "move": [0.0, 1.0]})
        for _ in range(5):
            sim.step({"jump": False, "move": [0.0, 1.0]})
        y_before_dash = sim.player.pos[1]
        self.assertGreater(y_before_dash, 0.3)

        evs = sim.step({"dash": True, "move": [0.0, 1.0]})
        self.assertTrue(any(e["name"] == "dash" for e in evs))
        self.assertAlmostEqual(sim.player.pos[1], y_before_dash, places=4)
        for _ in range(11):
            sim.step({"dash": False, "move": [0.0, 1.0]})
        self.assertAlmostEqual(sim.player.pos[1], y_before_dash, places=4)
        # Cooldown should still block immediate second dash
        evs_cd = sim.step({"dash": True})
        self.assertFalse(any(e["name"] == "dash" for e in evs_cd))

    def test_charm_boosts_speed_removes_dash_cooldown_and_respawns(self) -> None:
        sc = {
            "player": {"pos": [35.0, 0.0, 0.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
        }
        sim = Simulation(seed=1, night=2, scenario=sc)
        evs = sim.step({"move": [1.0, 0.0]})
        self.assertTrue(any(e["name"] == "charm_picked" and e["data"]["charm_id"] == "C1" for e in evs))
        self.assertFalse(sim.charms[0].available)
        self.assertGreater(sim.player.charm_ticks, 0)

        # Speed boosted to 7.2 m/s (0.12 m/tick)
        x0 = sim.player.pos[0]
        sim.step({"move": [1.0, 0.0]})
        self.assertAlmostEqual(sim.player.pos[0] - x0, 7.2 / 60.0, places=4)

        # Back-to-back dashes work with 0 cooldown while charm active
        self.assertTrue(any(e["name"] == "dash" for e in sim.step({"dash": True})))
        for _ in range(11):
            sim.step({"dash": False})
        self.assertTrue(any(e["name"] == "dash" for e in sim.step({"dash": True})))

    def test_drifter_steal_and_pulse_drop(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 7, "flames": 3, "invuln_ticks": 90},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "drifters": [{"id": "D1", "pos": [0.8, 0.0, 0.0], "state": "chase"}],
        }
        sim = Simulation(seed=2, night=2, scenario=sc)
        evs = sim.step()
        steals = [e for e in evs if e["name"] == "drifter_steal"]
        self.assertEqual(len(steals), 1)
        self.assertEqual(steals[0]["data"], {"drifter_id": "D1", "amount": 3, "carried": 4})
        self.assertEqual(sim.player.flames, 3)  # Drifters never damage Flames
        self.assertEqual(sim.drifters[0].state, "flee")

        # Pulse while fleeing with stolen motes drops them back
        evs2 = sim.step({"pulse": True})
        drops = [e for e in evs2 if e["name"] == "drifter_drop"]
        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0]["data"], {"drifter_id": "D1", "amount": 3})
        self.assertEqual(len(sim.motes), 3)

    def test_pause_freezes_sim_tick_and_time_then_resumes(self) -> None:
        sim = Simulation(seed=1, night=1, scenario={"random_motes": False, "random_shades": False})
        sim.step()
        self.assertEqual((sim.tick, sim.sim_tick), (1, 1))
        evs_p = sim.step({"pause": True})
        self.assertTrue(any(e["name"] == "paused" for e in evs_p))
        self.assertEqual(sim.state, "paused")
        t_frozen = sim.time_left_ticks
        for _ in range(5):
            sim.step({"pause": False})
        self.assertEqual(sim.sim_tick, 1)
        self.assertEqual(sim.time_left_ticks, t_frozen)
        self.assertEqual(sim.tick, 7)

        evs_r = sim.step({"pause": True})
        self.assertTrue(any(e["name"] == "resumed" for e in evs_r))
        self.assertEqual(sim.state, "playing")
        self.assertEqual(sim.sim_tick, 2)

    def test_night2_jump_pad_launches_across_to_island_b(self) -> None:
        sc = {
            "player": {"pos": [20.0, 0.0, 18.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
        }
        sim = Simulation(seed=1, night=2, scenario=sc)
        sim.step()  # triggers pad at (20,0,18)
        self.assertFalse(sim.player.grounded)
        for _ in range(110):
            sim.step()
            if sim.player.grounded:
                break
        self.assertTrue(sim.player.grounded)
        # Should land inside Island B (center (70, 0, 0), radius 28)
        dist_b = math.hypot(sim.player.pos[0] - 70.0, sim.player.pos[2])
        self.assertLessEqual(dist_b, 28.0)

    def test_night3_ramps_jump_pad_bell_tower_and_wind(self) -> None:
        # 1. Ramp at 30 deg: climb from r=30 (Y=0) to r=24 (Y=3)
        ang = math.radians(30.0)
        sc_ramp = {
            "player": {"pos": [29.5 * math.cos(ang), 0.0, 29.5 * math.sin(ang)], "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "wind_enabled": False,
        }
        sim_r = Simulation(seed=1, night=3, scenario=sc_ramp)
        for _ in range(90):
            sim_r.step({"move": [-math.cos(ang), -math.sin(ang)]})
        self.assertAlmostEqual(sim_r.player.pos[1], 3.0, places=1)

        # 2. Jump pad at (0, 3, 13) launches onto Tier 2 (Y=6)
        sc_pad = {
            "player": {"pos": [0.0, 3.0, 13.0], "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "wind_enabled": False,
        }
        sim_p = Simulation(seed=1, night=3, scenario=sc_pad)
        sim_p.step()
        for _ in range(90):
            sim_p.step()
            if sim_p.player.grounded:
                break
        self.assertTrue(sim_p.player.grounded)
        self.assertAlmostEqual(sim_p.player.pos[1], 6.0, places=2)

        # 3. Bell tower cylinder (R=2 at (0,6,0)) blocks walking through center
        sc_tower = {
            "player": {"pos": [2.2, 6.0, 0.0], "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "random_drifters": False,
            "wind_enabled": False,
        }
        sim_t = Simulation(seed=1, night=3, scenario=sc_tower)
        for _ in range(30):
            sim_t.step({"move": [-1.0, 0.0]})
        self.assertGreaterEqual(math.hypot(sim_t.player.pos[0], sim_t.player.pos[2]), 1.99)

        # 4. Night 3 Strong Wind triggers at tick 1800 for 300 ticks
        sc_wind = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": True}
        sim_w = Simulation(seed=42, night=3, scenario=sc_wind)
        for _ in range(1800):
            sim_w.step()
        self.assertTrue(sim_w.snapshot()["wind"]["active"])

    def test_night3_full_21600_ticks_performance_and_determinism(self) -> None:
        t0 = time.monotonic()
        r1 = run_headless(seed=77, night=3, ticks=21600, snapshot_every=120)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 15.0, f"Full Night 3 took {elapsed:.2f}s (budget <= 30s)")
        r2 = run_headless(seed=77, night=3, ticks=21600, snapshot_every=120)
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
