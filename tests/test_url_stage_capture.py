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
    build_web_snapshot_data,
    build_web_snapshot_html,
    build_web_snapshot_html_from_data,
    safe_stage_output_dir,
    slugify_stage_name,
    write_url_stage_manifest,
)
from scripts.workbench_projection import project_url_stage_manifest


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
        self.assertIn('src="/artifact/artifacts/url-stage/acme/latest/page.full-page.png"', html)
        self.assertIn('data-web-target-id="target-1"', html)
        self.assertIn("left:20px;top:30px;width:200px;height:48px", html)
        self.assertIn("Apply now", html)
        self.assertIn(".web-target:hover,.web-target:focus{outline:0;background:transparent;}", html)

    def test_web_snapshot_html_escapes_attacker_controlled_target_fields(self) -> None:
        target_map = {
            "source_url": "https://example.com/jobs",
            "screenshot": {
                "path": 'artifacts/url-stage/acme/latest/page-"full".png',
                "dimensions": {"width": 1200, "height": 900},
            },
            "targets": [
                {
                    "id": 'target-1" onclick="alert(1)',
                    "rect": {"x": 20, "y": 30, "width": 200, "height": 48},
                    "label": '"><img src=x onerror=alert(1)>&<',
                    "role": 'link" aria-label="bad',
                    "target_kind": "link",
                    "selector_candidates": ['#apply"][bad="1'],
                }
            ],
        }

        rendered_html = build_web_snapshot_html(target_map)

        self.assertNotIn('onclick="alert(1)"', rendered_html)
        self.assertNotIn('<img src=x onerror=alert(1)>', rendered_html)
        self.assertNotIn('#apply"][bad="1', rendered_html)
        self.assertIn("&quot;&gt;&lt;img src=x onerror=alert(1)&gt;&amp;&lt;", rendered_html)
        self.assertIn('data-web-target-id="target-1&quot; onclick=&quot;alert(1)"', rendered_html)
        self.assertIn("page-&quot;full&quot;.png", rendered_html)
        self.assertIn("&quot;selector_candidates&quot;: [&quot;#apply\\&quot;][bad=\\&quot;1&quot;]", rendered_html)

    def test_web_snapshot_html_can_be_rendered_from_canonical_data_target_map(self) -> None:
        data = {
            "schema_version": "web_snapshot.v0",
            "projections": {
                "target_map": {
                    "source_url": "https://example.com/jobs",
                    "screenshot": {
                        "path": "artifacts/url-stage/acme/latest/page.full-page.png",
                        "dimensions": {"width": 1200, "height": 900},
                    },
                    "targets": [
                        {
                            "id": "target-canonical",
                            "rect": {"x": 20, "y": 30, "width": 200, "height": 48},
                            "label": "Canonical target",
                            "role": "link",
                            "target_kind": "link",
                            "selector_candidates": ["#canonical"],
                        }
                    ],
                }
            },
        }

        rendered_html = build_web_snapshot_html_from_data(data)

        self.assertIn('data-web-target-id="target-canonical"', rendered_html)
        self.assertIn("Canonical target", rendered_html)

    def test_web_snapshot_data_consolidates_source_trees_and_projections(self) -> None:
        blueprint = {
            "schema_version": "url_stage_blueprint.v0",
            "url": "https://example.com/jobs",
            "title": "Careers",
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

        data = build_web_snapshot_data(
            blueprint,
            screenshot_dimensions={"width": 2000, "height": 2400},
            screenshot_path="artifacts/url-stage/acme/latest/page.full-page.png",
            visible_text="Apply now\nEngineering careers\n",
            page_snapshot="button Apply now [ref=e1]\n",
        )

        self.assertEqual(data["schema_version"], "web_snapshot.v0")
        self.assertEqual(data["visual"]["coordinate_space"], "screenshot")
        self.assertEqual(data["visual"]["image"]["path"], "artifacts/url-stage/acme/latest/page.full-page.png")
        self.assertEqual(data["source_trees"], {})
        self.assertEqual(data["projections"]["target_map"]["targets"][0]["rect"], {"x": 200, "y": 400, "width": 300, "height": 80})
        self.assertEqual(data["projections"]["visible_text"]["lines"], ["Apply now", "Engineering careers"])
        self.assertEqual(data["projections"]["structure"]["source"], "normalized_blueprint_elements")
        self.assertEqual(data["projections"]["page_snapshot"]["source"], "playwright_snapshot_text")
        self.assertEqual(data["projection_catalog"]["target_map"]["coordinate_space"], "screenshot")
        self.assertEqual(
            [view["id"] for view in data["ui_views"]],
            ["snapshot", "text", "structure"],
        )
        self.assertEqual(data["replay_policy"]["snapshot_replay"], "coordinates_authoritative")
        self.assertEqual(data["replay_policy"]["live_replay"], "semantic_selectors_first_coordinates_advisory")

    def test_write_url_stage_manifest_records_web_snapshot_and_single_data_artifact(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=".url-stage-test-", dir=REPO_ROOT / "artifacts"))
        try:
            manifest_path = write_url_stage_manifest(
                output_dir=root,
                slug="acme-careers",
                url="https://example.com/jobs",
                status="passed",
                viewport={"width": 1000, "height": 800, "devicePixelRatio": 1},
                paths={
                    "web_snapshot": root / "web-snapshot.html",
                    "web_snapshot_data": root / "web-snapshot-data.json",
                    "page_screenshot": root / "page.full-page.png",
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
            set(manifest["artifacts"]),
            {"web_snapshot", "web_snapshot_data", "page_screenshot", "capture_log"},
        )
        self.assertEqual(
            manifest["artifacts"]["web_snapshot"],
            "artifacts/.url-stage-test-" + root.name.rsplit(".url-stage-test-", 1)[-1] + "/web-snapshot.html",
        )
        self.assertEqual(
            manifest["artifacts"]["web_snapshot_data"],
            "artifacts/.url-stage-test-" + root.name.rsplit(".url-stage-test-", 1)[-1] + "/web-snapshot-data.json",
        )
        self.assertEqual(manifest["screenshot"]["dimensions"], {"width": 1000, "height": 1200})

    def test_url_stage_projection_rejects_missing_canonical_web_snapshot_data(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=".url-stage-test-", dir=REPO_ROOT / "artifacts"))
        try:
            web_snapshot = root / "web-snapshot.html"
            page_screenshot = root / "page.full-page.png"
            capture_log = root / "capture.log"
            web_snapshot.write_text("<!doctype html><html></html>\n", encoding="utf-8")
            page_screenshot.write_bytes(b"fixture screenshot bytes")
            capture_log.write_text("capture log\n", encoding="utf-8")
            manifest_path = write_url_stage_manifest(
                output_dir=root,
                slug="acme-careers",
                url="https://example.com/jobs",
                status="passed",
                viewport={"width": 1000, "height": 800, "devicePixelRatio": 1},
                paths={
                    "web_snapshot": web_snapshot,
                    "web_snapshot_data": root / "missing-web-snapshot-data.json",
                    "page_screenshot": page_screenshot,
                    "capture_log": capture_log,
                },
                screenshot_dimensions={"width": 1000, "height": 1200},
            )

            with self.assertRaisesRegex(ValueError, "web_snapshot_data"):
                project_url_stage_manifest(manifest_path)
        finally:
            for child in sorted(root.glob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            root.rmdir()

    def test_validation_includes_url_stage_capture_files(self) -> None:
        from scripts.eba_cli import validation_commands

        self.assertIn([sys.executable, "tests/test_url_stage_capture.py"], validation_commands())
        self.assertIn(["node", "--check", "scripts/playwright-snippets/extract-web-blueprint.js"], validation_commands())
        self.assertIn(["node", "--check", "scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js"], validation_commands())

    def test_stage_url_parser_is_registered(self) -> None:
        from scripts.eba_cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["dev", "stage-url", "https://example.com/jobs", "--name", "example-jobs", "--no-browser"])

        self.assertEqual(args.command, "stage-url")
        self.assertEqual(args.url, "https://example.com/jobs")
        self.assertEqual(args.name, "example-jobs")
        self.assertTrue(args.no_browser)


if __name__ == "__main__":
    unittest.main()
