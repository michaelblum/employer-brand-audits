from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.easy_audit_fixture import generate_easy_audit_fixture


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

    def test_capture_smoke_script_is_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        compile_command = validation_commands()[0]

        self.assertIn("scripts/easy_audit_site_capture_smoke.py", compile_command)


if __name__ == "__main__":
    unittest.main()
