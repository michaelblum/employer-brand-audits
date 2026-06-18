from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    COMPETITOR_WORKBOOK_TEMPLATE_ID,
    generate_competitor_messaging_workbook_fixture,
)
from scripts.workbench_projection import project_audit_manifest


HARBOURVEST_WORKBOOK = REPO_ROOT / "reference_publications" / "Reference" / "HarbourVest Partners - Competitor messaging samples.xlsx"


class CompetitorWorkbookPipelineTests(unittest.TestCase):
    def arbitrary_profile(self) -> dict[str, object]:
        return {
            "project_id": "summit-partners-workbook",
            "client_name": "Summit Partners",
            "client_full_name": "Summit Partners",
            "industry": "Investment management",
            "geography": "United States",
            "audience": "Investment and operations talent",
            "domain": "summitpartners.example",
            "competitors": [
                {"entity_id": "competitor-ridge", "name": "Ridge Capital", "careers_url": "https://ridge.example/careers"},
                {"entity_id": "competitor-cascade", "name": "Cascade Equity", "careers_url": "https://cascade.example/careers"},
            ],
        }

    @unittest.skipUnless(HARBOURVEST_WORKBOOK.exists(), "local HarbourVest workbook is not tracked")
    def test_local_harbourvest_workbook_is_readable_when_present(self) -> None:
        try:
            import openpyxl
        except ImportError as exc:
            self.skipTest(f"openpyxl unavailable: {exc}")

        workbook = openpyxl.load_workbook(HARBOURVEST_WORKBOOK, data_only=False, read_only=True)

        self.assertEqual(workbook.sheetnames, ["Messaging audit", "Partner orgs", "notes"])
        self.assertEqual(workbook["Messaging audit"].calculate_dimension(force=True), "A1:Z1017")
        self.assertEqual(workbook["Partner orgs"].calculate_dimension(force=True), "A1:Z1001")
        self.assertEqual(workbook["notes"].calculate_dimension(force=True), "A1:A12")

    def test_workbook_fixture_writes_manifest_and_required_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_competitor_messaging_workbook_fixture(Path(tmp) / "workbook")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            required_files = [
                "pipeline-intake.json",
                "source-roster.json",
                "workbook-extraction.json",
                "evidence-matrix.json",
                "analysis-pack.json",
                "data-workbook-view.html",
                "l4-publication.html",
            ]
            for relative_path in required_files:
                self.assertTrue((manifest_path.parent / relative_path).exists(), relative_path)

        self.assertEqual(manifest["template_id"], COMPETITOR_WORKBOOK_TEMPLATE_ID)
        self.assertNotIn("reference_publications", json.dumps(manifest))
        self.assertEqual(
            [step["id"] for step in manifest["steps"]],
            [
                "p0-pipeline-intake",
                "p0-source-roster",
                "p1-workbook-extraction",
                "p2-evidence-matrix",
                "p3-analysis-pack",
                "p4-data-workbook-view",
                "p4-l4-publication-view",
            ],
        )

    def test_workbook_fixture_normalizes_matrix_and_partner_records(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_competitor_messaging_workbook_fixture(Path(tmp) / "workbook")
            root = manifest_path.parent
            roster = json.loads((root / "source-roster.json").read_text(encoding="utf-8"))
            extraction = json.loads((root / "workbook-extraction.json").read_text(encoding="utf-8"))
            matrix = json.loads((root / "evidence-matrix.json").read_text(encoding="utf-8"))
            analysis = json.loads((root / "analysis-pack.json").read_text(encoding="utf-8"))

        self.assertEqual(len(roster["entities"]), 8)
        self.assertEqual(extraction["sheets"]["Messaging audit"]["dimension"], "A1:Z1017")
        self.assertEqual(extraction["sheets"]["Messaging audit"]["effective_range"], "A1:L135")
        self.assertEqual(extraction["sheets"]["Messaging audit"]["non_empty_cells"], 405)
        self.assertEqual(extraction["sheets"]["Messaging audit"]["formula_cells"], 52)
        self.assertEqual(len(matrix["wide_matrix_cells"]), 568)
        self.assertEqual(len(matrix["evidence_items"]), 128)
        self.assertEqual(len(matrix["partner_orgs"]), 30)
        self.assertEqual(len(matrix["partner_activations"]), 57)
        self.assertTrue(all(item["source_cell"] for item in matrix["evidence_items"]))
        self.assertTrue(all(item["source_cell"] for item in matrix["partner_activations"]))
        evidence_ids = {item["evidence_id"] for item in matrix["evidence_items"]}
        for finding in analysis["findings"]:
            self.assertTrue(set(finding["supporting_evidence_ids"]).issubset(evidence_ids), finding)

    def test_workbook_projection_groups_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_competitor_messaging_workbook_fixture(Path(tmp) / "workbook")
            projection = project_audit_manifest(manifest_path)

        group_slots = {group["slot"] for group in projection["artifact_groups"]}
        self.assertIn("publication.data_workbook.bundle", group_slots)
        self.assertIn("publication.l4_publication.bundle", group_slots)

    def test_arbitrary_workbook_profile_does_not_leak_reference_labels(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "summit-profile.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")
            manifest_path = generate_competitor_messaging_workbook_fixture(
                root / "workbook",
                project_profile_path=profile_path,
            )
            generated_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(manifest_path.parent.glob("*"))
                if path.is_file() and path.suffix in {".json", ".html"}
            )

        self.assertIn("Summit Partners", generated_text)
        for label in [
            "HarbourVest",
            "HarbourVest Partners",
            "harbourvest.com",
            "Adams Street Partners",
            "Bain Capital",
            "Blackstone",
            "Carlyle Group",
            "GCM Grosvenor",
            "Hamilton Lane",
            "Stepstone Group",
            "Level20",
            "GAIN Girls are Investors",
        ]:
            self.assertNotIn(label, generated_text)

    def test_workbook_fixture_is_registered_in_command_surface(self) -> None:
        from scripts.eba_cli import FIXTURE_GENERATORS, demo_recipe_lines, validation_commands

        self.assertIn("competitor-messaging-workbook", FIXTURE_GENERATORS)
        self.assertTrue(
            any(command[-1] == "tests/test_publication_competitor_workbook.py" for command in validation_commands())
        )
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(json.dumps({"template_id": COMPETITOR_WORKBOOK_TEMPLATE_ID}), encoding="utf-8")
            lines = demo_recipe_lines(fixture=None, manifest=manifest)

        self.assertIn("Workbook Extraction", "\n".join(lines))
        self.assertIn("Partner Activation", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
