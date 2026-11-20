#!/usr/bin/env python3
"""Single-command verification gate and proof recorder for Đảo Đèn Lồng."""

from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    raise SystemExit(f"Python >= 3.10 required, found {sys.version.split()[0]}")

import argparse
import datetime as dt
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_TEXT_SCAN_BYTES = 1_000_000
MAX_BINARY_ASSET_BYTES = 100_000_000
VALID_PHASES = {"0", "1", "2", "3", "4"}
ALLOWED_BINARY_ASSET_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".ogg", ".wav", ".mp3", ".mp4",
    ".ttf", ".woff", ".woff2", ".ico", ".glb", ".gltf",
}

SECRET_PATTERNS = [
    re.compile(r"sk-sp-[A-Za-z0-9._-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9._-]{24,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:QWEN_API|DASHSCOPE_API_KEY|OPENAI_API_KEY|API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{20,}['\"]?"),
]


def validate_phase(phase: str) -> str:
    """Validate --phase to prevent path traversal and unsupported phase labels."""
    if phase not in VALID_PHASES:
        raise SystemExit(f"Invalid --phase {phase!r}; expected one of {sorted(VALID_PHASES)}")
    return phase


def run_cmd(args: list[str], cwd: pathlib.Path = ROOT) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_cmd_bytes(args: list[str], cwd: pathlib.Path = ROOT) -> tuple[int, bytes, str]:
    """Run a subprocess returning raw stdout bytes and decoded stderr."""
    proc = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", errors="replace")


def _git_nul_paths(args: list[str]) -> tuple[int, set[str], str]:
    """Run a git -z path-listing command so non-ASCII filenames are never C-quoted."""
    rc, raw, err = run_cmd_bytes(args)
    if rc != 0:
        return rc, set(), err
    paths = {p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\x00") if p}
    return 0, paths, ""


def is_forbidden_secret_filename(rel: str) -> bool:
    """Return True if path is a local secret or private-key file (strict .env.example casing)."""
    name = pathlib.Path(rel).name
    lower = name.lower()
    if name == ".env.example":
        return False
    if lower in {"env", ".env", "id_rsa", "id_ed25519"}:
        return True
    if lower.startswith(".env.") or lower.startswith("env."):
        return True
    if lower.endswith((".key", ".pem", ".pfx", ".p12")):
        return True
    return False


def scan_text_for_secrets(source_label: str, text: str) -> list[str]:
    """Scan text for API key/token/private-key patterns."""
    hits: list[str] = []
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            hits.append(f"Potential secret pattern ({pat.pattern}) found in {source_label}")
    return hits


def _scan_raw_blob(source_label: str, rel: str, raw: bytes) -> tuple[list[str], list[str]]:
    """Scan raw bytes safely; scan allowlisted binaries as ASCII and fail closed on unknown/oversized blobs."""
    ext = pathlib.Path(rel).suffix.lower()
    is_binary = b"\x00" in raw
    if is_binary:
        if ext in ALLOWED_BINARY_ASSET_EXTS:
            if len(raw) > MAX_BINARY_ASSET_BYTES:
                return [f"Oversized binary asset > {MAX_BINARY_ASSET_BYTES} bytes (fail-closed): {source_label}"], []
            ascii_text = raw.decode("latin-1")
            hits = scan_text_for_secrets(source_label, ascii_text)
            return hits, [f"SCANNED binary asset ({len(raw)} bytes): {source_label}"]
        return [f"Unscanned non-allowlisted binary file (fail-closed): {source_label}"], []
    if len(raw) > MAX_TEXT_SCAN_BYTES:
        return [f"Oversized text file > {MAX_TEXT_SCAN_BYTES} bytes (fail-closed): {source_label}"], []
    text = raw.decode("utf-8", errors="replace")
    return scan_text_for_secrets(source_label, text), []


def check_secrets(include_staged: bool = False) -> tuple[bool, list[str], list[str]]:
    """Scan tracked index blobs, working files, and staged diffs for leaked keys."""
    issues: list[str] = []
    notes: list[str] = []

    rc_t, tracked_files, tracked_err = _git_nul_paths(["git", "ls-files", "-z"])
    if rc_t != 0:
        return False, [f"git ls-files failed: {tracked_err.strip()}"], notes

    rc_u, untracked_files, untracked_err = _git_nul_paths(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"]
    )
    if rc_u != 0:
        return False, [f"git ls-files --others failed: {untracked_err.strip()}"], notes

    rc_s, staged_files, staged_err = _git_nul_paths(["git", "diff", "--cached", "--name-only", "-z"])
    if rc_s != 0:
        return False, [f"git diff --cached failed: {staged_err.strip()}"], notes

    rc_d, deleted_staged, del_err = _git_nul_paths(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=D", "-z"]
    )
    if rc_d != 0:
        return False, [f"git diff --cached --diff-filter=D failed: {del_err.strip()}"], notes

    for rel in sorted(tracked_files | untracked_files | staged_files):
        if is_forbidden_secret_filename(rel):
            issues.append(f"Forbidden secret file in git scope: {rel}")
            continue

        if rel in tracked_files or rel in staged_files:
            if rel in deleted_staged:
                notes.append(f"Staged deletion (no index blob): {rel}")
            else:
                rc_blob, blob_bytes, blob_err = run_cmd_bytes(["git", "show", f":{rel}"])
                if rc_blob == 0:
                    blob_issues, blob_notes = _scan_raw_blob(f"index:{rel}", rel, blob_bytes)
                    issues.extend(blob_issues)
                    notes.extend(blob_notes)
                else:
                    issues.append(f"Could not read index blob for {rel}: {blob_err.strip()}")

        if include_staged and rel in staged_files:
            continue

        path = ROOT / rel
        if path.is_file():
            try:
                raw = path.read_bytes()
            except OSError as exc:
                issues.append(f"Could not read {rel}: {exc}")
            else:
                wt_issues, wt_notes = _scan_raw_blob(rel, rel, raw)
                issues.extend(wt_issues)
                notes.extend(wt_notes)

    if include_staged:
        rc_diff, diff_bytes, _ = run_cmd_bytes(["git", "diff", "--cached", "-U0"])
        if rc_diff == 0:
            diff_out = diff_bytes.decode("utf-8", errors="replace")
            for line in diff_out.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    issues.extend(scan_text_for_secrets("<staged-diff>", line[1:]))

    return len(issues) == 0, list(dict.fromkeys(issues)), list(dict.fromkeys(notes))


def check_phase_requirements(phase: str, root: pathlib.Path = ROOT) -> tuple[bool, list[str]]:
    """Ensure --phase N (>0) has its spec, contract, and deterministic headless scenario passing."""
    if phase == "0":
        return True, []
    spec_path = root / "docs" / "specs" / f"phase-{phase}.md"
    if not spec_path.is_file():
        return False, [f"Missing phase spec {spec_path.relative_to(root)} for --phase {phase}"]

    contract_path = root / "game.contract.json"
    if not contract_path.is_file():
        return False, [f"Missing game.contract.json for --phase {phase}"]

    if root == ROOT:
        # Run headless determinism double-run against phase-1 scenario when running on real repo
        sc_path = root / "tests" / "scenarios" / "p1_win_night1.json"
        in_path = root / "tests" / "scenarios" / "p1_win_inputs.json"
        if sc_path.is_file() and in_path.is_file():
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                out1 = pathlib.Path(tmp) / "run1.jsonl"
                out2 = pathlib.Path(tmp) / "run2.jsonl"
                base_args = [
                    sys.executable,
                    str(root / "src" / "headless.py"),
                    "--seed",
                    "42",
                    "--night",
                    "1",
                    "--scenario",
                    str(sc_path),
                    "--inputs",
                    str(in_path),
                    "--ticks",
                    "120",
                    "--snapshot-every",
                    "10",
                ]
                rc1, _, err1 = run_cmd([*base_args, "--out", str(out1)], cwd=root)
                rc2, _, err2 = run_cmd([*base_args, "--out", str(out2)], cwd=root)
                if rc1 != 0 or rc2 != 0:
                    return False, [f"Headless scenario failed: rc1={rc1} ({err1}) rc2={rc2} ({err2})"]
                if out1.read_text(encoding="utf-8") != out2.read_text(encoding="utf-8"):
                    return False, ["Headless determinism check failed: run1 != run2"]
    return True, []


def run_unit_tests() -> tuple[int, str]:
    """Discover and run all Python unit tests under tests/, failing on 0 tests or skipped tests."""
    tests_dir = ROOT / "tests"
    if not tests_dir.exists():
        return 1, "Missing tests/ directory."
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out = proc.stdout
    match = re.search(r"Ran (\d+) test", out)
    ran_count = int(match.group(1)) if match else 0
    if proc.returncode == 0 and ran_count == 0:
        return 1, out.rstrip() + "\nERROR: 0 tests discovered (fail-closed)."
    if proc.returncode == 0 and re.search(r"(?:skipped=|expected failures=)", out):
        return 1, out.rstrip() + "\nERROR: Skipped or expected-failure tests are blocked (fail-closed)."
    return proc.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify project health, tests, and save proof.")
    parser.add_argument("--phase", default="0", help="Phase number 0..4 (default: 0 for CP0).")
    parser.add_argument("--ci", action="store_true", help="CI mode (do not write proof files).")
    parser.add_argument("--check-staged", action="store_true", help="Also scan staged diff lines.")
    parser.add_argument("--require-clean", action="store_true", help="Fail if working tree is dirty.")
    parser.add_argument("--quiet", action="store_true", help="Only print summary on pass.")
    args = parser.parse_args()
    phase = validate_phase(str(args.phase))

    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    rc_head, head_out, _ = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    git_head = head_out.strip() if rc_head == 0 and head_out.strip() else "no-commit"
    rc_st, status_out, status_err = run_cmd(["git", "status", "--porcelain"])
    if rc_st != 0:
        tree_state = f"unknown ({status_err.strip()})"
        is_clean = False
    else:
        dirty_lines = [line for line in status_out.splitlines() if line.strip()]
        is_clean = len(dirty_lines) == 0
        tree_state = "clean" if is_clean else f"dirty ({len(dirty_lines)} uncommitted path(s))"

    rc_hk, hk_out, _ = run_cmd(["git", "config", "--get", "core.hooksPath"])
    hooks_path = hk_out.strip() if rc_hk == 0 and hk_out.strip() else "unset"

    phase_ok, phase_issues = check_phase_requirements(phase)
    secrets_ok, secret_issues, scan_notes = check_secrets(include_staged=args.check_staged)
    test_rc, test_out = run_unit_tests()

    clean_ok = (not args.require_clean) or is_clean
    passed = phase_ok and secrets_ok and (test_rc == 0) and clean_ok
    phase_label = "N/A (CP0)" if phase == "0" else ("SPEC_PRESENT" if phase_ok else "FAIL")
    lines = [
        f"=== Verification Report (phase={phase}) ===",
        f"Timestamp (UTC): {timestamp}",
        f"Git HEAD: {git_head}",
        f"Git working tree: {tree_state}",
        f"Git core.hooksPath: {hooks_path}",
        f"Python: {sys.version.split()[0]}",
        f"Phase spec check: {phase_label}",
        f"Secret scan: {'PASS' if secrets_ok else 'FAIL'}",
    ]
    if args.require_clean:
        lines.append(f"Clean tree check: {'PASS' if clean_ok else 'FAIL'}")
    for issue in phase_issues + secret_issues:
        lines.append(f"  - {issue}")
    if scan_notes:
        lines.append("Secret scan notes:")
        lines.extend(f"  - {note}" for note in scan_notes)
    lines.append("")
    lines.append("--- Unit Tests (python3 -m unittest discover -s tests -v) ---")
    lines.append(test_out.rstrip())
    lines.append("")
    lines.append(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    report = "\n".join(lines) + "\n"

    if not args.ci:
        proof_dir = ROOT / "docs" / "proof" / f"phase-{phase}"
        proof_dir.mkdir(parents=True, exist_ok=True)
        (proof_dir / "verify.log").write_text(report, encoding="utf-8")

    if not args.quiet or not passed:
        print(report, end="")
    else:
        print(f"verify.py: PASS (phase={phase}, commit={git_head}, tree={tree_state})")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
