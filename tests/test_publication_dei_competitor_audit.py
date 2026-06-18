from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    DEI_COMPETITOR_AUDIT_TEMPLATE_ID,
    generate_dei_competitor_audit_fixture,
)
from scripts.workbench_projection import project_audit_manifest


HARBOURVEST_DECK = REPO_ROOT / "reference_publications" / "Reference" / "HarbourVest Partners - Competitor Audit_.pptx"


class DeiCompetitorAuditPipelineTests(unittest.TestCase):
    def arbitrary_profile(self) -> dict[str, object]:
        return {
            "project_id": "altair-dei-audit",
            "client_name": "Altair Capital",
            "client_full_name": "Altair Capital",
            "industry": "Investment management",
            "geography": "United States",
            "audience": "Investment talent",
            "domain": "altair.example",
            "competitors": [
                {"entity_id": "competitor-north-peak", "name": "North Peak"},
                {"entity_id": "competitor-harborline", "name": "Harborline Equity"},
            ],
        }

    @unittest.skipUnless(HARBOURVEST_DECK.exists(), "local HarbourVest DEI deck is not tracked")
    def test_local_harbourvest_dei_deck_is_readable_when_present(self) -> None:
        try:
            from pptx import Presentation
        except ImportError as exc:
            self.skipTest(f"python-pptx unavailable: {exc}")

        deck = Presentation(HARBOURVEST_DECK)

        self.assertEqual(len(deck.slides), 33)

    def test_dei_fixture_writes_manifest_and_required_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_dei_competitor_audit_fixture(Path(tmp) / "dei-audit")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            required_files = [
                "pipeline-intake.json",
                "source-roster.json",
                "deck-extraction.json",
                "evidence-matrix.json",
                "analysis-pack.json",
                "dei-activation-matrix.html",
                "inclusion-philosophy-map.html",
                "partner-landscape.html",
                "competitor-audit-deck-view.html",
                "l4-publication.html",
            ]
            for relative_path in required_files:
                self.assertTrue((manifest_path.parent / relative_path).exists(), relative_path)

        self.assertEqual(manifest["template_id"], DEI_COMPETITOR_AUDIT_TEMPLATE_ID)
        self.assertNotIn("reference_publications", json.dumps(manifest))
        self.assertEqual(
            [step["id"] for step in manifest["steps"]],
            [
                "p0-pipeline-intake",
                "p0-source-roster",
                "p1-deck-extraction",
                "p2-dei-evidence-matrix",
                "p3-dei-analysis-pack",
                "p4-dei-activation-matrix-view",
                "p4-inclusion-philosophy-map-view",
                "p4-partner-landscape-view",
                "p4-competitor-audit-deck-view",
                "p4-l4-publication-view",
            ],
        )

    def test_dei_fixture_models_activations_philosophies_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_dei_competitor_audit_fixture(Path(tmp) / "dei-audit")
            root = manifest_path.parent
            roster = json.loads((root / "source-roster.json").read_text(encoding="utf-8"))
            extraction = json.loads((root / "deck-extraction.json").read_text(encoding="utf-8"))
            matrix = json.loads((root / "evidence-matrix.json").read_text(encoding="utf-8"))
            analysis = json.loads((root / "analysis-pack.json").read_text(encoding="utf-8"))

        self.assertEqual(len(roster["entities"]), 8)
        self.assertEqual(extraction["slide_count"], 33)
        self.assertEqual(set(matrix["inclusion_philosophy_classes"]), {"policy", "company/performance", "culture", "system"})
        self.assertEqual(len(matrix["dei_activations"]), 30)
        self.assertGreaterEqual(len(matrix["coverage_gaps"]), 6)
        self.assertGreaterEqual(len(matrix["benchmark_sources"]), 4)
        evidence_ids = {item["evidence_id"] for item in matrix["evidence_items"]}
        for collection_name in ("dei_activations", "inclusion_philosophies", "coverage_gaps", "benchmark_sources"):
            for record in matrix[collection_name]:
                self.assertTrue(set(record["supporting_evidence_ids"]).issubset(evidence_ids), record)
        for finding in analysis["findings"]:
            self.assertTrue(set(finding["supporting_evidence_ids"]).issubset(evidence_ids), finding)

    def test_dei_projection_groups_deck_and_l4_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_dei_competitor_audit_fixture(Path(tmp) / "dei-audit")
            projection = project_audit_manifest(manifest_path)

        group_slots = {group["slot"] for group in projection["artifact_groups"]}
        self.assertIn("publication.audit_deck.bundle", group_slots)
        self.assertIn("publication.l4_publication.bundle", group_slots)

    def test_arbitrary_dei_profile_does_not_leak_reference_labels(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "altair-profile.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")
            manifest_path = generate_dei_competitor_audit_fixture(
                root / "dei-audit",
                project_profile_path=profile_path,
            )
            generated_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(manifest_path.parent.glob("*"))
                if path.is_file() and path.suffix in {".json", ".html"}
            )

        self.assertIn("Altair Capital", generated_text)
        for label in [
            "HarbourVest",
            "HarbourVest Partners",
            "Adams Street Partners",
            "Bain Capital",
            "Blackstone",
            "Carlyle",
            "GCM Grosvenor",
            "Hamilton Lane",
            "StepStone",
            "Northside",
        ]:
            self.assertNotIn(label, generated_text)

    def test_dei_fixture_is_registered_in_command_surface(self) -> None:
        from scripts.eba_cli import FIXTURE_GENERATORS, demo_recipe_lines, validation_commands

        self.assertIn("dei-competitor-audit", FIXTURE_GENERATORS)
        self.assertTrue(
            any(command[-1] == "tests/test_publication_dei_competitor_audit.py" for command in validation_commands())
        )
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(json.dumps({"template_id": DEI_COMPETITOR_AUDIT_TEMPLATE_ID}), encoding="utf-8")
            lines = demo_recipe_lines(fixture=None, manifest=manifest)

        self.assertIn("DEI Activation Matrix", "\n".join(lines))
        self.assertIn("Inclusion Philosophy", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
