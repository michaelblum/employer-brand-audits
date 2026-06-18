from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID,
    generate_campaign_desk_research_fixture,
)
from scripts.publication_pipeline.core import slugify
from scripts.workbench_projection import project_audit_manifest


SCOTTISH_POWER_DECK = REPO_ROOT / "reference_publications" / "Reference" / "Scottish Power DEI Campaign - Desk Research Report & Comp Audit.pptx"


class CampaignDeskResearchPipelineTests(unittest.TestCase):
    def arbitrary_profile(self) -> dict[str, object]:
        return {
            "project_id": "green-grid-women-engineering",
            "client_name": "Green Grid",
            "client_full_name": "Green Grid",
            "industry": "Energy infrastructure",
            "geography": "United Kingdom",
            "audience": "Women in engineering",
            "domain": "greengrid.example",
            "campaign_goal": "Increase applications from women engineers",
            "target_population": "Women in engineering and field operations",
        }

    @unittest.skipUnless(SCOTTISH_POWER_DECK.exists(), "local Scottish Power deck is not tracked")
    def test_local_scottish_power_deck_is_readable_when_present(self) -> None:
        try:
            from pptx import Presentation
        except ImportError as exc:
            self.skipTest(f"python-pptx unavailable: {exc}")

        deck = Presentation(SCOTTISH_POWER_DECK)

        self.assertEqual(len(deck.slides), 49)

    def test_campaign_fixture_writes_manifest_and_required_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_campaign_desk_research_fixture(Path(tmp) / "campaign")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for relative_path in [
                "pipeline-intake.json",
                "research-source-roster.json",
                "desk-research-evidence-pack.json",
                "campaign-case-matrix.json",
                "channel-tactic-opportunity-map.json",
                "campaign-lessons-analysis-pack.json",
                "campaign-recommendation-readout.html",
                "l4-publication.html",
            ]:
                self.assertTrue((manifest_path.parent / relative_path).exists(), relative_path)

        self.assertEqual(manifest["template_id"], CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID)
        self.assertNotIn("reference_publications", json.dumps(manifest))
        self.assertEqual(
            [step["id"] for step in manifest["steps"]],
            [
                "p0-pipeline-intake",
                "p0-research-source-roster",
                "p1-desk-research-evidence-pack",
                "p2-campaign-case-matrix",
                "p2-channel-tactic-opportunity-map",
                "p3-campaign-lessons-analysis-pack",
                "p4-campaign-recommendation-readout",
                "p4-l4-publication-view",
            ],
        )

    def test_campaign_fixture_models_sources_cases_tactics_and_recommendations(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_campaign_desk_research_fixture(Path(tmp) / "campaign")
            root = manifest_path.parent
            sources = json.loads((root / "research-source-roster.json").read_text(encoding="utf-8"))
            evidence = json.loads((root / "desk-research-evidence-pack.json").read_text(encoding="utf-8"))
            cases = json.loads((root / "campaign-case-matrix.json").read_text(encoding="utf-8"))
            tactics = json.loads((root / "channel-tactic-opportunity-map.json").read_text(encoding="utf-8"))
            analysis = json.loads((root / "campaign-lessons-analysis-pack.json").read_text(encoding="utf-8"))

        self.assertEqual(evidence["slide_count"], 49)
        self.assertGreaterEqual(len(sources["desk_research_sources"]), 15)
        self.assertEqual(sources["source_group_counts"], {"global_uk_gender": 7, "energy_engineering": 4, "dei_practice": 4})
        self.assertEqual(len(cases["campaign_case_studies"]), 12)
        self.assertGreaterEqual(len(tactics["channel_tactics"]), 12)
        stat_ids = {item["stat_id"] for item in evidence["labor_market_stats"]}
        signal_ids = {item["signal_id"] for item in evidence["policy_or_context_signals"]}
        case_ids = {item["case_id"] for item in cases["campaign_case_studies"]}
        tactic_ids = {item["tactic_id"] for item in tactics["channel_tactics"]}
        for recommendation in analysis["campaign_recommendations"]:
            self.assertTrue(set(recommendation["supporting_stat_or_signal_ids"]) & (stat_ids | signal_ids), recommendation)
            self.assertTrue(set(recommendation["supporting_case_ids"]).issubset(case_ids), recommendation)
            self.assertTrue(set(recommendation["supporting_tactic_ids"]).issubset(tactic_ids), recommendation)

    def test_campaign_default_cases_and_tactics_derive_from_sample_profile_cases(self) -> None:
        profile_path = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-campaign-desk-research.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile_cases = profile.get("campaign_case_studies")
        self.assertIsInstance(profile_cases, list)
        self.assertGreaterEqual(len(profile_cases), 12)
        expected_case_ids = {
            str(case.get("case_id") or f"case:{slugify(str(case.get('organization') or 'case'))}")
            for case in profile_cases
            if isinstance(case, dict)
        }

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_campaign_desk_research_fixture(Path(tmp) / "campaign")
            cases = json.loads((manifest_path.parent / "campaign-case-matrix.json").read_text(encoding="utf-8"))
            tactics = json.loads((manifest_path.parent / "channel-tactic-opportunity-map.json").read_text(encoding="utf-8"))

        generated_case_ids = {case["case_id"] for case in cases["campaign_case_studies"]}
        tactic_case_ids = {
            case_id
            for tactic in tactics["channel_tactics"]
            for case_id in tactic["case_ids"]
        }
        self.assertEqual(generated_case_ids, expected_case_ids)
        self.assertLessEqual(tactic_case_ids, expected_case_ids)

    def test_campaign_projection_groups_l4_view(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_campaign_desk_research_fixture(Path(tmp) / "campaign")
            projection = project_audit_manifest(manifest_path)

        self.assertIn("publication.l4_publication.bundle", {group["slot"] for group in projection["artifact_groups"]})

    def test_arbitrary_campaign_profile_does_not_leak_reference_labels(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            profile_path = root / "green-grid.json"
            profile_path.write_text(json.dumps(self.arbitrary_profile()), encoding="utf-8")
            manifest_path = generate_campaign_desk_research_fixture(root / "campaign", project_profile_path=profile_path)
            generated_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(manifest_path.parent.glob("*"))
                if path.is_file() and path.suffix in {".json", ".html"}
            )

        self.assertIn("Green Grid", generated_text)
        for label in [
            "Scottish Power",
            "ScottishPower",
            "SP Energy Networks",
            "Iberdrola",
            "HerEnergy",
            "Strategies 4 Success",
            "Symphony Talent",
        ]:
            self.assertNotIn(label, generated_text)

    def test_campaign_fixture_is_registered_in_command_surface(self) -> None:
        from scripts.eba_cli import FIXTURE_GENERATORS, demo_recipe_lines, validation_commands

        self.assertIn("campaign-desk-research-comp-audit", FIXTURE_GENERATORS)
        self.assertTrue(
            any(command[-1] == "tests/test_publication_campaign_desk_research.py" for command in validation_commands())
        )
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(json.dumps({"template_id": CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID}), encoding="utf-8")
            lines = demo_recipe_lines(fixture=None, manifest=manifest)

        self.assertIn("Campaign Case Matrix", "\n".join(lines))
        self.assertIn("Channel Tactic", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
