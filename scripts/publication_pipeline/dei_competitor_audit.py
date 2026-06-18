#!/usr/bin/env python3
"""DEI competitor audit publication archetype."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .core import (
    CREATED_AT,
    DEI_COMPETITOR_AUDIT_DEFAULT_PROFILE_PATH,
    DEI_COMPETITOR_AUDIT_KEY,
    DEI_COMPETITOR_AUDIT_TEMPLATE_ID,
    REPO_ROOT,
    is_default_output_dir,
    manifest_artifact,
    manifest_step,
    prepare_output_dir,
    render_publication_html,
    slugify,
    write_json,
    write_text,
)
from .html_views import publication_table_body
from .projection_groups import publication_composite_group
from .workbook_shared import (
    load_workbook_profile,
    workbook_entities,
    workbook_partner_orgs,
    workbook_source_roster,
)


DEI_COMPETITOR_AUDIT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "dei-competitor-audit" / "latest"


def load_dei_competitor_profile(path: Path | None = None) -> dict[str, Any]:
    profile = load_workbook_profile(path, default_path=DEI_COMPETITOR_AUDIT_DEFAULT_PROFILE_PATH)
    profile.setdefault("dei_dimensions", ["gender", "ethnicity", "LGBTQ+", "socioeconomic", "disability", "age", "caregivers"])
    profile.setdefault("partner_org_sources", ["memberships", "external networks", "awards", "benchmarks"])
    profile.setdefault("withdrawal_watch", True)
    return profile


def dei_intake(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": DEI_COMPETITOR_AUDIT_TEMPLATE_ID,
        "pipeline_key": DEI_COMPETITOR_AUDIT_KEY,
        "client": {
            "name": str(profile.get("client_full_name") or profile.get("client_name") or "Client"),
            "sector": str(profile.get("industry") or "Investment management"),
            "geography": str(profile.get("geography") or "United States"),
            "domain": str(profile.get("domain") or f"{slugify(str(profile.get('client_name') or 'client'))}.example"),
            "audience": str(profile.get("audience") or "Investment talent"),
        },
        "objective": "Compare DEI messaging, activations, inclusion philosophy, partner coverage, benchmarks, and gaps across talent competitors.",
        "dei_dimensions": list(profile.get("dei_dimensions") or []),
        "partner_org_sources": list(profile.get("partner_org_sources") or []),
        "withdrawal_watch": bool(profile.get("withdrawal_watch", True)),
        "competitors": [entity["name"] for entity in workbook_entities(profile)[1:]],
        "ontology": {"framework_id": "KILOS", "framework_version": "1.0"},
        "desired_outputs": ["dei_activation_matrix", "inclusion_philosophy_map", "partner_landscape", "competitor_audit_deck", "l4_publication"],
        "review_requirements": {
            "manual_review_gates": ["activation coverage", "inclusion philosophy fit", "partner landscape coverage", "gap recommendations"],
        },
    }


def dei_source_roster(profile: dict[str, Any]) -> dict[str, Any]:
    roster = workbook_source_roster(profile)
    roster["source_model"] = "dei_competitor_audit"
    return roster


def dei_deck_extraction(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-dei-audit"),
        "slide_count": 33,
        "sections": [
            {"range": "1", "label": "cover"},
            {"range": "2-4", "label": "client employer brand and DEI positioning"},
            {"range": "5-7", "label": "creative/internal/external activations"},
            {"range": "8-13", "label": "talent competitor landscape and KILOS messaging"},
            {"range": "14-19", "label": "inclusion philosophies and positioning synthesis"},
            {"range": "20-22", "label": "partnership landscape and coverage gaps"},
            {"range": "23-28", "label": "best-practice benchmarks and awards"},
            {"range": "29-31", "label": "lessons and case examples"},
            {"range": "32", "label": "thank you"},
            {"range": "33", "label": "DEI withdrawals watch appendix"},
        ],
    }


def dei_evidence_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entities = workbook_entities(profile)
    items = []
    for entity in entities:
        for index in range(1, 9):
            items.append(
                {
                    "evidence_id": f"dei-evidence:{len(items) + 1:03d}",
                    "project_id": str(profile.get("project_id") or ""),
                    "entity_id": entity["entity_id"],
                    "section": "dei_messaging",
                    "evidence_text": f"{entity['name']} DEI evidence theme {index}",
                    "source_slide": 4 + index,
                    "confidence": "medium",
                }
            )
    return items


def ids_for_entity(evidence_items: list[dict[str, Any]], entity_id: str, limit: int = 3) -> list[str]:
    ids = [item["evidence_id"] for item in evidence_items if item.get("entity_id") == entity_id][:limit]
    return ids or [item["evidence_id"] for item in evidence_items[:limit]]


def dei_evidence_matrix(profile: dict[str, Any]) -> dict[str, Any]:
    entities = workbook_entities(profile)
    evidence_items = dei_evidence_items(profile)
    philosophy_classes = ["policy", "company/performance", "culture", "system"]
    activations = [
        {
            "activation_id": f"dei-activation:{index + 1:03d}",
            "entity_id": entities[index % len(entities)]["entity_id"],
            "activation_theme": f"DEI activation theme {index + 1}",
            "category": ["messaging", "internal", "external", "creative"][index % 4],
            "visibility": "high" if index % 3 == 0 else "medium",
            "supporting_evidence_ids": ids_for_entity(evidence_items, entities[index % len(entities)]["entity_id"]),
        }
        for index in range(30)
    ]
    philosophies = [
        {
            "philosophy_id": f"inclusion-philosophy:{index + 1:03d}",
            "entity_id": entity["entity_id"],
            "philosophy_class": philosophy_classes[index % len(philosophy_classes)],
            "belief": f"{entity['name']} inclusion philosophy signal",
            "narrative_level": "system" if index == 0 else philosophy_classes[index % len(philosophy_classes)],
            "supporting_evidence_ids": ids_for_entity(evidence_items, entity["entity_id"]),
        }
        for index, entity in enumerate(entities)
    ]
    gaps = [
        {
            "gap_id": f"coverage-gap:{index + 1:03d}",
            "dimension": dimension,
            "gap_type": "underrepresented_evidence",
            "affected_entities": [entities[index % len(entities)]["entity_id"]],
            "rationale": f"{dimension} evidence needs clearer proof or coverage.",
            "supporting_evidence_ids": ids_for_entity(evidence_items, entities[index % len(entities)]["entity_id"]),
        }
        for index, dimension in enumerate(["disability", "religion/faith", "age diversity", "reproductive health", "veterans/military", "caregivers/parents", "accessibility"])
    ]
    benchmarks = [
        {
            "benchmark_id": f"benchmark:{index + 1:03d}",
            "source_name": name,
            "year": 2025,
            "methodology": "reference benchmark list",
            "dimensions": ["gender", "ethnicity", "inclusion"],
            "supporting_evidence_ids": [evidence_items[index]["evidence_id"]],
        }
        for index, name in enumerate(["DEI award lists", "Private markets diversity benchmark", "Inclusive workplace index", "Partner organization landscape"])
    ]
    return {
        "project_id": str(profile.get("project_id") or ""),
        "evidence_items": evidence_items,
        "dei_activations": activations,
        "inclusion_philosophy_classes": philosophy_classes,
        "inclusion_philosophies": philosophies,
        "partner_orgs": workbook_partner_orgs(profile),
        "coverage_gaps": gaps,
        "benchmark_sources": benchmarks,
        "dei_withdrawal_watch": [
            {
                "watch_id": "withdrawal-watch:001",
                "signal": "DEI withdrawal watch appendix",
                "supporting_evidence_ids": [evidence_items[-1]["evidence_id"]],
            }
        ],
    }


def dei_analysis_pack(profile: dict[str, Any], matrix_record: dict[str, Any]) -> dict[str, Any]:
    evidence_items = list(matrix_record.get("evidence_items") or [])
    findings = []
    for index, activation in enumerate(matrix_record.get("dei_activations") or []):
        if index >= 8:
            break
        findings.append(
            {
                "finding_id": f"dei-finding:{index + 1:03d}",
                "entity_id": activation["entity_id"],
                "finding_type": "dei_activation_summary",
                "headline": activation["activation_theme"],
                "summary": "DEI activation is supported by visible messaging or program evidence.",
                "supporting_evidence_ids": activation["supporting_evidence_ids"],
                "confidence": "medium",
            }
        )
    for gap in matrix_record.get("coverage_gaps") or []:
        findings.append(
            {
                "finding_id": f"dei-finding:{len(findings) + 1:03d}",
                "entity_id": (gap.get("affected_entities") or [""])[0],
                "finding_type": "coverage_gap",
                "headline": f"{gap.get('dimension')} coverage gap",
                "summary": gap.get("rationale") or "",
                "supporting_evidence_ids": gap.get("supporting_evidence_ids") or [evidence_items[0]["evidence_id"]],
                "confidence": "medium",
            }
        )
    return {
        "project_id": str(profile.get("project_id") or ""),
        "activation_summaries": matrix_record.get("dei_activations") or [],
        "inclusion_philosophy_summaries": matrix_record.get("inclusion_philosophies") or [],
        "coverage_gap_summaries": matrix_record.get("coverage_gaps") or [],
        "findings": findings,
    }


def dei_activation_body(matrix_record: dict[str, Any]) -> str:
    rows = [[item["activation_theme"], item["category"], ", ".join(item["supporting_evidence_ids"])] for item in matrix_record.get("dei_activations") or []]
    return publication_table_body("DEI Activation Matrix", rows)


def dei_philosophy_body(matrix_record: dict[str, Any]) -> str:
    rows = [[item["entity_id"], item["philosophy_class"], ", ".join(item["supporting_evidence_ids"])] for item in matrix_record.get("inclusion_philosophies") or []]
    return publication_table_body("Inclusion Philosophy Map", rows)


def dei_partner_body(matrix_record: dict[str, Any]) -> str:
    rows = [[item["name"], item["dei_focus"], item["source_range"]] for item in matrix_record.get("partner_orgs") or []]
    return publication_table_body("Partner Organization Landscape", rows[:30])


def dei_deck_body(matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [[item["headline"], item["finding_type"], ", ".join(item["supporting_evidence_ids"])] for item in analysis_record.get("findings") or []]
    return publication_table_body("Competitor Audit Deck View", rows)


def dei_l4_body(profile: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    return f"""    <section>
      <h2>DEI Competitor Audit Readout</h2>
      <p>{escape(str(profile.get("client_full_name") or profile.get("client_name") or "Client"))} has {len(matrix_record.get("dei_activations") or [])} DEI activations, {len(matrix_record.get("inclusion_philosophies") or [])} philosophy records, and {len(matrix_record.get("coverage_gaps") or [])} coverage gaps.</p>
    </section>
{dei_deck_body(matrix_record, analysis_record)}
"""



def build_dei_competitor_audit_manifest(profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"publication-pipeline-{slugify(client_name)}-dei-competitor-audit",
        "company": client_name,
        "domain": str(profile.get("domain") or f"{slugify(client_name)}.example"),
        "template_id": DEI_COMPETITOR_AUDIT_TEMPLATE_ID,
        "talent_segment": str(profile.get("audience") or "Investment talent"),
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": DEI_COMPETITOR_AUDIT_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the DEI competitor audit request.", ["p0-pipeline-intake"], []),
            manifest_step("p0-source-roster", 0, "Source roster", "List DEI audit entities and source metadata.", ["p0-source-roster"], ["p0-pipeline-intake"]),
            manifest_step("p1-deck-extraction", 1, "Deck extraction", "Extract DEI audit deck section model.", ["p1-deck-extraction"], ["p0-source-roster"]),
            manifest_step("p2-dei-evidence-matrix", 2, "DEI evidence matrix", "Normalize activations, philosophies, partners, gaps, and benchmarks.", ["p2-dei-evidence-matrix"], ["p1-deck-extraction"]),
            manifest_step("p3-dei-analysis-pack", 3, "DEI analysis pack", "Summarize activation patterns, philosophies, and coverage gaps.", ["p3-dei-analysis-pack"], ["p2-dei-evidence-matrix"]),
            manifest_step("p4-dei-activation-matrix-view", 4, "DEI activation matrix view", "Render the DEI activation matrix.", ["p4-dei-activation-matrix"], ["p3-dei-analysis-pack"]),
            manifest_step("p4-inclusion-philosophy-map-view", 4, "Inclusion philosophy map view", "Render the inclusion philosophy map.", ["p4-inclusion-philosophy-map"], ["p3-dei-analysis-pack"]),
            manifest_step("p4-partner-landscape-view", 4, "Partner landscape view", "Render the partner organization landscape.", ["p4-partner-landscape"], ["p3-dei-analysis-pack"]),
            manifest_step("p4-competitor-audit-deck-view", 4, "Competitor audit deck view", "Render the DEI competitor audit deck.", ["p4-competitor-audit-deck"], ["p3-dei-analysis-pack"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the DEI audit readout.", ["p4-l4-publication"], ["p3-dei-analysis-pack"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "Operator-facing DEI audit intake"),
            manifest_artifact("p0-source-roster", 0, "source_roster", "p0-source-roster", ["p0-pipeline-intake"], "source-roster.json", "publication.source_roster", "DEI audit entity source roster"),
            manifest_artifact("p1-deck-extraction", 1, "deck_extraction", "p1-deck-extraction", ["p0-source-roster"], "deck-extraction.json", "publication.deck_extraction", "DEI audit deck extraction"),
            manifest_artifact("p2-dei-evidence-matrix", 2, "dei_evidence_matrix", "p2-dei-evidence-matrix", ["p1-deck-extraction"], "evidence-matrix.json", "publication.dei_evidence_matrix", "DEI activation and philosophy matrix"),
            manifest_artifact("p3-dei-analysis-pack", 3, "dei_analysis_pack", "p3-dei-analysis-pack", ["p2-dei-evidence-matrix"], "analysis-pack.json", "publication.dei_analysis_pack", "DEI coverage analysis pack"),
            manifest_artifact("p4-dei-activation-matrix", 4, "html", "p4-dei-activation-matrix-view", ["p3-dei-analysis-pack", "p2-dei-evidence-matrix"], "dei-activation-matrix.html", "publication.dei_activation_matrix", "DEI activation matrix view", composite_group=publication_composite_group("dei_activation_matrix")),
            manifest_artifact("p4-inclusion-philosophy-map", 4, "html", "p4-inclusion-philosophy-map-view", ["p3-dei-analysis-pack", "p2-dei-evidence-matrix"], "inclusion-philosophy-map.html", "publication.inclusion_philosophy_map", "Inclusion philosophy map view", composite_group=publication_composite_group("inclusion_philosophy_map")),
            manifest_artifact("p4-partner-landscape", 4, "html", "p4-partner-landscape-view", ["p3-dei-analysis-pack", "p2-dei-evidence-matrix"], "partner-landscape.html", "publication.partner_landscape", "Partner landscape view", composite_group=publication_composite_group("partner_landscape")),
            manifest_artifact("p4-competitor-audit-deck", 4, "audit_deck", "p4-competitor-audit-deck-view", ["p3-dei-analysis-pack", "p2-dei-evidence-matrix", "p1-deck-extraction"], "competitor-audit-deck-view.html", "publication.audit_deck", "DEI competitor audit deck view", composite_group=publication_composite_group("audit_deck")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-dei-analysis-pack", "p2-dei-evidence-matrix", "p1-deck-extraction"], "l4-publication.html", "publication.l4_publication", "DEI audit L4 readout", composite_group=publication_composite_group("l4_publication")),
        ],
    }


def generate_dei_competitor_audit_fixture(
    output_dir: Path = DEI_COMPETITOR_AUDIT_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, DEI_COMPETITOR_AUDIT_OUTPUT_DIR),
    )

    profile = load_dei_competitor_profile(project_profile_path)
    intake_record = dei_intake(profile)
    roster_record = dei_source_roster(profile)
    extraction_record = dei_deck_extraction(profile)
    matrix_record = dei_evidence_matrix(profile)
    analysis_record = dei_analysis_pack(profile, matrix_record)

    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "source-roster.json", roster_record)
    write_json(output_dir / "deck-extraction.json", extraction_record)
    write_json(output_dir / "evidence-matrix.json", matrix_record)
    write_json(output_dir / "analysis-pack.json", analysis_record)
    write_text(output_dir / "dei-activation-matrix.html", render_publication_html("DEI Activation Matrix", dei_activation_body(matrix_record)))
    write_text(output_dir / "inclusion-philosophy-map.html", render_publication_html("Inclusion Philosophy Map", dei_philosophy_body(matrix_record)))
    write_text(output_dir / "partner-landscape.html", render_publication_html("Partner Organization Landscape", dei_partner_body(matrix_record)))
    write_text(output_dir / "competitor-audit-deck-view.html", render_publication_html("DEI Competitor Audit Deck", dei_deck_body(matrix_record, analysis_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("DEI Competitor Audit Readout", dei_l4_body(profile, matrix_record, analysis_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_dei_competitor_audit_manifest(profile))
    return manifest_path



__all__ = ["DEI_COMPETITOR_AUDIT_TEMPLATE_ID", "generate_dei_competitor_audit_fixture"]
