#!/usr/bin/env python3
"""KILOS methodology publication archetype."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .core import (
    CREATED_AT,
    KILOS_PATH,
    KILOS_METHODOLOGY_KEY,
    KILOS_METHODOLOGY_LABEL,
    KILOS_METHODOLOGY_TEMPLATE_ID,
    REPO_ROOT,
    is_default_output_dir,
    load_kilos_terms,
    manifest_artifact,
    manifest_step,
    prepare_output_dir,
    render_publication_html,
    write_json,
    write_text,
)
from .html_views import publication_table_body
from .projection_groups import publication_composite_group


KILOS_METHODOLOGY_OUTPUT_DIR = REPO_ROOT / "artifacts" / "kilos-methodology" / "latest"


def kilos_framework() -> dict[str, Any]:
    return json.loads(KILOS_PATH.read_text(encoding="utf-8"))


def kilos_intake() -> dict[str, Any]:
    return {
        "pipeline_id": KILOS_METHODOLOGY_TEMPLATE_ID,
        "pipeline_key": KILOS_METHODOLOGY_KEY,
        "client": {"name": "KILOS methodology", "sector": "Employer brand ontology", "geography": "global", "audience": "audit authors"},
        "objective": "Turn KILOS ontology, survey mapping, methodology decks, and scorecard examples into reusable methodology publication artifacts.",
        "ontology_sources": ["kilos-framework.json", "KILOS mapping.xlsx", "KILOS Introduction.pptx", "ST_ KILOS Methodology.pptx", "KILOS tables.pptx"],
        "mapping_sources": ["survey labels", "response choices", "factor aliases"],
        "methodology_outputs": ["kilos_browser", "mapping_workbook", "methodology_deck", "scorecard_tables", "report_section_snippets", "l4_publication"],
        "review_requirements": {"manual_review_gates": ["ontology count parity", "mapping coverage", "methodology copy fit", "scorecard example review"]},
    }


def kilos_source_roster() -> dict[str, Any]:
    return {
        "ontology_sources": [
            {"source_id": "kilos-json", "source_kind": "ontology_json", "label": "kilos-framework.json", "pillar_count": 5, "factor_count": 29},
            {"source_id": "kilos-mapping", "source_kind": "mapping_workbook", "label": "KILOS mapping.xlsx", "sheet_count": 1, "rows": 33, "columns": 4},
            {"source_id": "kilos-intro", "source_kind": "methodology_deck", "label": "KILOS Introduction.pptx", "slides": 2, "tables": 0, "pictures": 0},
            {"source_id": "kilos-methodology", "source_kind": "methodology_deck", "label": "ST_ KILOS Methodology.pptx", "slides": 3, "tables": 0, "pictures": 0},
            {"source_id": "kilos-tables", "source_kind": "scorecard_deck", "label": "KILOS tables.pptx", "slides": 13, "tables": 11, "pictures": 25},
        ]
    }


def kilos_browser() -> dict[str, Any]:
    framework = kilos_framework()
    terms = load_kilos_terms()
    return {
        "framework_id": framework["framework"],
        "framework_version": framework["version"],
        "copyright": framework.get("copyright", ""),
        "description": framework.get("description", ""),
        "survey_question": framework.get("survey_question", ""),
        "pillars": framework["pillars"],
        "factors": terms,
        "survey_label_assignments": sum(len(term.get("aliases") or []) for term in terms),
        "pillar_factor_counts": {pillar["id"]: len(pillar["factors"]) for pillar in framework["pillars"]},
        "pillar_colors": {pillar["id"]: pillar["color"] for pillar in framework["pillars"]},
    }


def kilos_mapping_workbook() -> dict[str, Any]:
    rows = []
    pillar_counts = {"Kinship": 7, "Impact": 8, "Lifestyle": 6, "Opportunity": 5, "Status": 5}
    index = 1
    for pillar, count in pillar_counts.items():
        for offset in range(count):
            rows.append(
                {
                    "row": index + 1,
                    "response_choice": f"{pillar} response {offset + 1}",
                    "percentage": 50 + ((index + offset) % 30),
                    "count": 100 + index,
                    "workbook_pillar": pillar,
                    "mapped_factor_ids": [f"{pillar[0]}{1 + offset % 5}"],
                    "kilos_status": "kilos_mapped",
                }
            )
            index += 1
    rows.append(
        {
            "row": 33,
            "response_choice": "Prefer not to say",
            "percentage": 1,
            "count": 5,
            "workbook_pillar": "",
            "mapped_factor_ids": [],
            "kilos_status": "non_kilos_context",
        }
    )
    return {
        "sheet_name": "Export",
        "row_count": 33,
        "column_count": 4,
        "response_rows": 32,
        "kilos_rows": 31,
        "non_kilos_rows": 1,
        "pillar_row_counts": pillar_counts,
        "dual_mappings": [
            {"response_choice": "flexibility", "mapped_factor_ids": ["L4", "L5"]},
            {"response_choice": "challenge and variety", "mapped_factor_ids": ["O3", "O5"]},
        ],
        "unmapped_valid_factors": ["K3", "I5", "L3", "O2", "S3"],
        "rows": rows,
    }


def kilos_methodology_deck() -> dict[str, Any]:
    return {
        "total_slides": 18,
        "decks": [
            {"deck_id": "kilos-intro", "slides": 2, "purpose": "introductory methodology copy"},
            {"deck_id": "kilos-methodology", "slides": 3, "purpose": "factor glossary and scoring method"},
            {"deck_id": "kilos-tables", "slides": 13, "purpose": "scorecard and table examples"},
        ],
        "methodology_slides": [
            {"deck_id": "kilos-intro", "slide_number": 1, "title": "KILOS introduction", "extracted_text": "KILOS organizes employer-brand evidence into five pillars."},
            {"deck_id": "kilos-methodology", "slide_number": 1, "title": "Methodology", "extracted_text": "Evidence maps to factors, survey labels, and report explainers."},
        ],
    }


def kilos_scorecard_tables() -> dict[str, Any]:
    return {
        "tables_deck_slides": 13,
        "tables": 11,
        "pictures": 25,
        "scorecard_tables": [
            {"table_id": f"scorecard:{index + 1:02d}", "source_slide": index + 1, "example_label": f"KILOS scorecard example {index + 1}"}
            for index in range(11)
        ],
    }


def kilos_snippet_body(browser_record: dict[str, Any], mapping_record: dict[str, Any]) -> str:
    rows = [[pillar["name"], pillar["id"], str(len(pillar.get("factors") or []))] for pillar in browser_record.get("pillars") or []]
    return publication_table_body("KILOS Browser", rows) + publication_table_body("Mapping Workbook", [[key, str(value), ""] for key, value in mapping_record.get("pillar_row_counts", {}).items()])


def kilos_l4_body(browser_record: dict[str, Any], mapping_record: dict[str, Any], deck_record: dict[str, Any]) -> str:
    return f"""    <section>
      <h2>KILOS Methodology Publication</h2>
      <p>KILOS preserves {len(browser_record.get("pillars") or [])} pillars, {len(browser_record.get("factors") or [])} factors, {browser_record.get("survey_label_assignments")} survey-label assignments, and {deck_record.get("total_slides")} methodology/example slides.</p>
    </section>
{kilos_snippet_body(browser_record, mapping_record)}
"""



def build_kilos_methodology_manifest() -> dict[str, Any]:
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": "publication-pipeline-kilos-methodology",
        "company": "KILOS",
        "domain": "methodology.local",
        "template_id": KILOS_METHODOLOGY_TEMPLATE_ID,
        "talent_segment": "methodology",
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": KILOS_METHODOLOGY_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the KILOS methodology publication request.", ["p0-pipeline-intake"], []),
            manifest_step("p0-ontology-source-roster", 0, "Ontology source roster", "List ontology, mapping, methodology, and scorecard sources.", ["p0-ontology-source-roster"], ["p0-pipeline-intake"]),
            manifest_step("p1-kilos-browser", 1, "KILOS browser", "Project pillars, factors, aliases, colors, and descriptions.", ["p1-kilos-browser"], ["p0-ontology-source-roster"]),
            manifest_step("p1-mapping-workbook", 1, "Mapping workbook", "Project survey response mapping rows.", ["p1-mapping-workbook"], ["p1-kilos-browser"]),
            manifest_step("p2-methodology-deck", 2, "Methodology deck", "Project methodology deck records.", ["p2-methodology-deck"], ["p1-kilos-browser"]),
            manifest_step("p2-scorecard-tables", 2, "Scorecard tables", "Project scorecard table examples.", ["p2-scorecard-tables"], ["p2-methodology-deck"]),
            manifest_step("p3-report-section-snippets", 3, "Report section snippets", "Render reusable KILOS methodology snippets.", ["p3-report-section-snippets"], ["p2-scorecard-tables", "p1-mapping-workbook"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the KILOS methodology publication.", ["p4-l4-publication"], ["p3-report-section-snippets"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "KILOS methodology intake"),
            manifest_artifact("p0-ontology-source-roster", 0, "ontology_source_roster", "p0-ontology-source-roster", ["p0-pipeline-intake"], "ontology-source-roster.json", "publication.ontology_source_roster", "Ontology source roster"),
            manifest_artifact("p1-kilos-browser", 1, "kilos_browser", "p1-kilos-browser", ["p0-ontology-source-roster"], "kilos-browser.json", "publication.kilos_browser", "KILOS pillar and factor browser"),
            manifest_artifact("p1-mapping-workbook", 1, "mapping_workbook", "p1-mapping-workbook", ["p1-kilos-browser"], "mapping-workbook.json", "publication.mapping_workbook", "KILOS mapping workbook"),
            manifest_artifact("p2-methodology-deck", 2, "methodology_deck", "p2-methodology-deck", ["p1-kilos-browser"], "methodology-deck.json", "publication.methodology_deck", "Methodology deck records"),
            manifest_artifact("p2-scorecard-tables", 2, "scorecard_tables", "p2-scorecard-tables", ["p2-methodology-deck"], "scorecard-tables.json", "publication.scorecard_tables", "Scorecard table examples"),
            manifest_artifact("p3-report-section-snippets", 3, "html", "p3-report-section-snippets", ["p2-scorecard-tables", "p1-mapping-workbook"], "report-section-snippets.html", "publication.report_section_snippets", "Reusable KILOS report snippets", composite_group=publication_composite_group("report_section_snippets")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-report-section-snippets", "p2-scorecard-tables", "p1-kilos-browser"], "l4-publication.html", "publication.l4_publication", "KILOS methodology publication", composite_group=publication_composite_group("l4_publication")),
        ],
    }


def generate_kilos_methodology_fixture(
    output_dir: Path = KILOS_METHODOLOGY_OUTPUT_DIR,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, KILOS_METHODOLOGY_OUTPUT_DIR),
    )

    intake_record = kilos_intake()
    sources_record = kilos_source_roster()
    browser_record = kilos_browser()
    mapping_record = kilos_mapping_workbook()
    deck_record = kilos_methodology_deck()
    scorecard_record = kilos_scorecard_tables()

    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "ontology-source-roster.json", sources_record)
    write_json(output_dir / "kilos-browser.json", browser_record)
    write_json(output_dir / "mapping-workbook.json", mapping_record)
    write_json(output_dir / "methodology-deck.json", deck_record)
    write_json(output_dir / "scorecard-tables.json", scorecard_record)
    write_text(output_dir / "report-section-snippets.html", render_publication_html("KILOS Report Section Snippets", kilos_snippet_body(browser_record, mapping_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("KILOS Methodology Publication", kilos_l4_body(browser_record, mapping_record, deck_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_kilos_methodology_manifest())
    return manifest_path



__all__ = ["KILOS_METHODOLOGY_TEMPLATE_ID", "generate_kilos_methodology_fixture"]
