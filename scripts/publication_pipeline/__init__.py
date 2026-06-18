from __future__ import annotations

from .base_evp import (
    PIPELINE_TEMPLATE_ID,
    generate_publication_pipeline_fixture,
    main,
)
from .campaign_desk_research import CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID, generate_campaign_desk_research_fixture
from .competitor_workbook import COMPETITOR_WORKBOOK_TEMPLATE_ID, generate_competitor_messaging_workbook_fixture
from .core import (
    DEFAULT_OUTPUT_DIR,
    REPO_ROOT,
    capture_pack_from_url_stage_manifest,
    capture_pack_from_url_stage_manifests,
    evidence_items_from_capture_pack,
    load_kilos_terms,
    load_project_profile,
    source_artifacts_from_url_stage_manifest,
    source_roster_from_capture_pack,
)
from .dei_competitor_audit import DEI_COMPETITOR_AUDIT_TEMPLATE_ID, generate_dei_competitor_audit_fixture
from .kilos_methodology import KILOS_METHODOLOGY_TEMPLATE_ID, generate_kilos_methodology_fixture
from .segment_tvp import SEGMENT_TVP_TEMPLATE_ID, generate_segment_tvp_audit_fixture

__all__ = [
    "CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID",
    "COMPETITOR_WORKBOOK_TEMPLATE_ID",
    "DEFAULT_OUTPUT_DIR",
    "DEI_COMPETITOR_AUDIT_TEMPLATE_ID",
    "KILOS_METHODOLOGY_TEMPLATE_ID",
    "PIPELINE_TEMPLATE_ID",
    "REPO_ROOT",
    "SEGMENT_TVP_TEMPLATE_ID",
    "capture_pack_from_url_stage_manifest",
    "capture_pack_from_url_stage_manifests",
    "evidence_items_from_capture_pack",
    "generate_campaign_desk_research_fixture",
    "generate_competitor_messaging_workbook_fixture",
    "generate_dei_competitor_audit_fixture",
    "generate_kilos_methodology_fixture",
    "generate_publication_pipeline_fixture",
    "generate_segment_tvp_audit_fixture",
    "load_kilos_terms",
    "load_project_profile",
    "main",
    "source_artifacts_from_url_stage_manifest",
    "source_roster_from_capture_pack",
]
