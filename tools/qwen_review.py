#!/usr/bin/env python3
"""Independent AI reviewer & spec auditor using qwen4-max-preview via ENV."""

from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    raise SystemExit(f"Python >= 3.10 required, found {sys.version.split()[0]}")

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import verify as verify_tool  # noqa: E402

DEFAULT_BASE_URL = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen4-max-preview"

SYSTEM_PROMPT = """You are an independent senior SDLC reviewer auditing a student project ("Đảo Đèn Lồng", a 3D game with a deterministic headless Test Contract).
Your job is to catch flaws the coding agent may have missed or rationalized away.
Be concise, concrete, and skeptical. Check for:
1. Requirement / Test Contract mismatches or invented unrequested features.
2. Coupling between pure simulation logic and 3D rendering, or non-determinism hazards.
3. Weak/tautological tests ("always pass" tests) or missing edge cases.
4. Security issues (committed keys/ENV) or missing verification evidence.

End your review with a single final line (no trailing text):
VERDICT: PASS
or
VERDICT: BLOCKER - <short reason>
"""


def load_api_key() -> str:
    """Load QWEN_API from environment or local ENV/.env without printing it."""
    if os.environ.get("QWEN_API"):
        return os.environ["QWEN_API"].strip()
    for fname in ("ENV", ".env"):
        path = ROOT / fname
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "QWEN_API":
                    return v.strip().strip('"').strip("'")
    raise RuntimeError("QWEN_API not found in environment, ENV, or .env")


def resolve_repo_file(rel: str, root: pathlib.Path = ROOT) -> pathlib.Path:
    """Resolve rel inside root, rejecting symlinks, .git internals, traversal, or secret files."""
    if verify_tool.is_forbidden_secret_filename(rel):
        raise ValueError(f"Refusing to read/send forbidden secret file: {rel}")
    candidate = root / rel
    if candidate.is_symlink():
        raise ValueError(f"Refusing symlink path: {rel}")
    root_resolved = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"Refusing path outside repository root: {rel}")
    rel_resolved = resolved.relative_to(root_resolved)
    if ".git" in rel_resolved.parts:
        raise ValueError(f"Refusing .git internal path: {rel}")
    if verify_tool.is_forbidden_secret_filename(str(rel_resolved)):
        raise ValueError(f"Refusing resolved forbidden secret file: {rel_resolved}")
    return resolved


def read_text_if_exists(rel: str, max_chars: int = 60000, root: pathlib.Path = ROOT) -> str:
    """Read a repo file, failing closed if it exceeds max_chars so specs/proofs are never silently cut."""
    path = resolve_repo_file(rel, root=root)
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        raise RuntimeError(f"File {rel} ({len(text)} chars) exceeds max_chars={max_chars}")
    return text


def get_git_diff(
    base_ref: str | None,
    max_chars: int = 200000,
    root: pathlib.Path = ROOT,
) -> str:
    """Collect git diff + untracked files; fail closed on git errors, empty diffs, or oversized diffs."""
    path_filter = ["--", ".", ":!docs/proof/", ":!web/vendor/"]
    cmd = ["git", "diff", base_ref, *path_filter] if base_ref else ["git", "diff", "HEAD", *path_filter]
    proc = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed (rc={proc.returncode}): {proc.stderr.strip()}")
    diff = proc.stdout.strip()

    untracked_proc = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if untracked_proc.returncode != 0:
        raise RuntimeError(
            f"git ls-files --others failed: {untracked_proc.stderr.decode('utf-8', errors='replace').strip()}"
        )
    untracked_list = [
        p.decode("utf-8", errors="surrogateescape")
        for p in untracked_proc.stdout.split(b"\x00")
        if p
    ]

    parts = []
    if diff:
        parts.append(diff)
    if untracked_list:
        parts.append("Untracked non-ignored files:\n" + "\n".join(untracked_list))
    if not parts:
        raise RuntimeError(
            f"Empty diff against {base_ref or 'HEAD'}; pass --base <ref> to audit committed changes "
            "(fail-closed to prevent vacuous review)."
        )

    combined = "\n\n".join(parts)
    if len(combined) > max_chars:
        raise RuntimeError(
            f"Diff length ({len(combined)} chars) exceeds max_chars={max_chars}; "
            "split review or pass targeted --files instead of silently truncating."
        )
    return combined


def call_qwen(prompt: str, model: str, max_tokens: int = 16384) -> tuple[str, dict]:
    api_key = load_api_key()
    base_url = os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Qwen API HTTP {exc.code}: {body[:500]}") from exc
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, usage


def is_strict_pass(review_text: str) -> bool:
    """Fail-closed check: reject any BLOCKER marker and require final non-empty line == VERDICT: PASS."""
    if "VERDICT: BLOCKER" in review_text:
        return False
    non_empty = [ln.strip() for ln in review_text.splitlines() if ln.strip()]
    return bool(non_empty) and non_empty[-1] == "VERDICT: PASS"


def check_outbound_prompt(full_prompt: str) -> None:
    """Refuse outbound API prompts that contain any secret pattern."""
    secret_hits = verify_tool.scan_text_for_secrets("outbound-prompt", full_prompt)
    if secret_hits:
        raise RuntimeError(f"Refusing to send prompt containing secret(s): {secret_hits}")


def log_token_usage(phase: str, purpose: str, model: str, usage: dict) -> None:
    log_path = ROOT / "docs" / "notes" / "token-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "phase": phase,
        "purpose": purpose,
        "model": model,
        "usage": usage,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent review via qwen4-max-preview.")
    parser.add_argument("--phase", default="0", help="Phase number 0..4.")
    parser.add_argument("--base", default=None, help="Git ref to diff against (default: HEAD).")
    parser.add_argument("--prompt", default=None, help="Custom review prompt instead of git diff.")
    parser.add_argument("--files", nargs="*", default=[], help="Extra files to include as context.")
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", DEFAULT_MODEL))
    parser.add_argument("--strict", action="store_true", help="Fail closed unless final line is VERDICT: PASS.")
    args = parser.parse_args()
    phase = verify_tool.validate_phase(str(args.phase))

    sections: list[str] = []
    if args.prompt:
        sections.append(f"## Request\n{args.prompt}")
    else:
        sections.append(f"## Phase\n{phase}")
        sections.append(f"## Diff Base\n`{args.base or 'HEAD'}`")
        spec = read_text_if_exists(f"docs/specs/phase-{phase}.md")
        if spec:
            sections.append(f"## Phase Spec (docs/specs/phase-{phase}.md)\n{spec}")
        proof = read_text_if_exists(f"docs/proof/phase-{phase}/verify.log", max_chars=20000)
        if proof:
            sections.append(f"## Latest Verification Log\n```\n{proof}\n```")
        sections.append(
            f"## Git Diff\n```diff\n{get_git_diff(args.base)}\n```"
        )

    for rel in args.files:
        text = read_text_if_exists(rel)
        if text:
            sections.append(f"## File: {rel}\n```\n{text}\n```")

    full_prompt = "\n\n".join(sections)
    check_outbound_prompt(full_prompt)
    review_text, usage = call_qwen(full_prompt, model=args.model)
    log_token_usage(phase, "custom-prompt" if args.prompt else "diff-review", args.model, usage)

    out_dir = ROOT / "docs" / "proof" / f"phase-{phase}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "qwen-review.md"
    header = (
        f"# Qwen4-Max-Preview Independent Review (phase={phase})\n"
        f"- Timestamp (UTC): {dt.datetime.now(dt.timezone.utc).isoformat()}\n"
        f"- Audited diff base: `{args.base or 'HEAD'}`\n"
        f"- Model: `{args.model}`\n"
        f"- Token usage: `{json.dumps(usage)}`\n\n"
    )
    out_file.write_text(header + review_text.rstrip() + "\n", encoding="utf-8")

    print(header + review_text)
    if args.strict and not is_strict_pass(review_text):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
