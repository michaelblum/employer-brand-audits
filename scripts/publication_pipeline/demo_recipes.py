from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import (
    CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID,
    COMPETITOR_WORKBOOK_TEMPLATE_ID,
    DEI_COMPETITOR_AUDIT_TEMPLATE_ID,
    KILOS_METHODOLOGY_TEMPLATE_ID,
    REPO_ROOT,
    SEGMENT_TVP_TEMPLATE_ID,
)


def manifest_template_id(manifest: Path) -> str:
    try:
        payload: Any = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("template_id") or "")


def demo_recipe_lines(*, fixture: str | None, manifest: Path) -> list[str]:
    publication_manifest = REPO_ROOT / "artifacts" / "publication-pipeline" / "latest" / "manifest.json"
    publication_template_ids = {
        "publication-pipeline.evp-client-immersion-competitor-audit",
        "publication-pipeline.reference-workflow",
    }
    if (
        fixture == "publication-pipeline"
        or manifest_template_id(manifest) in publication_template_ids
        or manifest.resolve() == publication_manifest.resolve()
    ):
        return [
            "1. Confirm the workflow shows pipeline intake, project frame, capture pack, evidence matrix, analysis pack, and four publication views.",
            "2. Open Evidence Matrix and confirm every KILOS-coded item has pillar/factor provenance.",
            "3. Open Analysis Pack and confirm findings link back to evidence ids.",
            "4. Open L4 Publication and confirm it is a view over the same upstream records, not a separate source.",
        ]
    if fixture == "segment-tvp-audit" or manifest_template_id(manifest) == SEGMENT_TVP_TEMPLATE_ID:
        return [
            "1. Confirm the workflow shows pipeline intake, Segment Source Roster, segment capture pack, evidence matrix, TVP analysis pack, and publication views.",
            "2. Open Segment Source Roster and confirm role-family, job-posting, and social sources are represented.",
            "3. Open Social Platform Audit and confirm social observations cite upstream evidence ids.",
            "4. Open L4 Publication and confirm recommendations cite segment evidence records.",
        ]
    if fixture == "competitor-messaging-workbook" or manifest_template_id(manifest) == COMPETITOR_WORKBOOK_TEMPLATE_ID:
        return [
            "1. Confirm the workflow shows pipeline intake, source roster, Workbook Extraction, evidence matrix, analysis pack, Data Workbook, and L4 views.",
            "2. Open Workbook Extraction and confirm sheet dimensions, effective ranges, and header maps are visible.",
            "3. Open Data Workbook and confirm evidence cells and Partner Activation records retain source cells.",
            "4. Open L4 Publication and confirm coverage findings cite workbook evidence ids.",
        ]
    if fixture == "dei-competitor-audit" or manifest_template_id(manifest) == DEI_COMPETITOR_AUDIT_TEMPLATE_ID:
        return [
            "1. Confirm the workflow shows pipeline intake, source roster, deck extraction, DEI evidence matrix, analysis pack, and publication views.",
            "2. Open DEI Activation Matrix and confirm each activation cites evidence ids.",
            "3. Open Inclusion Philosophy Map and Partner Landscape to compare philosophy classes and coverage gaps.",
            "4. Open L4 Publication and confirm the readout is built from the DEI evidence matrix.",
        ]
    if fixture == "campaign-desk-research-comp-audit" or manifest_template_id(manifest) == CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID:
        return [
            "1. Confirm the workflow shows pipeline intake, research source roster, desk research evidence, Campaign Case Matrix, Channel Tactic map, analysis pack, and L4 views.",
            "2. Open Campaign Case Matrix and confirm the twelve case studies retain source linkage.",
            "3. Open Channel Tactic map and confirm tactics connect to campaign cases and funnel stages.",
            "4. Open L4 Publication and confirm recommendations cite source, case, and tactic records.",
        ]
    if fixture == "kilos-methodology" or manifest_template_id(manifest) == KILOS_METHODOLOGY_TEMPLATE_ID:
        return [
            "1. Confirm the workflow shows pipeline intake, ontology source roster, KILOS Browser, Mapping Workbook, methodology deck, scorecard tables, snippets, and L4 views.",
            "2. Open KILOS Browser and confirm the five pillars and factor counts are preserved.",
            "3. Open Mapping Workbook and confirm mapped and non-KILOS rows remain explicit.",
            "4. Open L4 Publication and confirm methodology copy is rendered from the same ontology records.",
        ]
    if fixture == "easy-audit" or manifest.resolve() == (
        REPO_ROOT / "artifacts" / "easy-audit" / "latest" / "manifest.json"
    ).resolve():
        return [
            "1. Confirm the artifact summary shows the Acme Robotics audit, not the public-page matrix.",
            "2. Inspect the projected L0-L4 steps and provenance edges in the sidebar.",
            "3. Open the final report and confirm the designed HTML report renders without edit controls.",
            "4. Open the JSON/text artifacts and confirm they render as inspectable document views.",
        ]
    return [
        "1. Inspect the artifact summary in the right sidebar.",
        "2. Toggle page and slot filter chips; previous/next should follow the filtered set.",
        "3. Open a markdown summary artifact and confirm edit/annotation still works.",
        "4. Inspect tall/full-page captures; viewer zoom should fit without mutating image bytes.",
    ]
