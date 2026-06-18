#!/usr/bin/env python3
"""Segment-specific TVP audit publication archetype."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .core import (
    CREATED_AT,
    REPO_ROOT,
    SEGMENT_TVP_DEFAULT_PROFILE_PATH,
    SEGMENT_TVP_KEY,
    SEGMENT_TVP_LABEL,
    SEGMENT_TVP_TEMPLATE_ID,
    evidence_items_from_capture_pack,
    is_default_output_dir,
    load_kilos_terms,
    load_project_profile,
    manifest_artifact,
    manifest_step,
    prepare_output_dir,
    render_publication_html,
    slugify,
    support_ids,
    table_rows,
    write_json,
    write_text,
)
from .projection_groups import publication_composite_group


SEGMENT_TVP_OUTPUT_DIR = REPO_ROOT / "artifacts" / "segment-tvp-audit" / "latest"


SEGMENT_EVIDENCE_THEME_TEMPLATES = [
    ("job_postings", "K", "K5", "Kinship / Sense of Belonging", "all_segment", "{name} uses team belonging and collaboration language in segment-facing job evidence."),
    ("role_family_careers_page", "I", "I6", "Impact / Innovation and Invention", "Technology", "{name} connects technology talent to modern platforms, invention, and product improvement."),
    ("role_family_careers_page", "I", "I1", "Impact / Meaningful Work for People", "Product", "{name} frames product work around customer, safety, service, or user outcomes."),
    ("job_postings", "L", "L1", "Lifestyle / Good Benefits", "all_segment", "{name} gives segment candidates tangible benefits, rewards, or wellbeing proof."),
    ("job_postings", "L", "L4", "Lifestyle / Flexibility (Hours)", "Technology", "{name} signals flexibility, hybrid work, autonomy, or scheduling control for technical roles."),
    ("careers_messaging", "O", "O6", "Opportunity / Career Progression", "all_segment", "{name} highlights growth paths, learning, mobility, or leadership progression."),
    ("job_postings", "O", "O3", "Opportunity / Challenging Work", "Technology", "{name} uses challenge, problem complexity, and technical variety as role-family proof."),
    ("social", "S", "S2", "Status / Industry Reputation", "all_segment", "{name} reinforces market credibility through social, awards, customer scale, or category leadership."),
    ("visual_identity", "K", "K1", "Kinship / Diverse and Inclusive", "all_segment", "{name} shows inclusive visual and verbal signals for segment candidates."),
    ("social", "I", "I5", "Impact / Impact on a Big Scale", "Product", "{name} uses social content to show scale, reach, and the impact of product decisions."),
    ("dedicated_page", "O", "O5", "Opportunity / Variety", "Technology", "{name} presents technology work as varied across domains, platforms, and teams."),
    ("recommendation_input", "S", "S5", "Status / Leadership Quality", "all_segment", "{name} can strengthen segment credibility by connecting leaders, strategy, and proofpoints."),
]



def load_segment_tvp_profile(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = SEGMENT_TVP_DEFAULT_PROFILE_PATH
    profile = load_project_profile(path)
    if "target_talent_segments" not in profile:
        profile["target_talent_segments"] = [str(profile.get("audience") or "Technology and Product")]
    if "segment_competitors" not in profile:
        profile["segment_competitors"] = list(profile.get("competitors") or [])
    if "role_evidence_sources" not in profile:
        profile["role_evidence_sources"] = ["job_postings", "role_family_careers_page", "innovation_or_product_page"]
    if "social_sources" not in profile:
        client_slug = slugify(str(profile.get("client_name") or "client"))
        profile["social_sources"] = [f"https://social.example/{client_slug}"]
    return profile


def segment_tvp_entities(profile: dict[str, Any]) -> list[dict[str, Any]]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    client_slug = slugify(client_name)
    entities = [
        {
            "entity_id": str(profile.get("client_entity_id") or f"client-{client_slug}"),
            "name": client_name,
            "role": "client",
            "careers_url": str(profile.get("careers_url") or f"https://{client_slug}.example/careers"),
            "role_family_url": str(profile.get("role_family_url") or f"https://{client_slug}.example/technology-product"),
            "job_search_url": str(profile.get("job_search_url") or f"https://{client_slug}.example/jobs?q=technology"),
            "social_url": str((profile.get("social_sources") or [f"https://social.example/{client_slug}"])[0]),
        }
    ]
    competitors = profile.get("segment_competitors") or profile.get("competitors") or []
    for index, competitor in enumerate(competitors, start=1):
        if not isinstance(competitor, dict):
            continue
        name = str(competitor.get("name") or f"Segment Competitor {index}")
        slug = slugify(name)
        entities.append(
            {
                "entity_id": str(competitor.get("entity_id") or f"competitor-{slug}"),
                "name": name,
                "role": "competitor",
                "careers_url": str(competitor.get("careers_url") or f"https://{slug}.example/careers"),
                "role_family_url": str(competitor.get("role_family_url") or f"https://{slug}.example/technology-product"),
                "job_search_url": str(competitor.get("job_search_url") or f"https://{slug}.example/jobs?q=technology"),
                "social_url": str(competitor.get("social_url") or f"https://social.example/{slug}"),
            }
        )
    return entities[:9]


def segment_tvp_intake(profile: dict[str, Any]) -> dict[str, Any]:
    entities = segment_tvp_entities(profile)
    source_seeds = []
    for entity in entities:
        for source_type, key in (
            ("careers", "careers_url"),
            ("role_family_careers_page", "role_family_url"),
            ("job_posting", "job_search_url"),
            ("social_profile", "social_url"),
        ):
            source_seeds.append(
                {
                    "entity_id": str(entity["entity_id"]),
                    "source_type": source_type,
                    "url": str(entity.get(key) or ""),
                }
            )
    return {
        "pipeline_id": SEGMENT_TVP_TEMPLATE_ID,
        "pipeline_key": SEGMENT_TVP_KEY,
        "client": {
            "name": str(entities[0].get("name") or profile.get("client_name") or "Client"),
            "sector": str(profile.get("industry") or "Unspecified"),
            "geography": str(profile.get("geography") or "United States"),
            "domain": str(profile.get("domain") or f"{slugify(str(profile.get('client_name') or 'client'))}.example"),
            "audience": str(profile.get("audience") or "Technology and Product talent"),
        },
        "objective": "Build a segment-specific TVP audit from role-family evidence, job postings, competitor messaging, and social observations.",
        "reference_artifacts": [
            {
                "reference_id": "segment-tvp-audit",
                "kind": "report_plus_deck_shape",
                "use": "segment evidence model, report structure, strategy deck, and social audit views",
            }
        ],
        "source_seeds": source_seeds,
        "competitors": [
            {
                "entity_id": str(entity["entity_id"]),
                "name": str(entity["name"]),
                "source_urls": {
                    "careers_url": str(entity.get("careers_url") or ""),
                    "role_family_url": str(entity.get("role_family_url") or ""),
                    "job_search_url": str(entity.get("job_search_url") or ""),
                    "social_url": str(entity.get("social_url") or ""),
                },
            }
            for entity in entities[1:]
        ],
        "target_talent_segments": list(profile.get("target_talent_segments") or [profile.get("audience") or "Technology"]),
        "role_evidence_sources": list(profile.get("role_evidence_sources") or []),
        "segment_competitors": [str(entity.get("name") or "") for entity in entities[1:]],
        "social_sources": list(profile.get("social_sources") or [str(entities[0].get("social_url") or "")]),
        "ontology": {
            "framework_id": "KILOS",
            "framework_version": "1.0",
            "evidence_rule": "Segment evidence keeps talent_segment plus KILOS pillar/factor lineage.",
        },
        "desired_outputs": [
            "capture_pack",
            "evidence_matrix",
            "analysis_pack",
            "report_docx",
            "brand_strategy_deck",
            "social_platform_audit",
            "data_workbook",
            "l4_publication",
        ],
        "review_requirements": {
            "minimum_evidence_items_per_entity": 10,
            "source_count": len(source_seeds),
            "manual_review_gates": [
                "segment source completeness",
                "job-posting and role-page evidence coverage",
                "social audit relevance",
                "segment recommendations cite evidence",
            ],
        },
    }


def segment_tvp_project_frame(profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(client_name)}-segment-tvp-audit"),
        "client_name": client_name,
        "industry": str(profile.get("industry") or "Technology"),
        "geography": str(profile.get("geography") or "United States"),
        "audience": str(profile.get("audience") or "Technology and Product talent"),
        "current_milestone": "l4_publication",
        "final_artifact_target": "l4_publication",
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "report_title": str(profile.get("report_title") or f"{client_name} Segment TVP Audit"),
        "report_date": str(profile.get("report_date") or "2026-06-18"),
        "target_talent_segments": list(profile.get("target_talent_segments") or ["Technology", "Product"]),
        "report_outline": {
            "pipeline_family": SEGMENT_TVP_KEY,
            "reference_shape": SEGMENT_TVP_LABEL,
            "sections": [
                {"section_id": "client_data_immersion", "title": "Client Data Immersion and Proofpoints", "expected_layout": "prose"},
                {"section_id": "competitor_messaging_audit", "title": "Competitor Messaging Audit", "expected_layout": "matrix"},
                {"section_id": "job_postings", "title": "Job posting evidence", "expected_layout": "table"},
                {"section_id": "dedicated_tech_product_pages", "title": "Dedicated technology/product pages", "expected_layout": "table"},
                {"section_id": "visual_identity", "title": "Visual identity and imagery", "expected_layout": "scorecard"},
                {"section_id": "social_platform_audit", "title": "Social platform audit", "expected_layout": "matrix"},
                {"section_id": "segment_recommendations", "title": "Segment TVP recommendations", "expected_layout": "prose"},
            ],
        },
    }


def segment_tvp_source_roster(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-segment-tvp-audit"),
        "entities": [
            {
                "entity_id": str(entity["entity_id"]),
                "name": str(entity["name"]),
                "role": str(entity["role"]),
                "talent_segment_scope": list(profile.get("target_talent_segments") or ["Technology", "Product"]),
                "source_urls": {
                    "careers_url": str(entity.get("careers_url") or ""),
                    "role_family_url": str(entity.get("role_family_url") or ""),
                    "job_search_url": str(entity.get("job_search_url") or ""),
                    "social_url": str(entity.get("social_url") or ""),
                },
            }
            for entity in segment_tvp_entities(profile)
        ],
    }


def segment_tvp_source_artifacts(project_id: str, entity: dict[str, Any]) -> list[dict[str, Any]]:
    entity_slug = slugify(str(entity.get("name") or entity.get("entity_id") or "entity"))
    specs = [
        ("careers", "careers_page", "careers_url"),
        ("role-family", "role_family_careers_page", "role_family_url"),
        ("jobs", "job_posting", "job_search_url"),
        ("social", "social_profile", "social_url"),
    ]
    return [
        {
            "artifact_id": f"source:{entity_slug}-{suffix}",
            "project_id": project_id,
            "entity_id": str(entity["entity_id"]),
            "source_url": str(entity.get(key) or ""),
            "source_type": source_type,
            "captured_at": CREATED_AT,
            "text_path": f"captures/{entity_slug}-{suffix}.txt",
            "screenshot_path": f"captures/{entity_slug}-{suffix}.png",
            "snapshot_path": f"captures/{entity_slug}-{suffix}.web-snapshot-data.json",
            "citation_label": f"{entity.get('name')} {suffix}",
        }
        for suffix, source_type, key in specs
    ]


def segment_tvp_capture_pack(profile: dict[str, Any]) -> dict[str, Any]:
    project_id = str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-segment-tvp-audit")
    source_artifacts: list[dict[str, Any]] = []
    excerpts: list[dict[str, Any]] = []
    for entity in segment_tvp_entities(profile):
        artifacts = segment_tvp_source_artifacts(project_id, entity)
        source_artifacts.extend(artifacts)
        artifact_by_type = {artifact["source_type"]: artifact["artifact_id"] for artifact in artifacts}
        for section, pillar_id, factor_id, theme_label, talent_segment, text_template in SEGMENT_EVIDENCE_THEME_TEMPLATES:
            if section in {"job_postings", "recommendation_input"}:
                artifact_id = artifact_by_type["job_posting"]
            elif section in {"role_family_careers_page", "dedicated_page"}:
                artifact_id = artifact_by_type["role_family_careers_page"]
            elif section in {"social"}:
                artifact_id = artifact_by_type["social_profile"]
            else:
                artifact_id = artifact_by_type["careers_page"]
            excerpts.append(
                {
                    "section": section,
                    "entity_id": str(entity["entity_id"]),
                    "artifact_id": artifact_id,
                    "evidence_text": text_template.format(name=str(entity["name"])),
                    "pillar_id": pillar_id,
                    "factor_id": factor_id,
                    "theme_label": theme_label,
                    "talent_segment": talent_segment,
                    "confidence": "high" if entity.get("role") == "client" else "medium",
                }
            )
    return {
        "project_id": project_id,
        "source_artifacts": source_artifacts,
        "excerpts": excerpts,
        "reference_shape": {
            "docx_tables": 11,
            "docx_media_files": 28,
            "deck_slides": 16,
            "heavy_table_slides": [4, 6, 7, 8, 12, 13],
        },
    }


def segment_tvp_evidence_items(capture_pack_record: dict[str, Any]) -> list[dict[str, Any]]:
    items = evidence_items_from_capture_pack(capture_pack_record)
    excerpts = [excerpt for excerpt in capture_pack_record.get("excerpts") or [] if isinstance(excerpt, dict)]
    for item, excerpt in zip(items, excerpts):
        item["talent_segment"] = str(excerpt.get("talent_segment") or "non_segment_context")
        item["segment_evidence_type"] = str(excerpt.get("section") or "notes")
    return items


def segment_tvp_evidence_matrix(kilos_terms: list[dict[str, Any]], capture_pack_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(capture_pack_record.get("project_id") or "segment-tvp-audit"),
        "ontology_terms": kilos_terms,
        "evidence_items": segment_tvp_evidence_items(capture_pack_record),
        "talent_segments": ["Technology", "Product", "all_segment", "non_segment_context"],
        "source_types": ["job_posting", "role_family_careers_page", "social_profile", "careers_page"],
    }


def segment_tvp_analysis_pack(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any]) -> dict[str, Any]:
    evidence_items = list(matrix_record.get("evidence_items") or [])
    findings: list[dict[str, Any]] = []

    def add(entity_id: str, finding_type: str, headline: str, summary: str, ids: list[str]) -> dict[str, Any]:
        finding = {
            "finding_id": f"segment-finding:{len(findings) + 1:03d}",
            "project_id": str(project_frame_record.get("project_id") or ""),
            "entity_id": entity_id,
            "finding_type": finding_type,
            "headline": headline,
            "summary": summary,
            "supporting_evidence_ids": ids,
            "confidence": "medium",
            "talent_segment": "Technology/Product",
        }
        findings.append(finding)
        return finding

    positioning = []
    for entity in roster_record.get("entities") or []:
        entity_id = str(entity.get("entity_id") or "")
        name = str(entity.get("name") or entity_id)
        positioning.append(
            add(
                entity_id,
                "segment_positioning",
                f"{name} segment positioning",
                f"{name} has role-family, job-posting, and social evidence for segment-specific TVP comparison.",
                support_ids(evidence_items, entity_id=entity_id, limit=4),
            )
        )
    client = next((entity for entity in roster_record.get("entities") or [] if entity.get("role") == "client"), {})
    client_id = str(client.get("entity_id") or "")
    recommendations = [
        add(client_id, "segment_recommendation", "Make technology and product proof easier to find", "Use a dedicated role-family page with hard proof, role examples, and social amplification.", support_ids(evidence_items, entity_id=client_id, limit=5)),
        add(client_id, "segment_recommendation", "Connect jobs to product impact", "Turn job-posting fragments into a coherent story about customer and platform outcomes.", support_ids(evidence_items, entity_id=client_id, pillar_id="I", limit=5)),
        add(client_id, "segment_recommendation", "Use social content as proof, not decoration", "Show team stories, product milestones, and leadership context in the social audit view.", support_ids(evidence_items, entity_id=client_id, limit=5)),
    ]
    return {
        "project_id": str(project_frame_record.get("project_id") or ""),
        "report_outline": project_frame_record.get("report_outline") or {},
        "segment_positioning_findings": positioning,
        "segment_recommendations": recommendations,
        "social_content_observations": [item for item in evidence_items if item.get("segment_evidence_type") == "social"],
        "visual_identity_observations": [item for item in evidence_items if item.get("segment_evidence_type") == "visual_identity"],
        "findings": findings,
    }


def segment_tvp_table_body(title: str, rows: list[list[str]]) -> str:
    return f"""    <section>
      <h2>{escape(title)}</h2>
      <table>
        <tr><th>Item</th><th>Detail</th><th>Evidence</th></tr>
{table_rows(rows)}
      </table>
    </section>
"""


def segment_tvp_report_body(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [
        [str(entity.get("name") or ""), str(entity.get("role") or ""), ", ".join(entity.get("talent_segment_scope") or [])]
        for entity in roster_record.get("entities") or []
    ]
    recommendations = [[str(item.get("headline") or ""), str(item.get("summary") or ""), ", ".join(item.get("supporting_evidence_ids") or [])] for item in analysis_record.get("segment_recommendations") or []]
    return segment_tvp_table_body("Segment Source Roster", rows) + segment_tvp_table_body("Segment Recommendations", recommendations)


def segment_tvp_deck_body(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [
        [str(finding.get("headline") or ""), str(finding.get("finding_type") or ""), ", ".join(finding.get("supporting_evidence_ids") or [])]
        for finding in (analysis_record.get("segment_positioning_findings") or [])[:8]
    ]
    return segment_tvp_table_body("Brand Strategy Deck View", rows)


def segment_tvp_social_body(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [
        [str(item.get("entity_id") or ""), str(item.get("talent_segment") or ""), str(item.get("evidence_text") or "")]
        for item in analysis_record.get("social_content_observations") or []
    ]
    return segment_tvp_table_body("Social Platform Audit", rows[:24])


def segment_tvp_workbook_body(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    rows = [
        [str(item.get("entity_id") or ""), f"{item.get('pillar_id')}{item.get('factor_id')}", str(item.get("talent_segment") or "")]
        for item in matrix_record.get("evidence_items") or []
    ]
    return segment_tvp_table_body("Segment Evidence Matrix", rows[:36])


def segment_tvp_l4_body(project_frame_record: dict[str, Any], roster_record: dict[str, Any], matrix_record: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    client_name = escape(str(project_frame_record.get("client_name") or "Client"))
    evidence_count = len(matrix_record.get("evidence_items") or [])
    return f"""    <section>
      <h2>Segment TVP Readout</h2>
      <p>{client_name} has {evidence_count} segment-tagged evidence records spanning job postings, role-family pages, careers messaging, visual identity, and social proof.</p>
    </section>
{segment_tvp_table_body("Priority Recommendations", [[str(item.get("headline") or ""), str(item.get("summary") or ""), ", ".join(item.get("supporting_evidence_ids") or [])] for item in analysis_record.get("segment_recommendations") or []])}
"""



def build_segment_tvp_manifest(project_frame_record: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(project_frame_record.get("client_name") or profile.get("client_name") or "Client")
    domain = str(profile.get("domain") or f"{slugify(client_name)}.example")
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"publication-pipeline-{slugify(client_name)}-segment-tvp-audit",
        "company": client_name,
        "domain": domain,
        "template_id": SEGMENT_TVP_TEMPLATE_ID,
        "talent_segment": str(project_frame_record.get("audience") or "Technology and Product talent"),
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": SEGMENT_TVP_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the segment TVP request and review requirements.", ["p0-pipeline-intake"], []),
            manifest_step("p0-project-frame", 0, "Project frame", "Define the segment TVP publication target.", ["p0-project-frame"], ["p0-pipeline-intake"]),
            manifest_step("p0-segment-source-roster", 0, "Segment source roster", "List client, segment competitors, and role-family sources.", ["p0-segment-source-roster"], ["p0-project-frame"]),
            manifest_step("p1-segment-capture-pack", 1, "Segment capture pack", "Stage role-family, job-posting, and social evidence.", ["p1-segment-capture-pack"], ["p0-segment-source-roster"]),
            manifest_step("p2-segment-evidence-matrix", 2, "Segment evidence matrix", "Normalize segment evidence into KILOS-tagged records.", ["p2-segment-evidence-matrix"], ["p1-segment-capture-pack"]),
            manifest_step("p3-tvp-analysis-pack", 3, "TVP analysis pack", "Derive segment positioning and recommendations.", ["p3-tvp-analysis-pack"], ["p2-segment-evidence-matrix"]),
            manifest_step("p4-report-docx-view", 4, "Report DOCX view", "Render the segment TVP report view.", ["p4-report-docx"], ["p3-tvp-analysis-pack"]),
            manifest_step("p4-brand-strategy-deck-view", 4, "Brand strategy deck view", "Render the segment brand strategy deck view.", ["p4-brand-strategy-deck"], ["p3-tvp-analysis-pack"]),
            manifest_step("p4-social-platform-audit-view", 4, "Social platform audit view", "Render the social platform audit view.", ["p4-social-platform-audit"], ["p3-tvp-analysis-pack"]),
            manifest_step("p4-data-workbook-view", 4, "Data workbook view", "Render the segment evidence workbook view.", ["p4-data-workbook"], ["p2-segment-evidence-matrix"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the segment TVP readout.", ["p4-l4-publication"], ["p3-tvp-analysis-pack"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "Operator-facing segment TVP intake"),
            manifest_artifact("p0-project-frame", 0, "publication_project", "p0-project-frame", ["p0-pipeline-intake"], "project-frame.json", "publication.project", "Segment TVP project frame"),
            manifest_artifact("p0-segment-source-roster", 0, "segment_source_roster", "p0-segment-source-roster", ["p0-project-frame"], "segment-source-roster.json", "publication.segment_source_roster", "Client and segment competitor source roster"),
            manifest_artifact("p1-segment-capture-pack", 1, "segment_capture_pack", "p1-segment-capture-pack", ["p0-segment-source-roster"], "segment-capture-pack.json", "publication.segment_capture_pack", "Segment capture pack with source artifacts and excerpts"),
            manifest_artifact("p2-segment-evidence-matrix", 2, "segment_evidence_matrix", "p2-segment-evidence-matrix", ["p1-segment-capture-pack"], "segment-evidence-matrix.json", "publication.segment_evidence_matrix", "KILOS-normalized segment evidence matrix"),
            manifest_artifact("p3-tvp-analysis-pack", 3, "tvp_analysis_pack", "p3-tvp-analysis-pack", ["p2-segment-evidence-matrix"], "tvp-analysis-pack.json", "publication.tvp_analysis_pack", "Segment TVP analysis findings"),
            manifest_artifact("p4-report-docx", 4, "report_docx", "p4-report-docx-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "report-docx-view.html", "publication.report_docx", "Segment TVP report view", composite_group=publication_composite_group("report_docx")),
            manifest_artifact("p4-brand-strategy-deck", 4, "brand_strategy_deck", "p4-brand-strategy-deck-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "brand-strategy-deck-view.html", "publication.brand_strategy_deck", "Brand strategy deck view", composite_group=publication_composite_group("brand_strategy_deck")),
            manifest_artifact("p4-social-platform-audit", 4, "social_platform_audit", "p4-social-platform-audit-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "social-platform-audit-view.html", "publication.social_platform_audit", "Social platform audit view", composite_group=publication_composite_group("social_platform_audit")),
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p2-segment-evidence-matrix", "p1-segment-capture-pack"], "data-workbook-view.html", "publication.data_workbook", "Segment evidence workbook view", composite_group=publication_composite_group("data_workbook")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "l4-publication.html", "publication.l4_publication", "Segment TVP L4 readout", composite_group=publication_composite_group("l4_publication")),
        ],
    }


def generate_segment_tvp_audit_fixture(
    output_dir: Path = SEGMENT_TVP_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, SEGMENT_TVP_OUTPUT_DIR),
    )

    profile = load_segment_tvp_profile(project_profile_path)
    project_frame_record = segment_tvp_project_frame(profile)
    intake_record = segment_tvp_intake(profile)
    roster_record = segment_tvp_source_roster(profile)
    capture_pack_record = segment_tvp_capture_pack(profile)
    evidence_matrix_record = segment_tvp_evidence_matrix(load_kilos_terms(), capture_pack_record)
    analysis_pack_record = segment_tvp_analysis_pack(project_frame_record, roster_record, evidence_matrix_record)

    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "project-frame.json", project_frame_record)
    write_json(output_dir / "segment-source-roster.json", roster_record)
    write_json(output_dir / "segment-capture-pack.json", capture_pack_record)
    write_json(output_dir / "segment-evidence-matrix.json", evidence_matrix_record)
    write_json(output_dir / "tvp-analysis-pack.json", analysis_pack_record)
    write_text(output_dir / "report-docx-view.html", render_publication_html("Segment TVP Report View", segment_tvp_report_body(project_frame_record, roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "brand-strategy-deck-view.html", render_publication_html("Brand Strategy Deck View", segment_tvp_deck_body(project_frame_record, roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "social-platform-audit-view.html", render_publication_html("Social Platform Audit", segment_tvp_social_body(project_frame_record, roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "data-workbook-view.html", render_publication_html("Segment Data Workbook View", segment_tvp_workbook_body(project_frame_record, roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("Segment TVP Publication", segment_tvp_l4_body(project_frame_record, roster_record, evidence_matrix_record, analysis_pack_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_segment_tvp_manifest(project_frame_record, profile))
    return manifest_path



__all__ = ["SEGMENT_TVP_TEMPLATE_ID", "generate_segment_tvp_audit_fixture"]
