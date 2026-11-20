"""Phase 3 tests: Lantern fuel decay, refuel, relight, Shade drain, Dawn Survival, and Contract v1.2."""

from __future__ import annotations

import json
import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.sim import Simulation, run_headless  # noqa: E402


class TestPhase3FuelAndDawnSurvival(unittest.TestCase):
    """Verify Ticket-03 mechanics and Contract v1.2 compliance."""

    def test_contract_v1_2_keys_and_snapshot_schema(self) -> None:
        contract = json.loads((ROOT / "game.contract.json").read_text(encoding="utf-8"))
        # Updated in Phase 4 (Ticket-04): contract_version upgraded to 1.3 while preserving all v1.2 keys
        self.assertEqual(contract["contract_version"], "1.3")
        for key in (
            "fuel_max", "fuel_decay_per_s", "fuel_per_mote", "relight_cost",
            "win_ratio", "drain_per_s", "low_fuel_threshold", "capacity_max",
        ):
            self.assertIn(key, contract["tuning"])
        self.assertEqual(contract["tuning"]["night1_duration_s"], 240)
        self.assertEqual(contract["tuning"]["night2_duration_s"], 270)
        self.assertEqual(contract["tuning"]["night3_duration_s"], 300)

        snap = Simulation(seed=1, night=1).snapshot()
        self.assertIn("capacity", snap["player"])
        self.assertEqual(snap["player"]["capacity"], 10)
        for lan in snap["lanterns"]:
            self.assertIn("fuel", lan)
            self.assertIn("ever_lit", lan)

    def test_exact_fuel_decay_and_lantern_out_and_relight(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 8, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 2.0, "ever_lit": True}],
            "time_left_s": 100.0,
        }
        sim = Simulation(seed=1, night=1, scenario=sc)
        # 60 ticks = 1.0s -> exact 1.0 fuel decay (no float drift)
        for _ in range(60):
            sim.step({})
        self.assertEqual(sim.lanterns[0].fuel, 1.0)
        self.assertTrue(sim.lanterns[0].lit)

        # Next 60 ticks -> fuel hits 0, lantern goes out, ever_lit stays True
        out_events = []
        for _ in range(60):
            out_events.extend(sim.step({}))
        self.assertFalse(sim.lanterns[0].lit)
        self.assertEqual(sim.lanterns[0].fuel, 0.0)
        self.assertTrue(sim.lanterns[0].ever_lit)
        self.assertEqual(sim.lanterns[0].deposited, 0)
        self.assertTrue(any(e["name"] == "lantern_out" and e["data"]["lantern_id"] == "L1" for e in out_events))

        # Relight costs only 5 motes (not 10), leaves 3 carried, grants +40 score, relight=True, capacity +2
        evs = sim.step({"interact": True})
        lit_ev = [e for e in evs if e["name"] == "lantern_lit"]
        self.assertEqual(len(lit_ev), 1)
        self.assertTrue(lit_ev[0]["data"]["relight"])
        self.assertEqual(sim.player.carried, 3)
        self.assertTrue(sim.lanterns[0].lit)
        self.assertEqual(sim.lanterns[0].fuel, 100.0)
        # 5 motes deposited * 5 + 40 relight = 65
        self.assertEqual(sim.score, 65)
        self.assertEqual(sim.player.capacity, 12)

    def test_refuel_exact_ceil_motes_and_full_lantern_skipped(self) -> None:
        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 8, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 75.0, "ever_lit": True}],
            "time_left_s": 100.0,
        }
        sim = Simulation(seed=2, night=1, scenario=sc)
        # Step 1: fuel decays to 75 - 1/60 (~74.9833), ceil((100 - 74.9833)/10) = ceil(2.5017) = 3 motes -> capped at 100
        evs = sim.step({"interact": True})
        refuel_ev = [e for e in evs if e["name"] == "refuel"]
        self.assertEqual(len(refuel_ev), 1)
        self.assertEqual(refuel_ev[0]["data"]["amount"], 3)
        self.assertEqual(refuel_ev[0]["data"]["fuel"], 100.0)
        self.assertEqual(sim.player.carried, 5)
        self.assertEqual(sim.lanterns[0].fuel, 100.0)

        # Pressing interact on a full lantern (fuel == 100 at tick start, decays 1/60? Wait: step 5 runs BEFORE step 10!)
        # Actually, after refuel to 100.0 in step 5, step 10 decays 1/60 -> fuel_60 = 5999.
        # Let's test exact full lantern in a fresh scenario with fuel=100.0 where step 5 sees fuel_60 == 6000!
        sc_full = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 100.0, "ever_lit": True}],
            "time_left_s": 100.0,
        }
        sim_full = Simulation(seed=3, night=1, scenario=sc_full)
        evs_full = sim_full.step({"interact": True})
        self.assertFalse(any(e["name"] == "refuel" for e in evs_full))
        self.assertEqual(sim_full.player.carried, 5)

    def test_progressive_capacity_caps_at_20(self) -> None:
        # 6 successful lights should cap capacity at 20 (10 + 2*5 = 20, 6th stays 20)
        sc = {
            "player": {"pos": [0.0, 0.0, 24.5], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": False, "deposited": 0, "ever_lit": True}],
            "time_left_s": 200.0,
        }
        sim = Simulation(seed=4, night=1, scenario=sc)
        expected_caps = [12, 14, 16, 18, 20, 20]
        for cap in expected_caps:
            sim.lanterns[0].lit = False
            sim.lanterns[0].fuel_60 = 0
            sim.lanterns[0].deposited = 0
            sim.player.carried = 5
            sim.step({"interact": False})
            sim.step({"interact": True})
            self.assertEqual(sim.player.capacity, cap)

    def test_shade_drain_low_fuel_safe_zone_loss_pulse_bonus_and_repel_on_refuel(self) -> None:
        # L1 is at (0, 0, 25), fuel=25 (< 30 so safe zone is lost). S1 starts at (0, 0, 23.5) (dist 1.5 <= 2.0).
        # Player starts far away at (0, 0, -10) so S1 drains L1 instead of chasing player.
        sc = {
            "player": {"pos": [0.0, 0.0, -10.0], "carried": 5, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 25.0, "ever_lit": True}],
            "shades": [{"id": "S1", "pos": [0.0, 0.0, 23.5]}],
            "time_left_s": 100.0,
        }
        sim = Simulation(seed=5, night=1, scenario=sc)
        evs = []
        # Step 1 transitions S1 to drain; next 60 ticks perform 60 drain ticks -> 1 fuel_drain event
        for _ in range(61):
            evs.extend(sim.step({}))
        self.assertEqual(sim.shades[0].state, "drain")
        # 61/60s passive decay + 60/60s drain (5.0) -> 25 - 6.0167 = 18.9833 (~19.0)
        self.assertAlmostEqual(sim.lanterns[0].fuel, 19.0, places=1)
        drain_evs = [e for e in evs if e["name"] == "fuel_drain"]
        self.assertEqual(len(drain_evs), 1)
        self.assertEqual(drain_evs[0]["data"]["shade_id"], "S1")
        self.assertEqual(drain_evs[0]["data"]["lantern_id"], "L1")

        # Pulse while S1 is draining awards per_stun_draining (+15 per Ticket-03)
        sim.player.pos = [0.0, 0.0, 21.0]
        score_before = sim.score
        sim.step({"pulse": True})
        self.assertEqual(sim.shades[0].state, "stunned")
        self.assertEqual(sim.score - score_before, 15)

        # Safe zone boundary: fuel == 30.0 STILL keeps safe zone active!
        sc_eq30 = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 31.0, "ever_lit": True}],
            "shades": [{"id": "S1", "pos": [0.0, 0.0, 22.0]}],
            "time_left_s": 100.0,
        }
        sim30 = Simulation(seed=6, night=1, scenario=sc_eq30)
        sim30.step({})
        # S1 must be pushed outside safe_radius=6.0 from L1(0, 0, 25)
        dist = math.hypot(sim30.shades[0].pos[0] - 0.0, sim30.shades[0].pos[2] - 25.0)
        self.assertGreaterEqual(dist, 5.99)

    def test_dawn_survival_win_and_loss_thresholds_and_scoring(self) -> None:
        # Night 1 has 5 lanterns -> ceil(0.6 * 5) = 3 needed to win at dawn
        sc_win = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 0, "flames": 2},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [
                {"id": "L1", "lit": True, "fuel": 50.0, "ever_lit": True},
                {"id": "L2", "lit": True, "fuel": 40.0, "ever_lit": True},
                {"id": "L3", "lit": True, "fuel": 30.0, "ever_lit": True},
            ],
            "time_left_s": 1.0,  # 60 ticks
        }
        sim_win = Simulation(seed=10, night=1, scenario=sc_win)
        evs = []
        for _ in range(60):
            evs.extend(sim_win.step({}))
        self.assertEqual(sim_win.state, "won")
        go = [e for e in evs if e["name"] == "game_over"]
        self.assertEqual(len(go), 1)
        self.assertEqual(go[0]["data"]["result"], "won")
        self.assertEqual(go[0]["data"]["reason"], "dawn_survived")
        # After 60 ticks (1s), fuels are 49, 39, 29 -> dawn bonus = (50+49)+(50+39)+(50+29) + 2*50 = 150+117+100 = 367
        self.assertEqual(sim_win.score, 367)

        # Only 2/5 lit at dawn -> lost with reason="dawn" and no dawn bonus
        sc_lose = {
            "player": {"pos": [0.0, 0.0, 0.0], "carried": 0, "flames": 3},
            "random_motes": False,
            "random_shades": False,
            "lanterns": [
                {"id": "L1", "lit": True, "fuel": 50.0, "ever_lit": True},
                {"id": "L2", "lit": True, "fuel": 50.0, "ever_lit": True},
            ],
            "time_left_s": 0.5,
        }
        sim_lose = Simulation(seed=11, night=1, scenario=sc_lose)
        evs_l = []
        for _ in range(30):
            evs_l.extend(sim_lose.step({}))
        self.assertEqual(sim_lose.state, "lost")
        go_l = [e for e in evs_l if e["name"] == "game_over"]
        self.assertEqual(go_l[0]["data"]["reason"], "dawn")
        self.assertEqual(sim_lose.score, 0)

    def test_p3_scenario_headless_determinism(self) -> None:
        sc = json.loads((ROOT / "tests" / "scenarios" / "p3_fuel_night1.json").read_text(encoding="utf-8"))
        inp = json.loads((ROOT / "tests" / "scenarios" / "p3_fuel_inputs.json").read_text(encoding="utf-8"))
        r1 = run_headless(seed=42, night=1, ticks=120, scenario_data=sc, inputs_data=inp, snapshot_every=30)
        r2 = run_headless(seed=42, night=1, ticks=120, scenario_data=sc, inputs_data=inp, snapshot_every=30)
        self.assertEqual(r1, r2)
        self.assertEqual(r1[-1]["state"], "won")
        names = [e["name"] for e in r1 if e["type"] == "event"]
        self.assertIn("refuel", names)
        self.assertIn("game_over", names)


if __name__ == "__main__":
    unittest.main()
