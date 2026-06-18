from __future__ import annotations

import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.publication_pipeline_fixture import (
    generate_campaign_desk_research_fixture,
    generate_competitor_messaging_workbook_fixture,
    generate_dei_competitor_audit_fixture,
    generate_publication_pipeline_fixture,
    generate_segment_tvp_audit_fixture,
)


REFERENCE_LABELS = [
    "Northside",
    "Wellstar",
    "Emory Healthcare",
    "Northeast Georgia",
    "ADT",
    "jobs.adt.com",
    "Vivint",
    "SimpliSafe",
    "Arlo",
    "Verisure",
    "Alarm.com",
    "Resideo",
    "Fortune Brands",
    "Motorola Solutions",
    "HarbourVest",
    "Harbourvest",
    "harbourvest.com",
    "Adams Street",
    "Bain Capital",
    "Blackstone",
    "Carlyle",
    "GCM Grosvenor",
    "Hamilton Lane",
    "Stepstone",
    "StepStone",
    "Level20",
    "GAIN Girls are Investors",
    "Scottish Power",
    "ScottishPower",
    "SP Energy Networks",
    "Iberdrola",
    "HerEnergy",
    "Strategies 4 Success",
    "Symphony Talent",
]


class PublicationDefaultSampleTests(unittest.TestCase):
    def generated_text(self, fixture_name: str, generator: Callable[[Path], Path]) -> str:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generator(Path(tmp) / fixture_name)
            return "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(manifest_path.parent.glob("*"))
                if path.is_file() and path.suffix in {".json", ".html"}
            )

    def assert_default_output_uses_only_sample_labels(self, fixture_name: str, generator: Callable[[Path], Path]) -> None:
        generated_text = self.generated_text(fixture_name, generator)
        for label in REFERENCE_LABELS:
            self.assertNotIn(label, generated_text, f"{fixture_name} leaked {label!r}")

    def test_base_publication_default_output_uses_sample_profile(self) -> None:
        self.assert_default_output_uses_only_sample_labels(
            "publication-pipeline",
            generate_publication_pipeline_fixture,
        )

    def test_segment_tvp_default_output_uses_sample_profile(self) -> None:
        self.assert_default_output_uses_only_sample_labels(
            "segment-tvp-audit",
            generate_segment_tvp_audit_fixture,
        )

    def test_competitor_workbook_default_output_uses_sample_profile(self) -> None:
        self.assert_default_output_uses_only_sample_labels(
            "competitor-messaging-workbook",
            generate_competitor_messaging_workbook_fixture,
        )

    def test_dei_competitor_audit_default_output_uses_sample_profile(self) -> None:
        self.assert_default_output_uses_only_sample_labels(
            "dei-competitor-audit",
            generate_dei_competitor_audit_fixture,
        )

    def test_campaign_desk_research_default_output_uses_sample_profile(self) -> None:
        self.assert_default_output_uses_only_sample_labels(
            "campaign-desk-research-comp-audit",
            generate_campaign_desk_research_fixture,
        )


if __name__ == "__main__":
    unittest.main()
