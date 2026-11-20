"""Smoke and fail-closed tests for Checkpoint 0 harness, secret hygiene, and headless readiness."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import qwen_review  # noqa: E402
import verify as verify_tool  # noqa: E402


def _clean_git_env() -> dict[str, str]:
    """Scrub GIT_* variables inherited from parent git hooks so temp-repo git calls stay isolated."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _init_temp_repo(tmp_dir: str) -> pathlib.Path:
    """Create an isolated temp git repo with harness tools and .githooks/pre-commit enabled."""
    env = _clean_git_env()
    repo = pathlib.Path(tmp_dir)
    subprocess.run(["git", "init"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, env=env, check=True)
    shutil.copytree(ROOT / ".githooks", repo / ".githooks")
    shutil.copytree(ROOT / "tools", repo / "tools")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_ok.py").write_text(
        "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertEqual(1 + 1, 2)\n",
        encoding="utf-8",
    )
    (repo / ".gitignore").write_text((ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, env=env, check=True)
    return repo


class TestHarnessSmoke(unittest.TestCase):
    """Verify repository hygiene, fail-closed security guards, and CP0 headless/HTTP readiness."""

    def test_hello_headless_and_local_http_serve(self) -> None:
        env = dict(os.environ)
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "hello_headless.py")],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["project"], "Dao Den Long")
        self.assertEqual(data["checkpoint"], "phase-0")
        self.assertEqual(data["mode"], "headless")
        self.assertEqual(data["http_static_status"], 200)
        self.assertEqual(data["status"], "ready")

    def test_env_ignored_and_hook_executable_in_index(self) -> None:
        env = _clean_git_env()
        ign = subprocess.run(
            ["git", "check-ignore", "ENV", ".env"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(ign.returncode, 0, ign.stderr)
        ignored = set(ign.stdout.splitlines())
        self.assertIn("ENV", ignored)
        self.assertIn(".env", ignored)

        idx = subprocess.run(
            ["git", "ls-files", "-s", ".githooks/pre-commit"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(idx.returncode, 0)
        self.assertTrue(idx.stdout.strip().startswith("100755 "), idx.stdout)

    def test_secret_scanner_boundaries_and_filenames(self) -> None:
        for prefix, tail_len in (
            ("sk-sp-", 20),
            ("sk-proj-", 24),
            ("ghp_", 30),
            ("github_pat_", 20),
            ("AKIA", 16),
            ("AIza", 35),
        ):
            hits = verify_tool.scan_text_for_secrets("sample.txt", f"KEY={prefix}{'A' * tail_len}")
            self.assertTrue(hits, f"Expected scanner to flag {prefix}")
        self.assertTrue(verify_tool.scan_text_for_secrets("k.txt", "-----BEGIN RSA " + "PRIVATE KEY-----\nabc"))
        opaque_val = "opaqueToken" + "Value1234567890"
        self.assertTrue(verify_tool.scan_text_for_secrets("cfg.py", "API_KEY='" + opaque_val + "'"))

        for below_min in ("sk-" + ("A" * 23), "ghp_" + ("A" * 29), "AKIA" + ("A" * 15)):
            self.assertEqual(verify_tool.scan_text_for_secrets("sample.txt", below_min), [])

        for label, text in (
            ("README.md", "Use sk-short or track prompt_tokens=1200 in ai-log.md."),
            (".env.example", "QWEN_API=<paste-your-local-key-here>\n"),
            ("src/sim.py", "lantern_key = 'great_lantern_01'\n"),
        ):
            self.assertEqual(verify_tool.scan_text_for_secrets(label, text), [], label)

        for forbidden in ("ENV", "ENV.local", ".env", "sub/.env.local", ".env.EXAMPLE", "c.pem", "k.key", "w.p12"):
            self.assertTrue(verify_tool.is_forbidden_secret_filename(forbidden), forbidden)
        self.assertFalse(verify_tool.is_forbidden_secret_filename(".env.example"))

    def test_phase_validation_hermetic_and_strict_review_guards(self) -> None:
        with self.assertRaises(ValueError):
            qwen_review.resolve_repo_file("ENV")
        with self.assertRaises(ValueError):
            qwen_review.resolve_repo_file("../outside.txt")
        with self.assertRaises(ValueError):
            qwen_review.resolve_repo_file("/etc/passwd")
        with self.assertRaises(ValueError):
            qwen_review.resolve_repo_file(".git/config")
        with self.assertRaises(SystemExit):
            verify_tool.validate_phase("../../escape")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = pathlib.Path(tmp)
            (tmp_root / "ENV").write_text("secret\n", encoding="utf-8")
            (tmp_root / "link.txt").symlink_to("ENV")
            with self.assertRaises(ValueError):
                qwen_review.resolve_repo_file("link.txt", root=tmp_root)

            ok_p3, issues_p3 = verify_tool.check_phase_requirements("3", root=tmp_root)
            self.assertFalse(ok_p3)
            self.assertIn("Missing phase spec", issues_p3[0])
            (tmp_root / "docs" / "specs").mkdir(parents=True)
            (tmp_root / "docs" / "specs" / "phase-3.md").write_text("# Spec\n", encoding="utf-8")
            (tmp_root / "game.contract.json").write_text("{}", encoding="utf-8")
            ok_p3_with_spec, _ = verify_tool.check_phase_requirements("3", root=tmp_root)
            self.assertTrue(ok_p3_with_spec)

        with self.assertRaises(RuntimeError):
            qwen_review.check_outbound_prompt("Authorization: " + ("sk-sp-" + "A" * 24))
        self.assertTrue(qwen_review.is_strict_pass("Looks good.\nVERDICT: PASS\n"))
        self.assertFalse(qwen_review.is_strict_pass("VERDICT: BLOCKER - mid\nVERDICT: PASS\n"))
        self.assertFalse(qwen_review.is_strict_pass("VERDICT: PASS\nTrailing text"))
        self.assertFalse(qwen_review.is_strict_pass("VERDICT: BLOCKER - bad"))
        self.assertFalse(qwen_review.is_strict_pass(""))

    def test_qwen_review_get_git_diff_fail_closed_on_empty_invalid_and_oversized(self) -> None:
        env = _clean_git_env()
        with tempfile.TemporaryDirectory() as tmp:
            repo = _init_temp_repo(tmp)
            subprocess.run(["git", "add", "."], cwd=repo, env=env, check=True)
            subprocess.run(["git", "commit", "--no-verify", "-m", "init"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE)

            # Empty diff on clean tree must fail closed
            with self.assertRaisesRegex(RuntimeError, "Empty diff"):
                qwen_review.get_git_diff(None, root=repo)

            # Invalid base ref must fail closed (not forward git error text as diff)
            with self.assertRaisesRegex(RuntimeError, "git diff failed"):
                qwen_review.get_git_diff("nonexistent_ref_xyz", root=repo)

            # Real diff exceeding max_chars must fail closed, while sufficient cap succeeds
            (repo / "big.txt").write_text("line\n" * 100, encoding="utf-8")
            subprocess.run(["git", "add", "big.txt"], cwd=repo, env=env, check=True)
            with self.assertRaisesRegex(RuntimeError, "exceeds max_chars"):
                qwen_review.get_git_diff("HEAD", max_chars=50, root=repo)
            full_diff = qwen_review.get_git_diff("HEAD", max_chars=50000, root=repo)
            self.assertIn("big.txt", full_diff)

    def test_hook_blocks_forbidden_and_staged_secret_and_allows_clean_binary(self) -> None:
        env = _clean_git_env()
        with tempfile.TemporaryDirectory() as tmp:
            repo = _init_temp_repo(tmp)

            # Staged ENV blocked
            (repo / "ENV").write_text("QWEN_API=placeholder\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", "ENV"], cwd=repo, env=env, check=True)
            env_commit = subprocess.run(["git", "commit", "-m", "leak ENV"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotEqual(env_commit.returncode, 0)
            self.assertIn("Forbidden secret file", env_commit.stdout + env_commit.stderr)
            subprocess.run(["git", "rm", "-f", "--cached", "ENV"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE)
            (repo / "ENV").unlink()

            # Staged key blocked even when worktree is sanitized
            fake_secret = "sk-sp-" + ("Z" * 28)
            (repo / "cfg.txt").write_text(f"token={fake_secret}\n", encoding="utf-8")
            subprocess.run(["git", "add", "cfg.txt"], cwd=repo, env=env, check=True)
            (repo / "cfg.txt").write_text("token=sanitized\n", encoding="utf-8")
            hook_leak = subprocess.run(["git", "commit", "-m", "leak"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotEqual(hook_leak.returncode, 0)
            self.assertIn("index:cfg.txt", hook_leak.stdout + hook_leak.stderr)

            # Remediation + clean allowlisted .png succeeds
            (repo / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
            subprocess.run(["git", "add", "cfg.txt", "icon.png", ".gitignore", ".githooks", "tools", "tests"], cwd=repo, env=env, check=True)
            ok = subprocess.run(["git", "commit", "-m", "clean"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)

            # Key appended inside allowlisted .png still fails
            (repo / "bad.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + fake_secret.encode("ascii"))
            png_leak = subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(png_leak.returncode, 1)
            self.assertIn("bad.png", png_leak.stdout)

    def test_verify_blocks_non_ascii_secret_oversized_binary_dirty_red_and_skipped(self) -> None:
        env = _clean_git_env()
        with tempfile.TemporaryDirectory() as tmp:
            repo = _init_temp_repo(tmp)
            subprocess.run(["git", "add", "."], cwd=repo, env=env, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE)

            # Non-ASCII Vietnamese secret file blocked; normal Vietnamese doc allowed
            (repo / "khóa.pem").write_text("dummy\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", "khóa.pem"], cwd=repo, env=env, check=True)
            vn_pem = subprocess.run(["git", "commit", "-m", "vn pem"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotEqual(vn_pem.returncode, 0)
            self.assertIn("Forbidden secret file", vn_pem.stdout + vn_pem.stderr)
            subprocess.run(["git", "rm", "-f", "--cached", "khóa.pem"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE)
            (repo / "khóa.pem").unlink()

            (repo / "Đảo_spec.md").write_text("Đảo Đèn Lồng\n", encoding="utf-8")
            subprocess.run(["git", "add", "Đảo_spec.md"], cwd=repo, env=env, check=True)
            vn_ok = subprocess.run(["git", "commit", "-m", "vn ok"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(vn_ok.returncode, 0, vn_ok.stdout + vn_ok.stderr)

            # Non-allowlisted binary + >1MB text + dirty tree fail closed
            (repo / "blob.bin").write_bytes(b"\x00\x01\x02")
            self.assertEqual(subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE).returncode, 1)
            (repo / "blob.bin").unlink()

            (repo / "huge.txt").write_bytes(b"a" * 1_000_050)
            self.assertEqual(subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE).returncode, 1)
            (repo / "huge.txt").unlink()

            (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            dirty = subprocess.run([sys.executable, "tools/verify.py", "--ci", "--require-clean"], cwd=repo, env=env, stdout=subprocess.PIPE, text=True)
            self.assertEqual(dirty.returncode, 1)
            self.assertIn("Clean tree check: FAIL", dirty.stdout)
            (repo / "dirty.txt").unlink()

            # Red test, skipped test, and 0-test suite fail closed
            (repo / "tests" / "test_bad.py").write_text(
                "import unittest\nclass F(unittest.TestCase):\n    def test_f(self): self.fail('boom')\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "tests/test_bad.py"], cwd=repo, env=env, check=True)
            red = subprocess.run(["git", "commit", "-m", "red"], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotEqual(red.returncode, 0)
            self.assertIn("OVERALL: FAIL", red.stdout + red.stderr)

            (repo / "tests" / "test_bad.py").write_text(
                "import unittest\nclass S(unittest.TestCase):\n    @unittest.skip('x')\n    def test_s(self): pass\n", encoding="utf-8"
            )
            skip_rc = subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE, text=True)
            self.assertEqual(skip_rc.returncode, 1)
            self.assertIn("Skipped or expected-failure tests are blocked", skip_rc.stdout)

            # Real key pasted into .env.example fails gate
            fake_secret = "sk-sp-" + ("Z" * 28)
            (repo / ".env.example").write_text(f"QWEN_API={fake_secret}\n", encoding="utf-8")
            ex_leak = subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE, text=True)
            self.assertEqual(ex_leak.returncode, 1)
            self.assertIn(".env.example", ex_leak.stdout)
            (repo / ".env.example").unlink()

            # 0-test suite fails closed
            subprocess.run(["git", "rm", "-f", "tests/test_bad.py", "tests/test_ok.py"], cwd=repo, env=env, check=True, stdout=subprocess.PIPE)
            zero_proc = subprocess.run([sys.executable, "tools/verify.py", "--ci"], cwd=repo, env=env, stdout=subprocess.PIPE, text=True)
            self.assertNotEqual(zero_proc.returncode, 0)
            self.assertIn("Ran 0 tests", zero_proc.stdout)


if __name__ == "__main__":
    unittest.main()
