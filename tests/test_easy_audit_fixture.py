from __future__ import annotations

import json
import argparse
import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scripts.easy_audit_fixture import generate_easy_audit_fixture
from scripts import easy_audit_site_capture_smoke as capture_smoke
from scripts.easy_audit_site_capture_smoke import attach_live_capture_artifacts, write_extra_capture_snippet


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


class EasyAuditFixtureTests(unittest.TestCase):
    def test_generates_mock_careers_site_and_non_placeholder_capture(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_easy_audit_fixture(Path(tmp) / "easy-audit")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            site = manifest.get("mock_site")
            self.assertIsInstance(site, dict)
            self.assertEqual(
                [page["slug"] for page in site["pages"]],
                ["careers", "roles", "culture"],
            )
            self.assertEqual(
                sorted(site["capture_features"]),
                [
                    "animation_settle",
                    "fixed_overlay_hide_restore",
                    "internal_scroll",
                    "shadow_dom",
                    "sticky_header",
                    "tall_full_page",
                ],
            )

            page_paths = [manifest_path.parent / page["path"] for page in site["pages"]]
            for page_path in page_paths:
                self.assertTrue(page_path.exists(), page_path)

            screenshot = manifest_path.parent / "l1-careers-screenshot.png"
            width, height = png_dimensions(screenshot)
            self.assertGreaterEqual(width, 900)
            self.assertGreaterEqual(height, 600)

    def test_mock_site_contains_capture_diagnostic_targets(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_easy_audit_fixture(Path(tmp) / "easy-audit")
            root = manifest_path.parent

            careers = (root / "site" / "index.html").read_text(encoding="utf-8")
            roles = (root / "site" / "roles.html").read_text(encoding="utf-8")

            self.assertIn('class="jobs-modal"', careers)
            self.assertIn('id="jobs-modal-scroll"', careers)
            self.assertIn('href="roles.html#principal-robotics-engineer"', careers)
            self.assertIn('class="progress-fill"', careers)
            self.assertIn("animation: progress-fill 3s linear forwards", careers)
            self.assertIn("Principal Robotics Engineer", careers)
            self.assertIn("Interview plan", careers)
            self.assertIn("data-capture-sticky", roles)
            self.assertIn('id="sticky-obscured-target"', roles)
            self.assertIn("scroll-margin-top: 0", roles)

    def test_capture_smoke_script_is_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        compile_command = validation_commands()[0]

        self.assertIn("scripts/easy_audit_site_capture_smoke.py", compile_command)

    def test_capture_smoke_targets_progress_and_sticky_obscured_artifacts(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            snippet = root / "extra.js"
            write_extra_capture_snippet(
                snippet,
                roles_path=root / "roles.png",
                culture_path=root / "culture.png",
                progress_path=root / "progress.png",
                sticky_path=root / "sticky.png",
            )

            source = snippet.read_text(encoding="utf-8")
            self.assertIn("progressTarget", source)
            self.assertIn("#animation-progress", source)
            self.assertIn("stickyObscuredTarget", source)
            self.assertIn("#sticky-obscured-target", source)

    def test_live_capture_artifacts_are_added_to_review_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "l1-animation-progress.png"
            sticky = Path(tmp) / "l1-sticky-obscured-target.png"
            progress.touch()
            sticky.touch()
            manifest = {
                "steps": [
                    {"id": "l1-source-capture", "artifact_ids": ["l1-careers-screenshot"]},
                ],
                "artifacts": [
                    {"id": "l1-careers-screenshot", "type": "screenshot"},
                ],
            }
            artifacts = {
                "animation_progress": str(progress),
                "sticky_obscured_target": str(sticky),
            }

            attach_live_capture_artifacts(manifest, artifacts)

            artifact_ids = [artifact["id"] for artifact in manifest["artifacts"]]
            self.assertIn("l1-animation-progress", artifact_ids)
            self.assertIn("l1-sticky-obscured-target", artifact_ids)
            self.assertIn("l1-animation-progress", manifest["steps"][0]["artifact_ids"])
            self.assertIn("l1-sticky-obscured-target", manifest["steps"][0]["artifact_ids"])

    def test_live_capture_artifacts_skip_missing_files(self) -> None:
        manifest = {
            "steps": [
                {"id": "l1-source-capture", "artifact_ids": ["l1-careers-screenshot"]},
            ],
            "artifacts": [
                {"id": "l1-careers-screenshot", "type": "screenshot"},
            ],
        }
        artifacts = {
            "animation_progress": "artifacts/easy-audit/latest/missing-progress.png",
            "sticky_obscured_target": "artifacts/easy-audit/latest/missing-sticky.png",
        }

        attach_live_capture_artifacts(manifest, artifacts)

        artifact_ids = [artifact["id"] for artifact in manifest["artifacts"]]
        self.assertNotIn("l1-animation-progress", artifact_ids)
        self.assertNotIn("l1-sticky-obscured-target", artifact_ids)
        self.assertNotIn("l1-animation-progress", manifest["steps"][0]["artifact_ids"])
        self.assertNotIn("l1-sticky-obscured-target", manifest["steps"][0]["artifact_ids"])

    def test_failed_live_capture_main_does_not_mark_missing_artifacts_complete(self) -> None:
        class Server:
            def shutdown(self) -> None:
                pass

            def server_close(self) -> None:
                pass

        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            output_dir = Path(tmp) / "easy-audit"
            original_parse_args = capture_smoke.parse_args
            original_which = capture_smoke.shutil.which
            original_start_site_server = capture_smoke.start_site_server
            original_run_step = capture_smoke.run_step
            try:
                capture_smoke.parse_args = lambda: argparse.Namespace(  # type: ignore[assignment]
                    output_dir=output_dir,
                    session="eba-live-capture",
                    width="1280",
                    height="900",
                    json=True,
                )
                capture_smoke.shutil.which = lambda name: "playwright-cli"  # type: ignore[assignment]
                capture_smoke.start_site_server = lambda site_dir: (Server(), "http://127.0.0.1:1/")  # type: ignore[assignment]

                def fake_run_step(*args: object, **kwargs: object) -> object:
                    raise RuntimeError("simulated capture failure")

                capture_smoke.run_step = fake_run_step  # type: ignore[assignment]

                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    exit_code = capture_smoke.main()
            finally:
                capture_smoke.parse_args = original_parse_args  # type: ignore[assignment]
                capture_smoke.shutil.which = original_which  # type: ignore[assignment]
                capture_smoke.start_site_server = original_start_site_server  # type: ignore[assignment]
                capture_smoke.run_step = original_run_step  # type: ignore[assignment]

            self.assertEqual(exit_code, 1)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["live_capture"]["status"], "failed")
            artifact_ids = [artifact["id"] for artifact in manifest["artifacts"]]
            self.assertNotIn("l1-animation-progress", artifact_ids)
            self.assertNotIn("l1-sticky-obscured-target", artifact_ids)


if __name__ == "__main__":
    unittest.main()
