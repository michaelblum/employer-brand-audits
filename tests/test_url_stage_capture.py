from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_FOR_IMPORTS))

from scripts.url_stage_capture import (
    REPO_ROOT,
    build_target_map,
    build_web_snapshot_html,
    safe_stage_output_dir,
    slugify_stage_name,
    write_url_stage_manifest,
)


class UrlStageCaptureTests(unittest.TestCase):
    def test_slugify_stage_name_keeps_human_name_safe(self) -> None:
        self.assertEqual(slugify_stage_name("Acme Careers!"), "acme-careers")
        self.assertEqual(slugify_stage_name("https://example.com/jobs?q=robotics"), "example-com-jobs")

    def test_safe_stage_output_dir_refuses_repo_root(self) -> None:
        with self.assertRaises(SystemExit):
            safe_stage_output_dir(REPO_ROOT)

    def test_target_map_projects_blueprint_rects_to_screenshot_space(self) -> None:
        blueprint = {
            "url": "https://example.com/jobs",
            "viewport": {"width": 1000, "height": 800, "devicePixelRatio": 2},
            "document": {"width": 1000, "height": 1200},
            "elements": [
                {
                    "uid": "target-1",
                    "tag": "a",
                    "role": "link",
                    "accessible_name": "Apply now",
                    "text": "Apply now",
                    "selector_candidates": ["#apply", "a.cta"],
                    "document_rect": {"x": 100, "y": 200, "width": 150, "height": 40},
                    "target_kind": "link",
                    "confidence": 0.92,
                }
            ],
        }

        target_map = build_target_map(
            blueprint,
            screenshot_dimensions={"width": 2000, "height": 2400},
            screenshot_path="artifacts/url-stage/acme/latest/page.full-page.png",
        )

        self.assertEqual(target_map["schema_version"], "url_stage_target_map.v0")
        self.assertEqual(target_map["coordinate_space"], "screenshot")
        self.assertEqual(target_map["targets"][0]["rect"], {"x": 200, "y": 400, "width": 300, "height": 80})
        self.assertEqual(target_map["targets"][0]["selector_candidates"], ["#apply", "a.cta"])

    def test_web_snapshot_html_uses_image_background_and_proxy_targets(self) -> None:
        target_map = {
            "source_url": "https://example.com/jobs",
            "screenshot": {
                "path": "artifacts/url-stage/acme/latest/page.full-page.png",
                "dimensions": {"width": 1200, "height": 900},
            },
            "targets": [
                {
                    "id": "target-1",
                    "rect": {"x": 20, "y": 30, "width": 200, "height": 48},
                    "label": "Apply now",
                    "role": "link",
                    "target_kind": "link",
                    "selector_candidates": ["#apply"],
                }
            ],
        }

        html = build_web_snapshot_html(target_map)

        self.assertIn('data-web-snapshot-stage="true"', html)
        self.assertIn('src="/artifacts/url-stage/acme/latest/page.full-page.png"', html)
        self.assertIn('data-web-target-id="target-1"', html)
        self.assertIn("left:20px;top:30px;width:200px;height:48px", html)
        self.assertIn("Apply now", html)

    def test_write_url_stage_manifest_records_blueprint_and_derived_artifacts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=".url-stage-test-", dir=REPO_ROOT / "artifacts"))
        try:
            manifest_path = write_url_stage_manifest(
                output_dir=root,
                slug="acme-careers",
                url="https://example.com/jobs",
                status="passed",
                viewport={"width": 1000, "height": 800, "devicePixelRatio": 1},
                paths={
                    "blueprint": root / "web-blueprint.json",
                    "target_map": root / "target-map.json",
                    "web_snapshot": root / "web-snapshot.html",
                    "page_screenshot": root / "page.full-page.png",
                    "visible_text": root / "visible-text.txt",
                    "page_snapshot": root / "page-snapshot.txt",
                    "capture_log": root / "capture.log",
                },
                screenshot_dimensions={"width": 1000, "height": 1200},
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            for child in sorted(root.glob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            root.rmdir()

        self.assertEqual(manifest["schema_version"], "url_stage_capture.v0")
        self.assertEqual(manifest["slug"], "acme-careers")
        self.assertEqual(
            manifest["artifacts"]["web_snapshot"],
            "artifacts/.url-stage-test-" + root.name.rsplit(".url-stage-test-", 1)[-1] + "/web-snapshot.html",
        )
        self.assertEqual(manifest["screenshot"]["dimensions"], {"width": 1000, "height": 1200})


if __name__ == "__main__":
    unittest.main()
