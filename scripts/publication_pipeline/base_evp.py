#!/usr/bin/env python3
"""EVP client immersion and competitor audit publication archetype."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from .core import (
    CREATED_AT,
    DEFAULT_OUTPUT_DIR,
    PIPELINE_KEY,
    PIPELINE_LABEL,
    PIPELINE_TEMPLATE_ID,
    REPO_ROOT,
    capture_pack_from_url_stage_manifests,
    default_project_profile,
    evidence_items_from_capture_pack,
    load_kilos_terms,
    load_project_profile,
    manifest_artifact,
    manifest_step,
    is_default_output_dir,
    prepare_output_dir,
    project_profile_entities,
    render_publication_html,
    slugify,
    source_roster_from_capture_pack,
    source_urls_from_entity,
    support_ids,
    table_rows,
    write_json,
    write_text,
)
from .projection_groups import publication_composite_group


REPORT_OUTLINE_SECTIONS = [
    ("introduction", "Introduction", ["publication_project"], "prose"),
    ("research_methodology", "Research Methodology", ["publication_project", "source_roster"], "prose"),
    ("client_data_immersion", "Client Data Immersion", ["survey_signal", "evidence_item"], "prose"),
    ("competitor_messaging_audit", "Competitor Messaging Audit", ["entity", "source_artifact"], "prose"),
    ("kilos_methodology", "Using KILOS to identify brand positioning", ["ontology_term"], "scorecard"),
    ("market_trends", "Market Trends Analysis", ["analysis_finding", "evidence_item"], "prose"),
    ("employer_brand_positioning", "Employer Brand Positioning Analysis", ["analysis_finding"], "prose"),
    ("headlines", "Headlines/taglines", ["evidence_item"], "table"),
    ("visual_identity", "Visual identity and imagery", ["evidence_item"], "table"),
    ("evp_analysis", "Employer Value Proposition analysis", ["analysis_finding", "evidence_item"], "prose"),
    ("strengths_and_gaps", "Strengths and Gaps Analysis", ["analysis_finding"], "prose"),
    ("strengths", "Strengths", ["analysis_finding"], "prose"),
    ("opportunities", "Opportunities", ["analysis_finding"], "prose"),
    ("employer_brand_risks", "Employer Brand Risks", ["analysis_finding"], "prose"),
    ("appendices", "Appendices", ["evidence_item", "review_snapshot"], "appendix"),
    ("careers_messaging_samples", "Careers website messaging samples and KILOS themes", ["evidence_item"], "matrix"),
    ("glassdoor_snapshot", "Employer reviews snapshot - Glassdoor", ["review_snapshot"], "table"),
    ("indeed_snapshot", "Employer reviews snapshot - Indeed", ["review_snapshot"], "table"),
]

EVIDENCE_THEME_TEMPLATES = [
    ("careers_messaging", "K", "K5", "Kinship / Sense of Belonging", "{name} invites talent into a culture where teams feel connected, supported, and able to belong."),
    ("dei_messaging", "K", "K1", "Kinship / Diverse and Inclusive", "{name} describes inclusive practices and employee voice as part of the workplace experience."),
    ("reviews", "K", "K4", "Kinship / Fairness and Respect", "{name} review themes point to fairness, respect, and manager consistency as candidate proof points."),
    ("careers_messaging", "I", "I1", "Impact / Meaningful Work for People", "{name} connects day-to-day work to outcomes for patients, communities, customers, and families."),
    ("careers_messaging", "I", "I5", "Impact / Impact on a Big Scale", "{name} uses scale, reach, and service footprint as proof that employees contribute to something substantial."),
    ("creative", "I", "I6", "Impact / Innovation and Invention", "{name} points to innovation, modern practice, and improved ways of working as part of the employer story."),
    ("benefits", "L", "L1", "Lifestyle / Good Benefits", "{name} presents benefits, wellbeing resources, and family support as reasons talent can thrive."),
    ("benefits", "L", "L4", "Lifestyle / Flexibility (Hours)", "{name} highlights scheduling choice, flexible programs, or work pattern control for key talent groups."),
    ("careers_messaging", "O", "O6", "Opportunity / Career Progression", "{name} emphasizes career paths, learning, progression, and long-term growth."),
    ("awards", "S", "S2", "Status / Industry Reputation", "{name} reinforces reputation through awards, recognition, quality credentials, or market position."),
]


def pipeline_intake_from_profile(
    profile: dict[str, Any],
    *,
    url_stage_manifest_paths: list[Path] | None = None,
) -> dict[str, Any]:
    entities = project_profile_entities(profile)
    client = entities[0] if entities else {}
    competitors = entities[1:]
    source_seeds = []
    for entity in entities:
        source_urls = source_urls_from_entity(entity)
        for source_key in ("careers_url", "culture_url", "dei_url"):
            source_url = str(source_urls.get(source_key) or "")
            if source_url:
                source_seeds.append(
                    {
                        "entity_id": str(entity.get("entity_id") or ""),
                        "source_type": source_key.replace("_url", ""),
                        "url": source_url,
                    }
                )
        for source_url in source_urls.get("review_urls") or []:
            source_seeds.append(
                {
                    "entity_id": str(entity.get("entity_id") or ""),
                    "source_type": "review",
                    "url": str(source_url),
                }
            )
    for path in url_stage_manifest_paths or []:
        source_seeds.append(
            {
                "source_type": "url_stage_manifest",
                "path": str(path),
            }
        )
    desired_outputs = [
        "capture_pack",
        "evidence_matrix",
        "analysis_pack",
        "report_docx",
        "audit_deck",
        "data_workbook",
        "l4_publication",
    ]
    return {
        "pipeline_id": PIPELINE_TEMPLATE_ID,
        "pipeline_key": PIPELINE_KEY,
        "client": {
            "name": str(client.get("name") or profile.get("client_full_name") or profile.get("client_name") or "Client"),
            "sector": str(profile.get("industry") or "Unspecified"),
            "geography": str(profile.get("geography") or "United States"),
            "domain": str(profile.get("domain") or f"{slugify(str(profile.get('client_name') or 'client'))}.example"),
            "audience": str(profile.get("audience") or "Employer brand target talent"),
        },
        "objective": "Generate a source-backed EVP client immersion and competitor messaging audit from reusable intake records.",
        "reference_artifacts": [
            {
                "reference_id": "evp-client-immersion-competitor-audit",
                "kind": "report_shape",
                "use": "section order, evidence density, and publication view coverage",
            }
        ],
        "source_seeds": source_seeds,
        "competitors": [
            {
                "entity_id": str(entity.get("entity_id") or ""),
                "name": str(entity.get("name") or ""),
                "source_urls": source_urls_from_entity(entity),
            }
            for entity in competitors
        ],
        "target_talent_segments": [str(profile.get("audience") or "Employer brand target talent")],
        "ontology": {
            "framework_id": "KILOS",
            "framework_version": "1.0",
            "evidence_rule": "Map every evidence item to a pillar/factor or mark it as non-KILOS context.",
        },
        "desired_outputs": desired_outputs,
        "review_requirements": {
            "minimum_evidence_items_per_entity": 10,
            "source_count": len(source_seeds),
            "screenshot_needs": "capture-stage screenshots stay on disk and are cited by source artifacts",
            "manual_review_gates": [
                "source roster completeness",
                "capture quality",
                "evidence lineage",
                "first-pass publication layout",
            ],
        },
    }


def pipeline_intake(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return pipeline_intake_from_profile(profile or default_project_profile())



def report_outline() -> dict[str, Any]:
    return {
        "pipeline_family": PIPELINE_KEY,
        "reference_shape": PIPELINE_LABEL,
        "sections": [
            {
                "section_id": section_id,
                "title": title,
                "source_record_types": source_record_types,
                "expected_layout": expected_layout,
            }
            for section_id, title, source_record_types, expected_layout in REPORT_OUTLINE_SECTIONS
        ],
    }


def project_frame_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-evp-competitor-audit"),
        "client_name": str(profile.get("client_name") or "Client"),
        "industry": str(profile.get("industry") or "Healthcare"),
        "geography": str(profile.get("geography") or "United States"),
        "audience": str(profile.get("audience") or "Clinical and technical talent"),
        "current_milestone": "l4_publication",
        "final_artifact_target": "l4_publication",
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "report_title": str(profile.get("report_title") or f"{profile.get('client_name') or 'Client'} EVP Client Data Immersion and Competitor Messaging Audit"),
        "report_date": str(profile.get("report_date") or "2026-06-18"),
        "report_outline": report_outline(),
    }


def project_frame(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return project_frame_from_profile(profile or default_project_profile())


def source_roster_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    project_id = str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-evp-competitor-audit")
    return {
        "project_id": project_id,
        "entities": [
            {
                "entity_id": str(entity.get("entity_id") or ""),
                "name": str(entity.get("name") or ""),
                "role": str(entity.get("role") or "competitor"),
                "source_urls": source_urls_from_entity(entity),
            }
            for entity in project_profile_entities(profile)
        ],
    }


def source_roster(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return source_roster_from_profile(profile or default_project_profile())


def source_roster_legacy() -> dict[str, Any]:
    return {
        "project_id": "legacy-source-roster",
        "entities": [
            {
                "entity_id": "client-example",
                "name": "Example Client",
                "role": "client",
                "source_urls": {
                    "careers_url": "https://example-client.example/careers",
                    "culture_url": "https://example-client.example/culture",
                    "dei_url": "https://example-client.example/diversity",
                    "review_urls": ["https://reviews.example/example-client"],
                    "other_urls": [],
                },
            },
        ],
    }



def source_artifacts_from_entity(project_id: str, entity: dict[str, Any]) -> list[dict[str, Any]]:
    entity_id = str(entity["entity_id"])
    entity_name = str(entity["name"])
    entity_slug = slugify(entity_name)
    source_urls = source_urls_from_entity(entity)
    artifact_specs = [
        ("careers", "careers_page", source_urls["careers_url"]),
        ("culture", "culture_page", source_urls["culture_url"]),
        ("benefits", "benefits_page", source_urls["other_urls"][0] if source_urls["other_urls"] else source_urls["careers_url"]),
    ]
    if source_urls["review_urls"]:
        artifact_specs.append(("reviews", "review_site", source_urls["review_urls"][0]))
    artifacts = []
    for suffix, source_type, source_url in artifact_specs:
        artifact_id = f"source:{entity_slug}-{suffix}"
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "project_id": project_id,
                "entity_id": entity_id,
                "source_url": source_url,
                "source_type": source_type,
                "captured_at": CREATED_AT,
                "text_path": f"captures/{entity_slug}-{suffix}.txt",
                "screenshot_path": f"captures/{entity_slug}-{suffix}.png",
                "snapshot_path": f"captures/{entity_slug}-{suffix}.web-snapshot-data.json",
                "citation_label": f"{entity_name} {suffix}",
            }
        )
    return artifacts


def evidence_text_for_entity(entity: dict[str, Any], template_text: str, profile: dict[str, Any]) -> str:
    name = str(entity["name"])
    if entity.get("role") != "client":
        return template_text.format(name=name)
    signals = profile.get("client_signals") if isinstance(profile.get("client_signals"), dict) else {}
    text = template_text.format(name=name)
    if "Meaningful Work" in text or "outcomes" in text:
        return f"{signals.get('mission') or text}"
    if "scheduling" in text or "flexible" in text or "work pattern" in text:
        return f"{signals.get('flexibility_program') or text}"
    if "benefits" in text or "wellbeing" in text:
        benefits = signals.get("benefits") if isinstance(signals.get("benefits"), list) else []
        return f"{name} highlights {', '.join(str(benefit) for benefit in benefits[:3])}."
    if "awards" in text or "recognition" in text:
        awards = signals.get("awards") if isinstance(signals.get("awards"), list) else []
        return f"{name} reinforces employer reputation through {', '.join(str(award) for award in awards[:3])}."
    return text


def survey_signals_from_profile(profile: dict[str, Any], entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    client = next((entity for entity in entities if entity.get("role") == "client"), entities[0])
    project_id = str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-evp-competitor-audit")
    signals = [
        ("great_place_to_work", "Taking everything into account, this is a great place to work.", "Positive", 79, 788, "K", "K5"),
        ("physical_safety", "This is a physically safe place to work.", "Positive", 89, 788, "L", "L2"),
        ("community_contribution", "I feel good about the ways we contribute to the community.", "Positive", 88, 788, "I", "I1"),
        ("fair_pay", "People here are paid fairly for the work they do.", "Positive", 48, 788, "L", "L1"),
        ("manager_decisions", "Management involves people in decisions that affect their jobs.", "Positive", 55, 788, "K", "K3"),
        ("career_growth", "I have opportunities to grow and develop here.", "Positive", 62, 788, "O", "O6"),
        ("work_life_balance", "People are encouraged to balance work and personal life.", "Positive", 64, 788, "L", "L6"),
        ("leadership_visibility", "Leaders communicate a clear direction for the organization.", "Positive", 58, 788, "I", "I4"),
    ]
    return [
        {
            "signal_id": f"survey:{signal_id}",
            "project_id": project_id,
            "entity_id": str(client["entity_id"]),
            "survey_question": question,
            "response_choice": response_choice,
            "percentage": percentage,
            "count": count,
            "pillar_id": pillar_id,
            "factor_id": factor_id,
        }
        for signal_id, question, response_choice, percentage, count, pillar_id, factor_id in signals
    ]


def review_snapshots_from_profile(profile: dict[str, Any], entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project_id = str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-evp-competitor-audit")
    snapshots: list[dict[str, Any]] = []
    for index, entity in enumerate(entities):
        rating_base = 4.2 if entity.get("role") == "client" else 3.8 - (index * 0.1)
        recommend_base = 90 if entity.get("role") == "client" else max(64, 78 - index * 4)
        for source_name, review_count in (("Glassdoor", 7080 - index * 900), ("Indeed", 2694 - index * 80)):
            snapshots.append(
                {
                    "snapshot_id": f"review:{slugify(str(entity['name']))}:{source_name.lower()}",
                    "project_id": project_id,
                    "entity_id": str(entity["entity_id"]),
                    "source_name": source_name,
                    "rating": round(rating_base, 1),
                    "review_count": max(review_count, 250),
                    "recommend_percent": recommend_base if source_name == "Glassdoor" else max(recommend_base - 3, 60),
                    "positive_themes": ["team pride", "meaningful work", "benefits"],
                    "negative_themes": ["pay fairness", "management consistency", "workload"],
                    "captured_at": CREATED_AT,
                }
            )
    return snapshots


def capture_pack_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    project_id = str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-evp-competitor-audit")
    entities = project_profile_entities(profile)
    source_artifacts: list[dict[str, Any]] = []
    excerpts: list[dict[str, Any]] = []
    for entity in entities:
        entity_artifacts = source_artifacts_from_entity(project_id, entity)
        source_artifacts.extend(entity_artifacts)
        careers_artifact = next((artifact for artifact in entity_artifacts if artifact["source_type"] == "careers_page"), entity_artifacts[0])
        culture_artifact = next((artifact for artifact in entity_artifacts if artifact["source_type"] == "culture_page"), careers_artifact)
        benefits_artifact = next((artifact for artifact in entity_artifacts if artifact["source_type"] == "benefits_page"), careers_artifact)
        artifact_by_section = {
            "benefits": benefits_artifact["artifact_id"],
            "creative": culture_artifact["artifact_id"],
            "dei_messaging": culture_artifact["artifact_id"],
            "reviews": next((artifact["artifact_id"] for artifact in entity_artifacts if artifact["source_type"] == "review_site"), careers_artifact["artifact_id"]),
        }
        for section, pillar_id, factor_id, theme_label, text_template in EVIDENCE_THEME_TEMPLATES:
            artifact_id = artifact_by_section.get(section, careers_artifact["artifact_id"])
            excerpts.append(
                {
                    "section": section,
                    "entity_id": str(entity["entity_id"]),
                    "artifact_id": artifact_id,
                    "evidence_text": evidence_text_for_entity(entity, text_template, profile),
                    "pillar_id": pillar_id,
                    "factor_id": factor_id,
                    "theme_label": theme_label,
                    "confidence": "high" if entity.get("role") == "client" else "medium",
                }
            )
    return {
        "project_id": project_id,
        "source_artifacts": source_artifacts,
        "excerpts": excerpts,
        "survey_signals": survey_signals_from_profile(profile, entities),
        "review_snapshots": review_snapshots_from_profile(profile, entities),
    }


def capture_pack(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return capture_pack_from_profile(profile or default_project_profile())



def evidence_matrix(kilos_terms: list[dict[str, Any]]) -> dict[str, Any]:
    return evidence_matrix_from_capture_pack(kilos_terms, capture_pack())


def evidence_matrix_from_capture_pack(
    kilos_terms: list[dict[str, Any]],
    capture_pack_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_id": str(capture_pack_record.get("project_id") or "evp-competitor-audit"),
        "ontology_terms": kilos_terms,
        "evidence_items": evidence_items_from_capture_pack(capture_pack_record),
        "survey_signals": list(capture_pack_record.get("survey_signals") or []),
        "review_snapshots": list(capture_pack_record.get("review_snapshots") or []),
    }



def analysis_pack_from_records(
    project_frame_record: dict[str, Any],
    source_roster_record: dict[str, Any],
    evidence_matrix_record: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = list(evidence_matrix_record.get("evidence_items") or [])
    entities = list(source_roster_record.get("entities") or [])
    project_id = str(project_frame_record.get("project_id") or evidence_matrix_record.get("project_id") or "")
    client = next((entity for entity in entities if entity.get("role") == "client"), entities[0] if entities else {})
    client_id = str(client.get("entity_id") or "")
    findings: list[dict[str, Any]] = []

    def add_finding(entity_id: str, finding_type: str, headline: str, summary: str, supporting_ids: list[str], confidence: str = "medium") -> dict[str, Any]:
        finding = {
            "finding_id": f"finding:{len(findings) + 1:03d}",
            "project_id": project_id,
            "entity_id": entity_id,
            "finding_type": finding_type,
            "headline": headline,
            "summary": summary,
            "supporting_evidence_ids": supporting_ids,
            "confidence": confidence,
        }
        findings.append(finding)
        return finding

    positioning_summaries = []
    for entity in entities:
        entity_id = str(entity.get("entity_id") or "")
        entity_name = str(entity.get("name") or entity_id)
        ids = support_ids(evidence_items, entity_id=entity_id, limit=3)
        summary = f"{entity_name} can support an EVP client immersion and competitor messaging audit with evidence across culture, impact, lifestyle, opportunity, and reputation themes."
        positioning_summaries.append(
            add_finding(entity_id, "positioning", f"{entity_name} employer positioning", summary, ids, "medium")
        )

    market_trend_specs = [
        ("Values-led cultures are the baseline", "K", "K5"),
        ("Impact for people and communities is table stakes", "I", "I1"),
        ("Benefits and wellbeing need concrete proof", "L", "L1"),
        ("Professional growth is a competitive differentiator", "O", "O6"),
    ]
    market_trends = [
        add_finding(client_id, "market_trend", headline, f"The evidence set shows {headline.lower()} across the audited employer set.", support_ids(evidence_items, pillar_id=pillar_id, factor_id=factor_id, limit=4))
        for headline, pillar_id, factor_id in market_trend_specs
    ]

    strength_specs = [
        ("Impact is a clear narrative anchor", "I", "I1"),
        ("Scale and reputation create proof of significance", "I", "I5"),
        ("Flexible work programs can differentiate the offer", "L", "L4"),
        ("Benefits and wellbeing provide strong transactional proof", "L", "L1"),
    ]
    strengths = [
        add_finding(client_id, "strength", headline, f"{str(client.get('name') or 'The client')} has source-backed material for this strength.", support_ids(evidence_items, entity_id=client_id, pillar_id=pillar_id, factor_id=factor_id))
        for headline, pillar_id, factor_id in strength_specs
    ]

    opportunity_specs = [
        ("Add more employee voice and belonging proof", "K", "K5"),
        ("Show structured development and mobility more clearly", "O", "O6"),
        ("Connect review strength to the careers-page story", "K", "K4"),
    ]
    opportunities = [
        add_finding(client_id, "opportunity", headline, f"The report should turn this into a specific recommendation with examples and source receipts.", support_ids(evidence_items, entity_id=client_id, pillar_id=pillar_id, factor_id=factor_id))
        for headline, pillar_id, factor_id in opportunity_specs
    ]

    risk_specs = [
        ("Thin inclusion proof can weaken emotional resonance", "K", "K1"),
        ("Transactional benefits language can crowd out culture", "L", "L1"),
        ("Reputation claims need visible candidate-facing receipts", "S", "S2"),
    ]
    risks = [
        add_finding(client_id, "gap", headline, f"The report should flag this as a watch item when source evidence is shallow or inconsistent.", support_ids(evidence_items, entity_id=client_id, pillar_id=pillar_id, factor_id=factor_id), "medium")
        for headline, pillar_id, factor_id in risk_specs
    ]

    return {
        "project_id": project_id,
        "report_outline": project_frame_record.get("report_outline") or report_outline(),
        "positioning_summaries": positioning_summaries,
        "market_trends": market_trends,
        "strengths": strengths,
        "opportunities": opportunities,
        "risks": risks,
        "findings": findings,
    }


def analysis_pack() -> dict[str, Any]:
    frame = project_frame()
    roster = source_roster()
    matrix = evidence_matrix(load_kilos_terms())
    return analysis_pack_from_records(frame, roster, matrix)



def entity_names_by_id(source_roster_record: dict[str, Any]) -> dict[str, str]:
    return {
        str(entity.get("entity_id") or ""): str(entity.get("name") or entity.get("entity_id") or "")
        for entity in source_roster_record.get("entities") or []
        if isinstance(entity, dict)
    }



def report_docx_body(
    project_frame_record: dict[str, Any],
    source_roster_record: dict[str, Any],
    evidence_matrix_record: dict[str, Any],
    analysis_pack_record: dict[str, Any],
) -> str:
    client_name = escape(str(project_frame_record.get("client_name") or "Client"))
    sections = project_frame_record.get("report_outline", {}).get("sections", [])
    section_rows = table_rows([[str(section.get("title") or ""), str(section.get("expected_layout") or "")] for section in sections])
    trend_items = "\n".join(f"        <li>{escape(str(finding.get('headline') or ''))}</li>" for finding in analysis_pack_record.get("market_trends") or [])
    strength_items = "\n".join(f"        <li>{escape(str(finding.get('headline') or ''))}</li>" for finding in analysis_pack_record.get("strengths") or [])
    opportunity_items = "\n".join(f"        <li>{escape(str(finding.get('headline') or ''))}</li>" for finding in analysis_pack_record.get("opportunities") or [])
    review_count = len(evidence_matrix_record.get("review_snapshots") or [])
    survey_count = len(evidence_matrix_record.get("survey_signals") or [])
    evidence_count = len(evidence_matrix_record.get("evidence_items") or [])
    entity_names = ", ".join(escape(str(entity.get("name") or "")) for entity in source_roster_record.get("entities") or [])
    return f"""    <section>
      <h2>Reusable report structure</h2>
      <p>{client_name} uses the same minimum report arc as the reference: introduction, methodology, client immersion, competitor messaging audit, KILOS positioning, market trends, strengths, opportunities, risks, and appendices.</p>
      <table>
        <tr><th>Section</th><th>Layout</th></tr>
{section_rows}
      </table>
    </section>
    <section>
      <h2>Client Data Immersion</h2>
      <p>Entities covered: {entity_names}. The data pack contains {evidence_count} evidence items, {survey_count} survey signals, and {review_count} review snapshots.</p>
    </section>
    <section>
      <h2>Market Trends Analysis</h2>
      <ul>
{trend_items}
      </ul>
    </section>
    <section>
      <h2>Strengths and Opportunities</h2>
      <h3>Strengths</h3>
      <ul>
{strength_items}
      </ul>
      <h3>Opportunities</h3>
      <ul>
{opportunity_items}
      </ul>
    </section>
"""


def audit_deck_body(
    project_frame_record: dict[str, Any],
    source_roster_record: dict[str, Any],
    evidence_matrix_record: dict[str, Any],
    analysis_pack_record: dict[str, Any],
) -> str:
    names_by_id = entity_names_by_id(source_roster_record)
    rows = table_rows(
        [
            [
                names_by_id.get(str(finding.get("entity_id") or ""), str(finding.get("entity_id") or "")),
                str(finding.get("finding_type") or ""),
                str(finding.get("headline") or ""),
            ]
            for finding in (analysis_pack_record.get("positioning_summaries") or [])[:4]
        ]
    )
    return f"""    <section>
      <h2>Executive summary slide</h2>
      <p>{escape(str(project_frame_record.get("client_name") or "Client"))} has a profile-ready evidence set for report, deck, workbook, and L4 publication views.</p>
    </section>
    <section>
      <h2>Comparison table slide</h2>
      <table>
        <tr><th>Entity</th><th>Finding type</th><th>Headline</th></tr>
{rows}
      </table>
    </section>
"""


def data_workbook_body(
    project_frame_record: dict[str, Any],
    source_roster_record: dict[str, Any],
    evidence_matrix_record: dict[str, Any],
    analysis_pack_record: dict[str, Any],
) -> str:
    names_by_id = entity_names_by_id(source_roster_record)
    rows = table_rows(
        [
            [
                names_by_id.get(str(item.get("entity_id") or ""), str(item.get("entity_id") or "")),
                f"{item.get('pillar_id')}{item.get('factor_id')}",
                str(item.get("evidence_text") or ""),
            ]
            for item in (evidence_matrix_record.get("evidence_items") or [])[:20]
        ]
    )
    return f"""    <section>
      <h2>Evidence matrix view</h2>
      <table>
        <tr><th>Entity</th><th>KILOS</th><th>Evidence</th></tr>
{rows}
      </table>
    </section>
"""


def l4_publication_body(
    project_frame_record: dict[str, Any],
    source_roster_record: dict[str, Any],
    evidence_matrix_record: dict[str, Any],
    analysis_pack_record: dict[str, Any],
) -> str:
    recommendation = next(iter(analysis_pack_record.get("opportunities") or []), {})
    return f"""    <section>
      <h2>Publication readout</h2>
      <p>The L4 view is a rendered projection over the capture pack, evidence matrix, and analysis pack for {escape(str(project_frame_record.get("client_name") or "Client"))}.</p>
    </section>
    <section>
      <h2>Evidence-backed recommendation</h2>
      <p>{escape(str(recommendation.get("headline") or "Use source-backed evidence to sharpen the employer value proposition."))}</p>
    </section>
"""


def build_manifest(project_frame_record: dict[str, Any] | None = None, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    project_frame_record = project_frame_record or project_frame()
    profile = profile or default_project_profile()
    client_name = str(project_frame_record.get("client_name") or profile.get("client_name") or "Client")
    domain = str(profile.get("domain") or f"{slugify(client_name)}.example")
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"publication-pipeline-{slugify(client_name)}-evp-audit",
        "company": client_name,
        "domain": domain,
        "template_id": PIPELINE_TEMPLATE_ID,
        "talent_segment": str(project_frame_record.get("audience") or "Clinical and technical talent"),
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": PIPELINE_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the operator request and review requirements.", ["p0-pipeline-intake"], []),
            manifest_step("p0-project-frame", 0, "Project frame", "Define the publication target and milestone scope.", ["p0-project-frame"], ["p0-pipeline-intake"]),
            manifest_step("p0-source-roster", 0, "Source roster", "List client and competitor sources.", ["p0-source-roster"], ["p0-project-frame"]),
            manifest_step("p1-capture-pack", 1, "Capture pack", "Stage source captures and excerpts.", ["p1-capture-pack"], ["p0-source-roster"]),
            manifest_step("p2-evidence-matrix", 2, "Evidence matrix", "Normalize evidence into KILOS-tagged records.", ["p2-evidence-matrix"], ["p1-capture-pack"]),
            manifest_step("p3-analysis-pack", 3, "Analysis pack", "Derive strengths, gaps, trends, and opportunities.", ["p3-analysis-pack"], ["p2-evidence-matrix"]),
            manifest_step("p4-report-docx-view", 4, "Report DOCX view", "Render the report view.", ["p4-report-docx"], ["p3-analysis-pack"]),
            manifest_step("p4-audit-deck-view", 4, "Audit deck view", "Render the companion audit deck view.", ["p4-audit-deck"], ["p3-analysis-pack"]),
            manifest_step("p4-data-workbook-view", 4, "Data workbook view", "Render the evidence workbook view.", ["p4-data-workbook"], ["p2-evidence-matrix"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the final publication surface.", ["p4-l4-publication"], ["p3-analysis-pack"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "Operator-facing pipeline intake"),
            manifest_artifact("p0-project-frame", 0, "publication_project", "p0-project-frame", ["p0-pipeline-intake"], "project-frame.json", "publication.project", "Publication project frame"),
            manifest_artifact("p0-source-roster", 0, "source_roster", "p0-source-roster", ["p0-project-frame"], "source-roster.json", "publication.source_roster", "Client and competitor source roster"),
            manifest_artifact("p1-capture-pack", 1, "capture_pack", "p1-capture-pack", ["p0-source-roster"], "capture-pack.json", "publication.capture_pack", "Capture pack with source artifacts and excerpts"),
            manifest_artifact("p2-evidence-matrix", 2, "evidence_matrix", "p2-evidence-matrix", ["p1-capture-pack"], "evidence-matrix.json", "publication.evidence_matrix", "KILOS-normalized evidence matrix"),
            manifest_artifact("p3-analysis-pack", 3, "analysis_pack", "p3-analysis-pack", ["p2-evidence-matrix"], "analysis-pack.json", "publication.analysis_pack", "Evidence-backed analysis findings"),
            manifest_artifact("p4-report-docx", 4, "report_docx", "p4-report-docx-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "report-docx-view.html", "publication.report_docx", "EVP audit report view", composite_group=publication_composite_group("report_docx")),
            manifest_artifact("p4-audit-deck", 4, "audit_deck", "p4-audit-deck-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "audit-deck-view.html", "publication.audit_deck", "Companion audit deck view", composite_group=publication_composite_group("audit_deck")),
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p2-evidence-matrix", "p1-capture-pack"], "data-workbook-view.html", "publication.data_workbook", "Evidence workbook view", composite_group=publication_composite_group("data_workbook")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "l4-publication.html", "publication.l4_publication", "Final L4 publication view", composite_group=publication_composite_group("l4_publication")),
        ],
    }



def generate_publication_pipeline_fixture(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
    url_stage_manifest_path: Path | None = None,
    url_stage_manifest_paths: list[Path] | None = None,
    url_stage_entity_ids: list[str] | None = None,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, DEFAULT_OUTPUT_DIR),
    )

    kilos_terms = load_kilos_terms()
    profile = load_project_profile(project_profile_path)
    project_frame_record = project_frame(profile)
    capture_pack_record = capture_pack(profile)
    source_roster_record = source_roster(profile)
    manifest_paths: list[Path] = []
    if url_stage_manifest_path is not None:
        manifest_paths.append(url_stage_manifest_path)
    if url_stage_manifest_paths:
        manifest_paths.extend(url_stage_manifest_paths)
    intake_record = pipeline_intake_from_profile(profile, url_stage_manifest_paths=manifest_paths)
    if manifest_paths:
        capture_pack_record = capture_pack_from_url_stage_manifests(
            [json.loads(path.read_text(encoding="utf-8")) for path in manifest_paths],
            project_id=str(project_frame_record["project_id"]),
            entity_ids=url_stage_entity_ids,
        )
        source_roster_record = source_roster_from_capture_pack(capture_pack_record)
    evidence_matrix_record = evidence_matrix_from_capture_pack(kilos_terms, capture_pack_record)
    analysis_pack_record = analysis_pack_from_records(project_frame_record, source_roster_record, evidence_matrix_record)
    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "project-frame.json", project_frame_record)
    write_json(output_dir / "source-roster.json", source_roster_record)
    write_json(output_dir / "capture-pack.json", capture_pack_record)
    write_json(output_dir / "evidence-matrix.json", evidence_matrix_record)
    write_json(output_dir / "analysis-pack.json", analysis_pack_record)
    write_text(output_dir / "report-docx-view.html", render_publication_html("Report DOCX View", report_docx_body(project_frame_record, source_roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "audit-deck-view.html", render_publication_html("Audit Deck View", audit_deck_body(project_frame_record, source_roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "data-workbook-view.html", render_publication_html("Data Workbook View", data_workbook_body(project_frame_record, source_roster_record, evidence_matrix_record, analysis_pack_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("L4 Publication", l4_publication_body(project_frame_record, source_roster_record, evidence_matrix_record, analysis_pack_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_manifest(project_frame_record, profile))
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will receive manifest.json and publication fixture artifacts.",
    )
    parser.add_argument(
        "--url-stage-manifest",
        type=Path,
        action="append",
        help="Optional URL-stage manifest to import as the publication capture pack source.",
    )
    parser.add_argument(
        "--project-profile",
        type=Path,
        help="Optional JSON project profile for generating the EVP audit data shape for another company.",
    )
    parser.add_argument(
        "--url-stage-entity-id",
        action="append",
        help="Entity ID for the corresponding --url-stage-manifest. Provide once per manifest when used.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = generate_publication_pipeline_fixture(
        args.output_dir,
        project_profile_path=args.project_profile,
        url_stage_manifest_paths=args.url_stage_manifest,
        url_stage_entity_ids=args.url_stage_entity_id,
    )
    payload = {
        "status": "passed",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
    }
    if args.url_stage_manifest:
        payload["url_stage_manifests"] = [str(path) for path in args.url_stage_manifest]
        if len(args.url_stage_manifest) == 1:
            payload["url_stage_manifest"] = str(args.url_stage_manifest[0])
    if args.project_profile is not None:
        payload["project_profile"] = str(args.project_profile)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"manifest={payload['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["PIPELINE_TEMPLATE_ID", "generate_publication_pipeline_fixture", "main"]
