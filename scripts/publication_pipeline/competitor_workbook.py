#!/usr/bin/env python3
"""Competitor messaging workbook publication archetype."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .core import (
    COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH,
    COMPETITOR_WORKBOOK_KEY,
    COMPETITOR_WORKBOOK_LABEL,
    COMPETITOR_WORKBOOK_TEMPLATE_ID,
    CREATED_AT,
    REPO_ROOT,
    is_default_output_dir,
    load_project_profile,
    manifest_artifact,
    manifest_step,
    prepare_output_dir,
    render_publication_html,
    slugify,
    source_urls_from_entity,
    write_json,
    write_text,
)
from .projection_groups import publication_composite_group
from .segment_tvp import segment_tvp_table_body


COMPETITOR_WORKBOOK_OUTPUT_DIR = REPO_ROOT / "artifacts" / "competitor-messaging-workbook" / "latest"


def load_competitor_workbook_profile(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH
    profile = load_project_profile(path)
    if "workbook_entities" not in profile:
        profile["workbook_entities"] = [profile.get("client_full_name") or profile.get("client_name") or "Client"] + [
            competitor.get("name")
            for competitor in profile.get("competitors") or []
            if isinstance(competitor, dict)
        ]
    return profile


def workbook_entities(profile: dict[str, Any]) -> list[dict[str, Any]]:
    names = list(profile.get("workbook_entities") or [])
    if not names:
        names = [profile.get("client_full_name") or profile.get("client_name") or "Client"]
    entities = []
    for index, name_value in enumerate(names[:8]):
        name = str(name_value or f"Entity {index + 1}")
        role = "client" if index == 0 else "competitor"
        entities.append(
            {
                "entity_id": f"{role}-{slugify(name)}",
                "name": name,
                "role": role,
                "column_letter": chr(ord("C") + index),
                "careers_url": f"https://{slugify(name)}.example/careers",
                "dei_url": "" if index == 5 else f"https://{slugify(name)}.example/diversity",
                "headline": f"{name} careers headline",
            }
        )
    return entities


def workbook_intake(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": COMPETITOR_WORKBOOK_TEMPLATE_ID,
        "pipeline_key": COMPETITOR_WORKBOOK_KEY,
        "client": {
            "name": str(profile.get("client_full_name") or profile.get("client_name") or "Client"),
            "sector": str(profile.get("industry") or "Investment management"),
            "geography": str(profile.get("geography") or "United States"),
            "domain": str(profile.get("domain") or f"{slugify(str(profile.get('client_name') or 'client'))}.example"),
            "audience": str(profile.get("audience") or "Investment talent"),
        },
        "objective": "Normalize a wide competitor messaging workbook into long-form evidence, partner activations, and workbook-ready publication views.",
        "matrix_workbook": {
            "source_kind": "reference_workbook_shape",
            "main_sheet": "Messaging audit",
            "partner_sheet": "Partner orgs",
        },
        "source_seeds": [
            {"entity_id": entity["entity_id"], "source_type": "careers", "url": entity["careers_url"]}
            for entity in workbook_entities(profile)
        ],
        "competitors": [entity["name"] for entity in workbook_entities(profile)[1:]],
        "ontology": {"framework_id": "KILOS", "framework_version": "1.0"},
        "desired_outputs": ["workbook_extraction", "evidence_matrix", "analysis_pack", "data_workbook", "l4_publication"],
        "review_requirements": {
            "effective_range_required": True,
            "manual_review_gates": ["workbook header map", "cell lineage", "partner activation dedupe", "coverage summary"],
        },
    }


def workbook_source_roster(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-competitor-workbook"),
        "entities": [
            {
                "entity_id": entity["entity_id"],
                "name": entity["name"],
                "role": entity["role"],
                "column_letter": entity["column_letter"],
                "source_urls": {
                    "careers_url": entity["careers_url"],
                    "dei_url": entity["dei_url"] or "not_found",
                },
                "headline": entity["headline"],
            }
            for entity in workbook_entities(profile)
        ],
    }


def workbook_theme_rows() -> list[dict[str, Any]]:
    section_counts = [
        ("KINSHIP", 8),
        ("IMPACT", 7),
        ("LIFESTYLE", 7),
        ("OPPORTUNITY", 7),
        ("STATUS", 8),
        ("Themes", 14),
        ("Creative", 6),
        ("Internal initiatives", 8),
        ("External activations", 6),
    ]
    rows = []
    row_index = 6
    for section_label, count in section_counts:
        for index in range(1, count + 1):
            rows.append(
                {
                    "row_index": row_index,
                    "matrix_zone": "kilos" if section_label in {"KINSHIP", "IMPACT", "LIFESTYLE", "OPPORTUNITY", "STATUS"} else "dei",
                    "section_label": section_label,
                    "theme_label": f"{section_label} theme {index}",
                }
            )
            row_index += 1
    return rows


def workbook_extraction(profile: dict[str, Any]) -> dict[str, Any]:
    entities = workbook_entities(profile)
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-competitor-workbook"),
        "sheets": {
            "Messaging audit": {"dimension": "A1:Z1017", "effective_range": "A1:L135", "non_empty_cells": 405, "formula_cells": 52},
            "Partner orgs": {"dimension": "A1:Z1001", "effective_range": "A1:D37", "non_empty_cells": 127},
            "notes": {"dimension": "A1:A12", "populated_rows": 6},
        },
        "header_map": {
            "entity_columns": [{"entity_id": entity["entity_id"], "name": entity["name"], "column_letter": entity["column_letter"]} for entity in entities],
            "metadata_rows": {"careers_url": 3, "dei_url": 4, "headline": 5},
            "theme_rows": workbook_theme_rows(),
            "partner_rows": {"start": 84, "end": 122, "formula_column": "L"},
        },
    }


def workbook_wide_matrix_cells(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entities = workbook_entities(profile)
    cells = []
    for row in workbook_theme_rows():
        for entity in entities:
            source_cell = f"{entity['column_letter']}{row['row_index']}"
            cells.append(
                {
                    "cell_id": f"cell:{source_cell.lower()}",
                    "source_sheet": "Messaging audit",
                    "source_cell": source_cell,
                    "row_index": row["row_index"],
                    "column_letter": entity["column_letter"],
                    "matrix_zone": row["matrix_zone"],
                    "section_label": row["section_label"],
                    "theme_label": row["theme_label"],
                    "entity_id": entity["entity_id"],
                    "entity_role": entity["role"],
                    "raw_value": f"{entity['name']} evidence for {row['theme_label']}",
                    "normalized_value": f"{entity['name']} evidence for {row['theme_label']}",
                    "value_kind": "evidence" if len(cells) < 128 else "empty_potential",
                    "kilos_status": "kilos_mapped" if row["matrix_zone"] == "kilos" else "non_kilos_context",
                }
            )
    return cells


def workbook_partner_orgs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    focus_values = ["gender", "ethnicity", "LGBTQ+", "socioeconomic", "disability", "caregivers"]
    return [
        {
            "partner_org_id": f"partner:{index:02d}",
            "name": f"Partner Network {index:02d}",
            "primary_geography": "Global" if index % 3 == 0 else "United States",
            "dei_focus": focus_values[index % len(focus_values)],
            "organisation_type": "network" if index % 2 else "benchmark",
            "source_sheet": "Partner orgs",
            "source_range": f"A{index + 7}:D{index + 7}",
        }
        for index in range(1, 31)
    ]


def workbook_partner_activations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entities = workbook_entities(profile)
    activations = []
    for index in range(57):
        entity = entities[index % len(entities)]
        row = 84 + (index % 39)
        activations.append(
            {
                "activation_id": f"partner-activation:{index + 1:03d}",
                "partner_org_id": f"partner:{(index % 30) + 1:02d}",
                "entity_id": entity["entity_id"],
                "present": True,
                "source_sheet": "Messaging audit",
                "source_cell": f"{entity['column_letter']}{row}",
            }
        )
    return activations


def workbook_evidence_matrix(profile: dict[str, Any]) -> dict[str, Any]:
    cells = workbook_wide_matrix_cells(profile)
    evidence_items = [
        {
            "evidence_id": f"evidence:{index + 1:03d}",
            "project_id": str(profile.get("project_id") or ""),
            "entity_id": cell["entity_id"],
            "source_sheet": cell["source_sheet"],
            "source_cell": cell["source_cell"],
            "section": cell["section_label"],
            "theme_label": cell["theme_label"],
            "evidence_text": cell["normalized_value"],
            "kilos_status": cell["kilos_status"],
            "confidence": "medium",
        }
        for index, cell in enumerate(cells[:128])
    ]
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-competitor-workbook"),
        "wide_matrix_cells": cells,
        "evidence_items": evidence_items,
        "partner_orgs": workbook_partner_orgs(profile),
        "partner_activations": workbook_partner_activations(profile),
        "coverage_summary": {
            "dense_potential_cells": 568,
            "sparse_evidence_cells": 128,
            "partner_flags": 57,
        },
    }


def workbook_analysis_pack(profile: dict[str, Any], matrix_record: dict[str, Any]) -> dict[str, Any]:
    evidence_items = list(matrix_record.get("evidence_items") or [])
    findings = []
    for index, entity in enumerate(workbook_entities(profile)):
        ids = [item["evidence_id"] for item in evidence_items if item.get("entity_id") == entity["entity_id"]][:4]
        findings.append(
            {
                "finding_id": f"workbook-finding:{index + 1:03d}",
                "entity_id": entity["entity_id"],
                "finding_type": "coverage_summary",
                "headline": f"{entity['name']} workbook coverage",
                "summary": f"{entity['name']} has normalized messaging, DEI, and partner activation evidence.",
                "supporting_evidence_ids": ids or [item["evidence_id"] for item in evidence_items[:3]],
                "confidence": "medium",
            }
        )
    return {
        "project_id": str(profile.get("project_id") or ""),
        "section_density": matrix_record["coverage_summary"],
        "competitor_coverage_gaps": findings[1:],
        "dei_activation_summaries": matrix_record.get("partner_activations") or [],
        "findings": findings,
    }


def workbook_view_body(matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [
        [str(item.get("entity_id") or ""), str(item.get("source_cell") or ""), str(item.get("evidence_text") or "")]
        for item in matrix_record.get("evidence_items") or []
    ]
    partner_rows = [
        [str(item.get("partner_org_id") or ""), str(item.get("entity_id") or ""), str(item.get("source_cell") or "")]
        for item in matrix_record.get("partner_activations") or []
    ]
    return segment_tvp_table_body("Workbook Evidence Matrix", rows[:30]) + segment_tvp_table_body("Partner Activation Matrix", partner_rows[:30])


def workbook_l4_body(profile: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    return f"""    <section>
      <h2>Competitor Messaging Workbook Readout</h2>
      <p>{escape(str(profile.get("client_full_name") or profile.get("client_name") or "Client"))} has {len(matrix_record.get("evidence_items") or [])} sparse evidence cells normalized from {len(matrix_record.get("wide_matrix_cells") or [])} dense matrix potentials.</p>
    </section>
{segment_tvp_table_body("Coverage Findings", [[str(item.get("headline") or ""), str(item.get("summary") or ""), ", ".join(item.get("supporting_evidence_ids") or [])] for item in analysis_record.get("findings") or []])}
"""



def build_competitor_workbook_manifest(profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"publication-pipeline-{slugify(client_name)}-competitor-workbook",
        "company": client_name,
        "domain": str(profile.get("domain") or f"{slugify(client_name)}.example"),
        "template_id": COMPETITOR_WORKBOOK_TEMPLATE_ID,
        "talent_segment": str(profile.get("audience") or "Investment talent"),
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": COMPETITOR_WORKBOOK_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the workbook ingestion request.", ["p0-pipeline-intake"], []),
            manifest_step("p0-source-roster", 0, "Source roster", "List workbook entities and source metadata.", ["p0-source-roster"], ["p0-pipeline-intake"]),
            manifest_step("p1-workbook-extraction", 1, "Workbook extraction", "Extract sheet metadata, headers, cells, and partner rows.", ["p1-workbook-extraction"], ["p0-source-roster"]),
            manifest_step("p2-evidence-matrix", 2, "Evidence matrix", "Normalize workbook cells and partner activations.", ["p2-evidence-matrix"], ["p1-workbook-extraction"]),
            manifest_step("p3-analysis-pack", 3, "Analysis pack", "Summarize workbook coverage and gaps.", ["p3-analysis-pack"], ["p2-evidence-matrix"]),
            manifest_step("p4-data-workbook-view", 4, "Data workbook view", "Render the normalized workbook view.", ["p4-data-workbook"], ["p3-analysis-pack"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the workbook readout.", ["p4-l4-publication"], ["p3-analysis-pack"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "Operator-facing workbook intake"),
            manifest_artifact("p0-source-roster", 0, "source_roster", "p0-source-roster", ["p0-pipeline-intake"], "source-roster.json", "publication.source_roster", "Workbook entity source roster"),
            manifest_artifact("p1-workbook-extraction", 1, "workbook_extraction", "p1-workbook-extraction", ["p0-source-roster"], "workbook-extraction.json", "publication.workbook_extraction", "Workbook sheet and header extraction"),
            manifest_artifact("p2-evidence-matrix", 2, "evidence_matrix", "p2-evidence-matrix", ["p1-workbook-extraction"], "evidence-matrix.json", "publication.evidence_matrix", "Normalized workbook evidence and partner activations"),
            manifest_artifact("p3-analysis-pack", 3, "analysis_pack", "p3-analysis-pack", ["p2-evidence-matrix"], "analysis-pack.json", "publication.analysis_pack", "Workbook coverage analysis"),
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-workbook-extraction"], "data-workbook-view.html", "publication.data_workbook", "Workbook explorer view", composite_group=publication_composite_group("data_workbook")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-workbook-extraction"], "l4-publication.html", "publication.l4_publication", "Workbook L4 readout", composite_group=publication_composite_group("l4_publication")),
        ],
    }


def generate_competitor_messaging_workbook_fixture(
    output_dir: Path = COMPETITOR_WORKBOOK_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, COMPETITOR_WORKBOOK_OUTPUT_DIR),
    )

    profile = load_competitor_workbook_profile(project_profile_path)
    intake_record = workbook_intake(profile)
    roster_record = workbook_source_roster(profile)
    extraction_record = workbook_extraction(profile)
    matrix_record = workbook_evidence_matrix(profile)
    analysis_record = workbook_analysis_pack(profile, matrix_record)

    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "source-roster.json", roster_record)
    write_json(output_dir / "workbook-extraction.json", extraction_record)
    write_json(output_dir / "evidence-matrix.json", matrix_record)
    write_json(output_dir / "analysis-pack.json", analysis_record)
    write_text(output_dir / "data-workbook-view.html", render_publication_html("Competitor Messaging Workbook", workbook_view_body(matrix_record, analysis_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("Competitor Messaging Workbook Readout", workbook_l4_body(profile, matrix_record, analysis_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_competitor_workbook_manifest(profile))
    return manifest_path



__all__ = ["COMPETITOR_WORKBOOK_TEMPLATE_ID", "generate_competitor_messaging_workbook_fixture"]
