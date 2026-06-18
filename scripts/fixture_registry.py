"""Fixture generator registry for the project command surface."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

try:
    from scripts.easy_audit_fixture import generate_easy_audit_fixture
    from scripts.publication_pipeline import (
        generate_campaign_desk_research_fixture,
        generate_competitor_messaging_workbook_fixture,
        generate_dei_competitor_audit_fixture,
        generate_kilos_methodology_fixture,
        generate_publication_pipeline_fixture,
        generate_segment_tvp_audit_fixture,
    )
except ModuleNotFoundError:
    from easy_audit_fixture import generate_easy_audit_fixture
    from publication_pipeline import (
        generate_campaign_desk_research_fixture,
        generate_competitor_messaging_workbook_fixture,
        generate_dei_competitor_audit_fixture,
        generate_kilos_methodology_fixture,
        generate_publication_pipeline_fixture,
        generate_segment_tvp_audit_fixture,
    )


FixtureGenerator = Callable[[], Path]

FIXTURE_GENERATORS: dict[str, FixtureGenerator] = {
    "easy-audit": generate_easy_audit_fixture,
    "publication-pipeline": generate_publication_pipeline_fixture,
    "segment-tvp-audit": generate_segment_tvp_audit_fixture,
    "competitor-messaging-workbook": generate_competitor_messaging_workbook_fixture,
    "dei-competitor-audit": generate_dei_competitor_audit_fixture,
    "campaign-desk-research-comp-audit": generate_campaign_desk_research_fixture,
    "kilos-methodology": generate_kilos_methodology_fixture,
}
