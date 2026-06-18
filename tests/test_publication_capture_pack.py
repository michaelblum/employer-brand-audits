from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    capture_pack_from_url_stage_manifests,
    generate_publication_pipeline_fixture,
    evidence_items_from_capture_pack,
    source_roster_from_capture_pack,
    source_artifacts_from_url_stage_manifest,
)


class PublicationCapturePackTests(unittest.TestCase):
    def url_stage_manifest(self, slug: str, url: str) -> dict[str, object]:
        return {
            "schema_version": "url_stage_capture.v0",
            "slug": slug,
            "url": url,
            "captured_at": "2026-06-18T12:00:00Z",
            "artifacts": {
                "visible_text": f"artifacts/url-stage/{slug}/latest/visible-text.txt",
                "web_snapshot_data": f"artifacts/url-stage/{slug}/latest/web-snapshot-data.json",
                "page_screenshot": f"artifacts/url-stage/{slug}/latest/page.full-page.png",
            },
        }

    def test_source_artifacts_from_url_stage_manifest_preserves_stage_paths(self) -> None:
        manifest = {
            "schema_version": "url_stage_capture.v0",
            "slug": "patagonia-careers-live",
            "url": "https://www.patagonia.com/jobs/",
            "captured_at": "2026-06-18T12:00:00Z",
            "artifacts": {
                "web_snapshot_data": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
                "web_snapshot": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot.html",
                "page_screenshot": "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png",
            },
        }

        source_artifacts = source_artifacts_from_url_stage_manifest(
            manifest,
            project_id="url-stage-capture-pack",
            entity_id="competitor-patagonia",
        )

        self.assertEqual(source_artifacts[0]["artifact_id"], "source:patagonia-careers-live")
        self.assertEqual(source_artifacts[0]["source_url"], "https://www.patagonia.com/jobs/")
        self.assertEqual(
            source_artifacts[0]["screenshot_path"],
            "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png",
        )
        self.assertEqual(
            source_artifacts[0]["snapshot_path"],
            "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
        )

    def test_evidence_items_from_capture_pack_maps_kilos_and_contextual_items(self) -> None:
        capture_pack = {
            "source_artifacts": [
                {
                    "artifact_id": "source:patagonia-careers-live",
                    "project_id": "url-stage-capture-pack",
                    "entity_id": "competitor-patagonia",
                    "source_url": "https://www.patagonia.com/jobs/",
                }
            ],
            "excerpts": [
                {
                    "section": "careers_messaging",
                    "evidence_text": "We offer paid time off for activism and community action.",
                    "pillar_id": "I",
                    "factor_id": "I1",
                    "theme_label": "Impact / Meaningful Work for People",
                    "confidence": "high",
                },
                {
                    "section": "notes",
                    "evidence_text": "The page has a prominent video hero.",
                    "pillar_id": "",
                    "factor_id": "",
                    "theme_label": "visual context",
                    "confidence": "medium",
                },
            ],
        }

        items = evidence_items_from_capture_pack(capture_pack)

        self.assertEqual([item["evidence_id"] for item in items], ["evidence:001", "evidence:002"])
        self.assertEqual(items[0]["pillar_id"], "I")
        self.assertEqual(items[1]["kilos_status"], "non_kilos_context")

    def test_capture_pack_from_url_stage_manifests_preserves_order_and_entity_ids(self) -> None:
        capture_pack = capture_pack_from_url_stage_manifests(
            [
                self.url_stage_manifest("patagonia-careers-live", "https://www.patagonia.com/jobs/"),
                self.url_stage_manifest("demo-client-careers-live", "https://demo-client.example/careers"),
            ],
            entity_ids=["competitor-patagonia", "client-demo"],
        )

        source_artifacts = capture_pack["source_artifacts"]
        self.assertEqual(
            [artifact["artifact_id"] for artifact in source_artifacts],
            ["source:patagonia-careers-live", "source:demo-client-careers-live"],
        )
        self.assertEqual(
            [artifact["entity_id"] for artifact in source_artifacts],
            ["competitor-patagonia", "client-demo"],
        )
        self.assertEqual(
            [excerpt["artifact_id"] for excerpt in capture_pack["excerpts"]],
            ["source:patagonia-careers-live", "source:demo-client-careers-live"],
        )

    def test_capture_pack_from_url_stage_manifests_infers_neutral_entity_ids(self) -> None:
        capture_pack = capture_pack_from_url_stage_manifests(
            [self.url_stage_manifest("patagonia-careers-live", "https://www.patagonia.com/jobs/")]
        )

        self.assertEqual(capture_pack["source_artifacts"][0]["entity_id"], "source-patagonia")

    def test_source_roster_from_capture_pack_uses_imported_entities_and_urls(self) -> None:
        capture_pack = capture_pack_from_url_stage_manifests(
            [
                self.url_stage_manifest("patagonia-careers-live", "https://www.patagonia.com/jobs/"),
                self.url_stage_manifest("demo-client-careers-live", "https://demo-client.example/careers"),
            ],
            entity_ids=["competitor-patagonia", "client-demo"],
        )

        roster = source_roster_from_capture_pack(capture_pack)

        self.assertEqual(
            [entity["entity_id"] for entity in roster["entities"]],
            ["competitor-patagonia", "client-demo"],
        )
        self.assertEqual(
            [entity["role"] for entity in roster["entities"]],
            ["competitor", "client"],
        )
        self.assertEqual(roster["entities"][0]["name"], "Patagonia")
        self.assertEqual(
            roster["entities"][0]["source_urls"]["careers_url"],
            "https://www.patagonia.com/jobs/",
        )
        self.assertEqual(
            roster["entities"][1]["source_urls"]["careers_url"],
            "https://demo-client.example/careers",
        )

    def test_generated_fixture_can_ingest_url_stage_manifest(self) -> None:
        url_stage_manifest = {
            "schema_version": "url_stage_capture.v0",
            "slug": "patagonia-careers-live",
            "url": "https://www.patagonia.com/jobs/",
            "captured_at": "2026-06-18T12:00:00Z",
            "artifacts": {
                "visible_text": "artifacts/url-stage/patagonia-careers-live/latest/visible-text.txt",
                "web_snapshot_data": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
                "page_screenshot": "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png",
            },
        }

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            stage_path = Path(tmp) / "url-stage-manifest.json"
            stage_path.write_text(json.dumps(url_stage_manifest), encoding="utf-8")
            manifest_path = generate_publication_pipeline_fixture(
                Path(tmp) / "publication-pipeline",
                url_stage_manifest_path=stage_path,
            )
            capture_pack = json.loads((manifest_path.parent / "capture-pack.json").read_text())
            evidence_matrix = json.loads((manifest_path.parent / "evidence-matrix.json").read_text())

        self.assertEqual(capture_pack["source_artifacts"][0]["artifact_id"], "source:patagonia-careers-live")
        self.assertEqual(
            capture_pack["source_artifacts"][0]["snapshot_path"],
            "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
        )
        self.assertEqual(evidence_matrix["evidence_items"][0]["artifact_id"], "source:patagonia-careers-live")

    def test_generated_fixture_can_ingest_multiple_url_stage_manifests(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            patagonia_path = root / "patagonia-manifest.json"
            demo_path = root / "demo-client-manifest.json"
            patagonia_path.write_text(
                json.dumps(self.url_stage_manifest("patagonia-careers-live", "https://www.patagonia.com/jobs/")),
                encoding="utf-8",
            )
            demo_path.write_text(
                json.dumps(self.url_stage_manifest("demo-client-careers-live", "https://demo-client.example/careers")),
                encoding="utf-8",
            )

            manifest_path = generate_publication_pipeline_fixture(
                root / "publication-pipeline",
                url_stage_manifest_paths=[patagonia_path, demo_path],
                url_stage_entity_ids=["competitor-patagonia", "client-demo"],
            )
            capture_pack = json.loads((manifest_path.parent / "capture-pack.json").read_text(encoding="utf-8"))
            source_roster = json.loads((manifest_path.parent / "source-roster.json").read_text(encoding="utf-8"))
            evidence_matrix = json.loads((manifest_path.parent / "evidence-matrix.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [artifact["artifact_id"] for artifact in capture_pack["source_artifacts"]],
            ["source:patagonia-careers-live", "source:demo-client-careers-live"],
        )
        self.assertEqual(
            [item["entity_id"] for item in evidence_matrix["evidence_items"]],
            ["competitor-patagonia", "client-demo"],
        )
        self.assertEqual(
            [item["artifact_id"] for item in evidence_matrix["evidence_items"]],
            ["source:patagonia-careers-live", "source:demo-client-careers-live"],
        )
        self.assertEqual(
            [entity["entity_id"] for entity in source_roster["entities"]],
            ["competitor-patagonia", "client-demo"],
        )
        self.assertEqual(
            [entity["source_urls"]["careers_url"] for entity in source_roster["entities"]],
            ["https://www.patagonia.com/jobs/", "https://demo-client.example/careers"],
        )

    def test_publication_fixture_cli_accepts_url_stage_manifest(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            stage_path = root / "url-stage-manifest.json"
            stage_path.write_text(
                json.dumps(
                    {
                        "schema_version": "url_stage_capture.v0",
                        "slug": "patagonia-careers-live",
                        "url": "https://www.patagonia.com/jobs/",
                        "captured_at": "2026-06-18T12:00:00Z",
                        "artifacts": {
                            "web_snapshot_data": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
                            "page_screenshot": "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png",
                        },
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "publication-pipeline"

            result = subprocess.run(
                [
                    "python3",
                    "scripts/publication_pipeline_fixture.py",
                    "--output-dir",
                    str(output_dir),
                    "--url-stage-manifest",
                    str(stage_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "passed")
            capture_pack = json.loads((output_dir / "capture-pack.json").read_text(encoding="utf-8"))

        self.assertEqual(capture_pack["source_artifacts"][0]["artifact_id"], "source:patagonia-careers-live")

    def test_publication_fixture_cli_accepts_repeated_url_stage_manifests_and_entity_ids(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            patagonia_path = root / "patagonia-manifest.json"
            demo_path = root / "demo-client-manifest.json"
            patagonia_path.write_text(
                json.dumps(self.url_stage_manifest("patagonia-careers-live", "https://www.patagonia.com/jobs/")),
                encoding="utf-8",
            )
            demo_path.write_text(
                json.dumps(self.url_stage_manifest("demo-client-careers-live", "https://demo-client.example/careers")),
                encoding="utf-8",
            )
            output_dir = root / "publication-pipeline"

            result = subprocess.run(
                [
                    "python3",
                    "scripts/publication_pipeline_fixture.py",
                    "--output-dir",
                    str(output_dir),
                    "--url-stage-manifest",
                    str(patagonia_path),
                    "--url-stage-entity-id",
                    "competitor-patagonia",
                    "--url-stage-manifest",
                    str(demo_path),
                    "--url-stage-entity-id",
                    "client-demo",
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            capture_pack = json.loads((output_dir / "capture-pack.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["url_stage_manifests"], [str(patagonia_path), str(demo_path)])
        self.assertEqual(
            [artifact["entity_id"] for artifact in capture_pack["source_artifacts"]],
            ["competitor-patagonia", "client-demo"],
        )


if __name__ == "__main__":
    unittest.main()
