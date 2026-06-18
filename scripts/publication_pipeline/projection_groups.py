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
}


def publication_view_group_config(artifact: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(artifact.get("kind") or artifact.get("type") or "")
    return PUBLICATION_VIEW_KINDS.get(kind)
