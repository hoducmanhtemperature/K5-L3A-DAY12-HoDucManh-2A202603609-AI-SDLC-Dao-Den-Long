#!/usr/bin/env python3
"""Headless Test Contract v1.0 CLI for Đảo Đèn Lồng (no display/window required)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.game.sim import ContractInputError, run_headless  # noqa: E402


def _load_json_file(path_str: str, label: str) -> object:
    path = pathlib.Path(path_str)
    if not path.is_file():
        raise ContractInputError(f"{label} file not found: {path_str}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractInputError(f"Malformed {label} JSON ({path_str}): {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Đảo Đèn Lồng headless simulation.")
    parser.add_argument("--seed", type=int, required=True, help="Deterministic RNG seed.")
    parser.add_argument("--night", type=int, required=True, help="Night number (1 in Phase 1).")
    parser.add_argument("--scenario", default=None, help="Optional scenario JSON file.")
    parser.add_argument("--inputs", default=None, help="Optional inputs JSON file.")
    parser.add_argument("--ticks", type=int, required=True, help="Maximum simulation steps to run.")
    parser.add_argument("--out", required=True, help="Output JSONL file path.")
    parser.add_argument(
        "--snapshot-every",
        type=int,
        default=10,
        help="Emit snapshot every N ticks starting at tick 0 (default: 10).",
    )
    args = parser.parse_args(argv)

    try:
        scenario_data = _load_json_file(args.scenario, "scenario") if args.scenario else None
        inputs_data = _load_json_file(args.inputs, "inputs") if args.inputs else None
        records = run_headless(
            seed=args.seed,
            night=args.night,
            ticks=args.ticks,
            snapshot_every=args.snapshot_every,
            scenario_data=scenario_data,
            inputs_data=inputs_data,
        )
    except ContractInputError as exc:
        print(f"Contract error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
