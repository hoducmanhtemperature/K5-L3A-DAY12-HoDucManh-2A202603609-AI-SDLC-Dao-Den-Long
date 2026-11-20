"""Local persistent Top-10 Leaderboard for Đảo Đèn Lồng (Ticket-04)."""

from __future__ import annotations

from datetime import datetime
import json
import os
import pathlib
import re
from typing import Any

# 3-12 chars: ASCII [A-Za-z0-9_] plus Vietnamese Latin letters
NAME_RE = re.compile(r"^[A-Za-z0-9_\u00C0-\u024F\u1E00-\u1EFF]{3,12}$")
MAX_ENTRIES = 10


def default_leaderboard_path() -> pathlib.Path:
    env_path = os.environ.get("DDL_LEADERBOARD_PATH")
    if env_path:
        return pathlib.Path(env_path)
    return pathlib.Path.home() / ".local" / "share" / "dao-den-long" / "leaderboard.json"


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError("Tên phải dài 3–12 ký tự ([A-Za-z0-9_] hoặc chữ tiếng Việt không khoảng trắng).")
    return name


def _sort_key(entry: dict[str, Any]) -> tuple[int, str]:
    # Higher score first; tie-breaker: earlier achieved_at first
    return (-int(entry.get("score", 0)), str(entry.get("achieved_at", "")))


def load_entries(path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    p = path or default_leaderboard_path()
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    if not isinstance(entries, list):
        return []
    valid = [e for e in entries if isinstance(e, dict) and "name" in e and "score" in e]
    valid.sort(key=_sort_key)
    return valid[:MAX_ENTRIES]


def save_entries(entries: list[dict[str, Any]], path: pathlib.Path | None = None) -> pathlib.Path:
    p = path or default_leaderboard_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=_sort_key)[:MAX_ENTRIES]
    p.write_text(json.dumps({"entries": ordered}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def add_entry(
    name: str,
    score: int,
    nights_won: int,
    seed: int,
    achieved_at: str | None = None,
    path: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    clean_name = validate_name(name)
    nw = int(nights_won)
    if nw < 0 or nw > 3:
        raise ValueError("nights_won must be between 0 and 3.")
    ts = achieved_at or datetime.now().astimezone().isoformat(timespec="seconds")
    entry = {
        "name": clean_name,
        "score": int(score),
        "nights_won": nw,
        "achieved_at": ts,
        "seed": int(seed),
    }
    entries = load_entries(path)
    entries.append(entry)
    entries.sort(key=_sort_key)
    entries = entries[:MAX_ENTRIES]
    save_entries(entries, path)
    return entries


def export_leaderboard(out_path: pathlib.Path | str, path: pathlib.Path | None = None) -> dict[str, Any]:
    data = {"entries": load_entries(path)}
    target = pathlib.Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
