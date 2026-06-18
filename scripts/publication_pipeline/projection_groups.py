from __future__ import annotations

from typing import Any


PUBLICATION_VIEW_KINDS = {
    "report_docx": {
        "label": "Report DOCX View",
        "slot": "publication.report_docx.bundle",
        "group_kind": "publication_report_docx_bundle",
    },
    "audit_deck": {
        "label": "Audit Deck View",
        "slot": "publication.audit_deck.bundle",
        "group_kind": "publication_audit_deck_bundle",
    },
    "data_workbook": {
        "label": "Data Workbook View",
        "slot": "publication.data_workbook.bundle",
        "group_kind": "publication_data_workbook_bundle",
    },
    "brand_strategy_deck": {
        "label": "Brand Strategy Deck View",
        "slot": "publication.brand_strategy_deck.bundle",
        "group_kind": "publication_brand_strategy_deck_bundle",
    },
    "social_platform_audit": {
        "label": "Social Platform Audit View",
        "slot": "publication.social_platform_audit.bundle",
        "group_kind": "publication_social_platform_audit_bundle",
    },
    "l4_publication": {
        "label": "L4 Publication View",
        "slot": "publication.l4_publication.bundle",
        "group_kind": "publication_l4_publication_bundle",
    },
    "dei_activation_matrix": {
        "label": "DEI Activation Matrix",
        "slot": "publication.dei_activation_matrix.bundle",
        "group_kind": "publication_dei_activation_matrix_bundle",
    },
    "inclusion_philosophy_map": {
        "label": "Inclusion Philosophy Map",
        "slot": "publication.inclusion_philosophy_map.bundle",
        "group_kind": "publication_inclusion_philosophy_map_bundle",
    },
    "partner_landscape": {
        "label": "Partner Landscape",
        "slot": "publication.partner_landscape.bundle",
        "group_kind": "publication_partner_landscape_bundle",
    },
    "campaign_recommendation_readout": {
        "label": "Campaign Recommendation Readout",
        "slot": "publication.campaign_recommendation_readout.bundle",
        "group_kind": "publication_campaign_recommendation_readout_bundle",
    },
    "report_section_snippets": {
        "label": "Report Section Snippets",
        "slot": "publication.report_section_snippets.bundle",
        "group_kind": "publication_report_section_snippets_bundle",
    },
}


def publication_view_group_config(artifact: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(artifact.get("kind") or artifact.get("type") or "")
    return PUBLICATION_VIEW_KINDS.get(kind)


def publication_composite_group(kind: str) -> dict[str, Any] | None:
    config = PUBLICATION_VIEW_KINDS.get(kind)
    if config is None:
        return None
    return {
        "kind": config["group_kind"],
        "label": config["label"],
        "slot": config["slot"],
    }
