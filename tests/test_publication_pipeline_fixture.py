from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    PIPELINE_TEMPLATE_ID,
    generate_publication_pipeline_fixture,
    load_kilos_terms,
    load_project_profile,
)
from scripts.workbench_projection import project_audit_manifest


class PublicationPipelineFixtureTests(unittest.TestCase):
    def arbitrary_profile(self) -> dict[str, object]:
        return {
            "project_id": "acme-care-reference-prototype",
            "client_name": "Acme Care",
            "industry": "Healthcare",
            "geography": "United States",
            "audience": "Clinical and technical talent",
            "report_title": "Acme Care EVP Client Data Immersion and Competitor Messaging Audit",
            "report_date": "2026-06-18",
            "domain": "acmecare.example",
            "competitors": [
                {
                    "entity_id": "competitor-bright-clinic",
                    "name": "Bright Clinic",
                    "careers_url": "https://bright.example/careers",
                },
                {
                    "entity_id": "competitor-apex-health",
                    "name": "Apex Health",
                    "careers_url": "https://apex.example/careers",
                },
                {
                    "entity_id": "competitor-beacon-medical",
                    "name": "Beacon Medical",
                    "careers_url": "https://beacon.example/careers",
                },
            ],
            "client_signals": {
                "mission": "Acme Care helps communities get timely, compassionate care close to home.",
                "values": ["Compassion", "Access", "Teamwork", "Progress"],
                "flexibility_program": "Acme Flex lets nurses choose preferred sites and schedule patterns.",
                "benefits": ["Paid family support", "Wellbeing stipends", "Tuition support"],
                "awards": ["Regional care quality leader 2026"],
            },
        }

    def test_load_kilos_terms_uses_tracked_data(self) -> None:
        terms = load_kilos_terms(REPO_ROOT / "data" / "kilos-framework.json")

        self.assertEqual(len(terms), 29)
        self.assertEqual(terms[0]["framework_id"], "KILOS")
        self.assertEqual(terms[0]["pillar_id"], "K")
        self.assertEqual(terms[0]["factor_id"], "K1")
        self.assertIn("pillar_color", terms[0])

    def test_fixture_writes_full_publication_manifest(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["schema_version"], "adr-002.audit-manifest.v1")
        self.assertEqual(manifest["template_id"], PIPELINE_TEMPLATE_ID)
        self.assertEqual(manifest["framework_id"], "KILOS")
        self.assertEqual(manifest["framework_version"], "1.0")
        self.assertNotIn("reference_publications", json.dumps(manifest))
        self.assertEqual(
            [step["id"] for step in manifest["steps"]],
            [
                "p0-pipeline-intake",
                "p0-project-frame",
                "p0-source-roster",
                "p1-capture-pack",
                "p2-evidence-matrix",
                "p3-analysis-pack",
                "p4-report-docx-view",
                "p4-audit-deck-view",
                "p4-data-workbook-view",
                "p4-l4-publication-view",
            ],
        )

    def test_fixture_preserves_evidence_lineage_to_publication_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            root = manifest_path.parent
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            required_files = [
                "pipeline-intake.json",
                "project-frame.json",
                "source-roster.json",
                "capture-pack.json",
                "evidence-matrix.json",
                "analysis-pack.json",
                "report-docx-view.html",
                "audit-deck-view.html",
                "data-workbook-view.html",
                "l4-publication.html",
            ]
            for relative_path in required_files:
                self.assertTrue((root / relative_path).exists(), relative_path)

        artifacts_by_id = {artifact["id"]: artifact for artifact in manifest["artifacts"]}
        self.assertEqual(
            artifacts_by_id["p0-project-frame"]["parent_ids"],
            ["p0-pipeline-intake"],
        )
        self.assertEqual(
            artifacts_by_id["p4-l4-publication"]["parent_ids"],
            ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"],
        )

    def test_fixture_writes_pipeline_intake_contract(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            intake = json.loads((manifest_path.parent / "pipeline-intake.json").read_text(encoding="utf-8"))

        self.assertEqual(intake["pipeline_id"], PIPELINE_TEMPLATE_ID)
        self.assertEqual(intake["client"]["name"], "Northside Hospital")
        self.assertEqual(intake["ontology"]["framework_id"], "KILOS")
        self.assertIn("report_docx", intake["desired_outputs"])
        self.assertIn("l4_publication", intake["desired_outputs"])
        self.assertGreaterEqual(len(intake["competitors"]), 3)
        self.assertTrue(intake["review_requirements"]["manual_review_gates"])

    def test_default_fixture_contains_reference_report_data_groups(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            root = manifest_path.parent
            project_frame = json.loads((root / "project-frame.json").read_text(encoding="utf-8"))
            roster = json.loads((root / "source-roster.json").read_text(encoding="utf-8"))
            capture_pack = json.loads((root / "capture-pack.json").read_text(encoding="utf-8"))
            evidence_matrix = json.loads((root / "evidence-matrix.json").read_text(encoding="utf-8"))
            analysis_pack = json.loads((root / "analysis-pack.json").read_text(encoding="utf-8"))

        section_ids = [section["section_id"] for section in project_frame["report_outline"]["sections"]]
        self.assertEqual(section_ids[0:4], [
            "introduction",
            "research_methodology",
            "client_data_immersion",
            "competitor_messaging_audit",
        ])
        self.assertIn("careers_messaging_samples", section_ids)
        self.assertIn("glassdoor_snapshot", section_ids)
        self.assertIn("indeed_snapshot", section_ids)

        self.assertEqual(
            [entity["name"] for entity in roster["entities"]],
            [
                "Northside Hospital",
                "Wellstar Health System",
                "Emory Healthcare",
                "Northeast Georgia Health System",
            ],
        )
        self.assertGreaterEqual(len(capture_pack["source_artifacts"]), 12)
        self.assertGreaterEqual(len(capture_pack["excerpts"]), 40)
        self.assertGreaterEqual(len(evidence_matrix["evidence_items"]), 40)
        self.assertGreaterEqual(len(evidence_matrix["survey_signals"]), 8)
        self.assertGreaterEqual(len(evidence_matrix["review_snapshots"]), 8)
        self.assertGreaterEqual(len(analysis_pack["positioning_summaries"]), 4)
        self.assertGreaterEqual(len(analysis_pack["market_trends"]), 4)
        self.assertGreaterEqual(len(analysis_pack["strengths"]), 4)
        self.assertGreaterEqual(len(analysis_pack["opportunities"]), 3)
        self.assertGreaterEqual(len(analysis_pack["risks"]), 3)

        evidence_ids = {item["evidence_id"] for item in evidence_matrix["evidence_items"]}
        for finding in analysis_pack["findings"]:
            self.assertTrue(finding["supporting_evidence_ids"], finding)
            self.assertTrue(set(finding["supporting_evidence_ids"]).issubset(evidence_ids), finding)

    def test_profile_driven_fixture_recreates_report_shape_for_arbitrary_company(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "acme-profile.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")

            manifest_path = generate_publication_pipeline_fixture(
                root / "publication-pipeline",
                project_profile_path=profile_path,
            )
            output_root = manifest_path.parent
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            project_frame = json.loads((output_root / "project-frame.json").read_text(encoding="utf-8"))
            roster = json.loads((output_root / "source-roster.json").read_text(encoding="utf-8"))
            evidence_matrix = json.loads((output_root / "evidence-matrix.json").read_text(encoding="utf-8"))
            analysis_pack = json.loads((output_root / "analysis-pack.json").read_text(encoding="utf-8"))
            report_html = (output_root / "report-docx-view.html").read_text(encoding="utf-8")

        self.assertEqual(manifest["company"], "Acme Care")
        self.assertEqual(project_frame["client_name"], "Acme Care")
        self.assertEqual(roster["entities"][0]["name"], "Acme Care")
        self.assertEqual(
            [entity["name"] for entity in roster["entities"][1:]],
            ["Bright Clinic", "Apex Health", "Beacon Medical"],
        )
        self.assertIn("Acme Care", report_html)
        self.assertIn("Client Data Immersion", report_html)
        self.assertIn("Competitor Messaging Audit", report_html)
        self.assertNotIn("Northside Hospital", json.dumps(project_frame))
        self.assertNotIn("Northside Hospital", report_html)
        self.assertGreaterEqual(len(evidence_matrix["evidence_items"]), 40)
        self.assertGreaterEqual(len(analysis_pack["findings"]), 14)

    def test_project_profile_loader_does_not_merge_reference_profile_defaults(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            profile_path = Path(tmp) / "minimal-profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "project_id": "minimal-client-audit",
                        "client_name": "Minimal Client",
                    }
                ),
                encoding="utf-8",
            )

            profile = load_project_profile(profile_path)

        self.assertEqual(profile["client_name"], "Minimal Client")
        self.assertNotIn("Northside", json.dumps(profile))
        self.assertEqual(profile.get("competitors"), [])

    def test_arbitrary_profile_outputs_are_free_of_reference_profile_labels(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "acme-profile.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")

            manifest_path = generate_publication_pipeline_fixture(
                root / "publication-pipeline",
                project_profile_path=profile_path,
            )

            generated_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(manifest_path.parent.glob("*"))
                if path.is_file() and path.suffix in {".json", ".html"}
            )

        self.assertNotIn("Northside", generated_text)
        self.assertNotIn("northside", generated_text)
        self.assertNotIn("ADT-style", generated_text)
        self.assertNotIn("HarbourVest-style", generated_text)

    def test_projection_groups_publication_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            projection = project_audit_manifest(manifest_path)

        group_slots = [group["slot"] for group in projection["artifact_groups"]]
        self.assertIn("publication.report_docx.bundle", group_slots)
        self.assertIn("publication.audit_deck.bundle", group_slots)
        self.assertIn("publication.data_workbook.bundle", group_slots)
        self.assertIn("publication.l4_publication.bundle", group_slots)
        l4_group = next(group for group in projection["artifact_groups"] if group["slot"] == "publication.l4_publication.bundle")
        self.assertIn("p0-pipeline-intake", l4_group["artifact_ids"])

    def test_publication_pipeline_fixture_is_registered_in_command_surface(self) -> None:
        from scripts.eba_cli import FIXTURE_GENERATORS, validation_commands

        self.assertIn("publication-pipeline", FIXTURE_GENERATORS)
        compile_command = validation_commands()[0]
        self.assertIn("scripts/publication_pipeline_fixture.py", compile_command)
        self.assertTrue(
            any(command[-1] == "tests/test_publication_pipeline_fixture.py" for command in validation_commands())
        )
        self.assertTrue(
            any(command[-1] == "tests/test_publication_capture_pack.py" for command in validation_commands())
        )

    def test_publication_pipeline_demo_recipe_is_specific(self) -> None:
        from scripts.eba_cli import demo_recipe_lines

        lines = demo_recipe_lines(
            fixture="publication-pipeline",
            manifest=REPO_ROOT / "artifacts" / "publication-pipeline" / "latest" / "manifest.json",
        )

        self.assertIn("Evidence Matrix", "\n".join(lines))
        self.assertIn("pipeline intake", "\n".join(lines))
        self.assertIn("L4 Publication", "\n".join(lines))
        self.assertNotIn("Acme Robotics", "\n".join(lines))

    def test_publication_pipeline_demo_recipe_detects_manifest_shape(self) -> None:
        from scripts.eba_cli import demo_recipe_lines

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(
                json.dumps({"template_id": PIPELINE_TEMPLATE_ID}),
                encoding="utf-8",
            )

            lines = demo_recipe_lines(fixture=None, manifest=manifest)

        self.assertIn("Evidence Matrix", "\n".join(lines))
        self.assertIn("L4 Publication", "\n".join(lines))

    def test_publication_fixture_cli_accepts_project_profile(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "acme-profile.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")
            output_dir = root / "publication-pipeline"

            result = subprocess.run(
                [
                    "python3",
                    "scripts/publication_pipeline_fixture.py",
                    "--output-dir",
                    str(output_dir),
                    "--project-profile",
                    str(profile_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            project_frame = json.loads((output_dir / "project-frame.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["project_profile"], str(profile_path))
        self.assertEqual(project_frame["client_name"], "Acme Care")


if __name__ == "__main__":
    unittest.main()
