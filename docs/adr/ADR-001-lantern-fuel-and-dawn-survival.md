# ADR-001: Lantern Fuel State Machine & Dawn-Survival Win Condition (Phase 3)

- **Status:** Accepted (Phase 3 / Ticket-03, Contract v1.2)
- **Context:** Playtests showed skilled players lighting all lanterns in ~2 minutes and ending the night early. Ticket-03 replaces permanent lanterns and instant `all_lit` victory with decaying lantern fuel, Shade fuel-draining (`drain` state), and surviving until dawn with `>= ceil(0.6 * total)` lit lanterns.

## Decision
1. **Exact Integer Fuel (`fuel_60`):** Store lantern fuel internally as integer 1/60th units (`0..6000` where `6000 == 100.0` fuel) instead of floating-point subtraction. Natural decay subtracts `1` per tick; each draining Shade subtracts `5` per tick. This eliminates floating-point drift over 18,000 ticks and guarantees byte-identical determinism across platforms. Output rounds to 1 decimal place (`round(fuel_60 / 60.0, 1)`).
2. **Lantern Lifecycle:** `unlit (ever_lit=False, cost=10)` → `lit (fuel_60=6000, ever_lit=True)` → `low-fuel (<1800, safe zone disabled)` → `unlit (ever_lit=True, cost=5, lantern_out emitted)`. Refueling from `<1800` to `>=1800` restores the 6 m safe zone and repels enclosed Shades within 30 ticks.
3. **Dawn-Survival Evaluation:** Removed early `all_lit` termination. At `time_left_ticks == 0`, if `flames > 0` and `lit_count >= ceil(0.6 * total_lanterns)`, emit `game_over (won, dawn_survived)` and award `+50 + floor(fuel)` per lit lantern plus `+50` per remaining Flame.

## Consequences
- Phase 1/2 tests asserting instant win on lighting 5/5 lanterns or old `+10/mote` + time-bonus scores are invalidated by Ticket-03. They are updated explicitly (never skipped) with reasons documented in `docs/notes/assumptions.md` and `CHANGELOG.md`.
