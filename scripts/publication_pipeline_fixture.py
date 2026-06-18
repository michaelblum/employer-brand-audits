#!/usr/bin/env python3
"""Generate a deterministic publication pipeline fixture."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "publication-pipeline" / "latest"
KILOS_PATH = REPO_ROOT / "data" / "kilos-framework.json"
DEFAULT_REFERENCE_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "northside-healthcare-evp-2025.json"
PIPELINE_TEMPLATE_ID = "publication-pipeline.evp-client-immersion-competitor-audit"
PIPELINE_KEY = "evp-client-immersion-competitor-audit"
PIPELINE_LABEL = "EVP Client Data Immersion and Competitor Messaging Audit"
SEGMENT_TVP_TEMPLATE_ID = "publication-pipeline.segment-tvp-audit"
SEGMENT_TVP_KEY = "segment-tvp-audit"
SEGMENT_TVP_LABEL = "Segment-Specific Talent Value Proposition Audit"
SEGMENT_TVP_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "adt-tech-product-tvp-2025.json"
COMPETITOR_WORKBOOK_TEMPLATE_ID = "publication-pipeline.competitor-messaging-workbook"
COMPETITOR_WORKBOOK_KEY = "competitor-messaging-workbook"
COMPETITOR_WORKBOOK_LABEL = "Competitor Messaging Workbook"
COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "harbourvest-competitor-messaging-workbook-2025.json"
CREATED_AT = "2026-06-18T12:00:00Z"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_kilos_terms(path: Path = KILOS_PATH) -> list[dict[str, Any]]:
    framework = json.loads(path.read_text(encoding="utf-8"))
    terms: list[dict[str, Any]] = []
    for pillar in framework["pillars"]:
        for factor in pillar["factors"]:
            terms.append(
                {
                    "framework_id": framework["framework"],
                    "framework_version": framework["version"],
                    "pillar_id": pillar["id"],
                    "pillar_name": pillar["name"],
                    "pillar_color": pillar["color"],
                    "factor_id": factor["id"],
                    "factor_name": factor["name"],
                    "theme_label": f"{pillar['name']} / {factor['name']}",
                    "aliases": factor.get("survey_labels", []),
                    "description": factor["description"],
                }
            )
    return terms


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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def source_urls_from_entity(entity: dict[str, Any]) -> dict[str, Any]:
    source_urls = empty_source_urls()
    raw = entity.get("source_urls")
    if isinstance(raw, dict):
        source_urls.update(
            {
                "careers_url": str(raw.get("careers_url") or ""),
                "culture_url": str(raw.get("culture_url") or ""),
                "dei_url": str(raw.get("dei_url") or ""),
                "review_urls": list(raw.get("review_urls") or []),
                "other_urls": list(raw.get("other_urls") or []),
            }
        )
        return source_urls
    entity_slug = slugify(str(entity.get("name") or entity.get("entity_id") or "source"))
    source_urls["careers_url"] = str(entity.get("careers_url") or f"https://{entity_slug}.example/careers")
    source_urls["culture_url"] = str(entity.get("culture_url") or f"https://{entity_slug}.example/culture")
    source_urls["dei_url"] = str(entity.get("dei_url") or "")
    source_urls["review_urls"] = list(entity.get("review_urls") or [f"https://reviews.example/{entity_slug}"])
    source_urls["other_urls"] = list(entity.get("other_urls") or [])
    return source_urls


def generic_project_profile_defaults(profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(profile.get("client_name") or "Client")
    client_slug = slugify(client_name)
    return {
        "project_id": f"{client_slug}-evp-competitor-audit",
        "client_name": client_name,
        "client_full_name": client_name,
        "industry": "Unspecified",
        "geography": "United States",
        "audience": "Employer brand target talent",
        "report_title": f"{client_name} EVP Client Data Immersion and Competitor Messaging Audit",
        "report_date": "2026-06-18",
        "domain": f"{client_slug}.example",
        "client_signals": {},
        "competitors": [],
    }


def normalize_project_profile(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = generic_project_profile_defaults(profile)
    normalized.update(profile)
    if "client_full_name" not in profile:
        normalized["client_full_name"] = normalized.get("client_name")
    normalized["competitors"] = list(normalized.get("competitors") or [])
    return normalized


def default_project_profile() -> dict[str, Any]:
    return load_project_profile(DEFAULT_REFERENCE_PROFILE_PATH)


def load_project_profile(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = DEFAULT_REFERENCE_PROFILE_PATH
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("project profile must be a JSON object")
    return normalize_project_profile(profile)


def project_profile_entities(profile: dict[str, Any]) -> list[dict[str, Any]]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    client_slug = slugify(client_name)
    client_entity = {
        "entity_id": str(profile.get("client_entity_id") or f"client-{client_slug}"),
        "name": client_name,
        "role": "client",
        "careers_url": str(profile.get("careers_url") or f"https://{slugify(str(profile.get('client_name') or client_name))}.example/careers"),
        "culture_url": str(profile.get("culture_url") or f"https://{slugify(str(profile.get('client_name') or client_name))}.example/culture"),
        "dei_url": str(profile.get("dei_url") or f"https://{slugify(str(profile.get('client_name') or client_name))}.example/diversity"),
        "review_urls": list(profile.get("review_urls") or [f"https://reviews.example/{slugify(str(profile.get('client_name') or client_name))}"]),
    }
    competitors = []
    for index, competitor in enumerate(profile.get("competitors") or [], start=1):
        if not isinstance(competitor, dict):
            continue
        name = str(competitor.get("name") or f"Competitor {index}")
        competitors.append(
            {
                "entity_id": str(competitor.get("entity_id") or f"competitor-{slugify(name)}"),
                "name": name,
                "role": "competitor",
                **{key: value for key, value in competitor.items() if key not in {"entity_id", "name", "role"}},
            }
        )
    return [client_entity, *competitors[:3]]


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


def entity_role_from_id(entity_id: str) -> str:
    if entity_id.startswith("client-"):
        return "client"
    if entity_id.startswith("competitor-"):
        return "competitor"
    return "source"


def entity_name_from_id(entity_id: str) -> str:
    parts = entity_id.split("-", 1)
    name = parts[1] if len(parts) == 2 and parts[0] in {"client", "competitor", "source"} else entity_id
    return name.replace("-", " ").title()


def empty_source_urls() -> dict[str, Any]:
    return {
        "careers_url": "",
        "culture_url": "",
        "dei_url": "",
        "review_urls": [],
        "other_urls": [],
    }


def add_source_url(source_urls: dict[str, Any], source_url: str, source_type: str) -> None:
    if not source_url:
        return
    if source_type == "review":
        if source_url not in source_urls["review_urls"]:
            source_urls["review_urls"].append(source_url)
        return
    if source_type in {"culture_page", "culture"} and not source_urls["culture_url"]:
        source_urls["culture_url"] = source_url
        return
    if source_type in {"dei_page", "dei"} and not source_urls["dei_url"]:
        source_urls["dei_url"] = source_url
        return
    if not source_urls["careers_url"]:
        source_urls["careers_url"] = source_url
        return
    if source_url != source_urls["careers_url"] and source_url not in source_urls["other_urls"]:
        source_urls["other_urls"].append(source_url)


def source_roster_from_capture_pack(capture_pack_record: dict[str, Any]) -> dict[str, Any]:
    entities_by_id: dict[str, dict[str, Any]] = {}
    for artifact in capture_pack_record.get("source_artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        entity_id = str(artifact.get("entity_id") or "")
        if not entity_id:
            continue
        entity = entities_by_id.setdefault(
            entity_id,
            {
                "entity_id": entity_id,
                "name": entity_name_from_id(entity_id),
                "role": entity_role_from_id(entity_id),
                "source_urls": empty_source_urls(),
            },
        )
        add_source_url(
            entity["source_urls"],
            str(artifact.get("source_url") or ""),
            str(artifact.get("source_type") or "careers_page"),
        )
    return {
        "project_id": str(capture_pack_record.get("project_id") or "url-stage-capture-pack"),
        "entities": list(entities_by_id.values()),
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


def source_artifacts_from_url_stage_manifest(
    manifest: dict[str, Any],
    *,
    project_id: str,
    entity_id: str,
) -> list[dict[str, Any]]:
    slug = str(manifest.get("slug") or "source")
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    return [
        {
            "artifact_id": f"source:{slug}",
            "project_id": project_id,
            "entity_id": entity_id,
            "source_url": str(manifest.get("url") or ""),
            "source_type": "careers_page",
            "captured_at": str(manifest.get("captured_at") or ""),
            "text_path": str(artifacts.get("visible_text") or ""),
            "screenshot_path": str(artifacts.get("page_screenshot") or ""),
            "snapshot_path": str(artifacts.get("web_snapshot_data") or artifacts.get("web_snapshot") or ""),
            "citation_label": slug.replace("-", " ").title(),
        }
    ]


def capture_pack_from_url_stage_manifest(
    manifest: dict[str, Any],
    *,
    project_id: str = "url-stage-capture-pack",
    entity_id: str = "source-client",
) -> dict[str, Any]:
    return capture_pack_from_url_stage_manifests(
        [manifest],
        project_id=project_id,
        entity_ids=[entity_id],
    )


def inferred_entity_id_from_url_stage_manifest(manifest: dict[str, Any], index: int) -> str:
    slug = str(manifest.get("slug") or "")
    for suffix in ("-careers-live", "-careers-page", "-careers", "-live", "-page"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    if not slug:
        slug = f"entity-{index + 1}"
    return f"source-{slug}"


def url_stage_entity_id(index: int, manifest: dict[str, Any], entity_ids: list[str] | None) -> str:
    if entity_ids is not None and index < len(entity_ids):
        return entity_ids[index]
    return inferred_entity_id_from_url_stage_manifest(manifest, index)


def capture_pack_from_url_stage_manifests(
    manifests: list[dict[str, Any]],
    *,
    project_id: str = "url-stage-capture-pack",
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    if entity_ids is not None and len(entity_ids) not in (0, len(manifests)):
        raise ValueError("--url-stage-entity-id must be provided once per --url-stage-manifest")
    source_artifacts: list[dict[str, Any]] = []
    excerpts: list[dict[str, Any]] = []
    for index, manifest in enumerate(manifests):
        entity_id = url_stage_entity_id(index, manifest, entity_ids)
        imported_artifacts = source_artifacts_from_url_stage_manifest(
            manifest,
            project_id=project_id,
            entity_id=entity_id,
        )
        source_artifacts.extend(imported_artifacts)
        source_artifact = imported_artifacts[0]
        excerpts.append(
            {
                "section": "notes",
                "entity_id": entity_id,
                "artifact_id": source_artifact["artifact_id"],
                "evidence_text": f"URL-stage capture imported from {source_artifact['source_url']}",
                "pillar_id": "",
                "factor_id": "",
                "theme_label": "url-stage capture context",
                "confidence": "medium",
                "evidence_type": "note",
            }
        )
    return {
        "project_id": project_id,
        "source_artifacts": source_artifacts,
        "excerpts": excerpts,
    }


def evidence_items_from_capture_pack(capture_pack_record: dict[str, Any]) -> list[dict[str, Any]]:
    source_artifacts = capture_pack_record.get("source_artifacts")
    if not isinstance(source_artifacts, list):
        source_artifacts = []
    artifacts_by_id = {
        str(artifact.get("artifact_id")): artifact
        for artifact in source_artifacts
        if isinstance(artifact, dict) and artifact.get("artifact_id")
    }
    default_artifact = source_artifacts[0] if source_artifacts and isinstance(source_artifacts[0], dict) else {}
    evidence_items = []
    for index, excerpt in enumerate(capture_pack_record.get("excerpts") or [], start=1):
        if not isinstance(excerpt, dict):
            continue
        artifact = artifacts_by_id.get(str(excerpt.get("artifact_id") or ""), default_artifact)
        pillar_id = str(excerpt.get("pillar_id") or "")
        factor_id = str(excerpt.get("factor_id") or "")
        evidence_items.append(
            {
                "evidence_id": f"evidence:{index:03d}",
                "project_id": str(artifact.get("project_id") or capture_pack_record.get("project_id") or ""),
                "entity_id": str(excerpt.get("entity_id") or artifact.get("entity_id") or ""),
                "artifact_id": str(excerpt.get("artifact_id") or artifact.get("artifact_id") or ""),
                "section": str(excerpt.get("section") or "notes"),
                "pillar_id": pillar_id,
                "factor_id": factor_id,
                "theme_label": str(excerpt.get("theme_label") or ""),
                "evidence_type": str(excerpt.get("evidence_type") or "quote"),
                "evidence_text": str(excerpt.get("evidence_text") or ""),
                "source_url": str(excerpt.get("source_url") or artifact.get("source_url") or ""),
                "confidence": str(excerpt.get("confidence") or "medium"),
                "reviewer_notes": str(excerpt.get("reviewer_notes") or ""),
                "kilos_status": "kilos_mapped" if pillar_id and factor_id else "non_kilos_context",
            }
        )
    return evidence_items


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


def support_ids(
    evidence_items: list[dict[str, Any]],
    *,
    entity_id: str | None = None,
    pillar_id: str | None = None,
    factor_id: str | None = None,
    limit: int = 3,
) -> list[str]:
    ids = []
    for item in evidence_items:
        if entity_id is not None and item.get("entity_id") != entity_id:
            continue
        if pillar_id is not None and item.get("pillar_id") != pillar_id:
            continue
        if factor_id is not None and item.get("factor_id") != factor_id:
            continue
        ids.append(str(item["evidence_id"]))
        if len(ids) == limit:
            break
    if ids:
        return ids
    return [str(item["evidence_id"]) for item in evidence_items[:limit]]


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


def render_publication_html(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin: 0; color: #17202a; font-family: Arial, Helvetica, sans-serif; line-height: 1.5; background: #f5f7fa; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 40px 24px 72px; }}
    h1 {{ margin: 0 0 16px; font-size: 34px; }}
    section {{ margin: 22px 0; padding: 22px; border: 1px solid #ccd5df; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #d7dee7; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    .tag {{ display: inline-block; padding: 2px 8px; border: 1px solid #8aa0b8; background: #f5f8fb; font-size: 12px; font-weight: 700; }}
  </style>
</head>
<body>
  <main data-publication-pipeline-view="true">
    <h1>{title}</h1>
{body}
  </main>
</body>
</html>
"""


def entity_names_by_id(source_roster_record: dict[str, Any]) -> dict[str, str]:
    return {
        str(entity.get("entity_id") or ""): str(entity.get("name") or entity.get("entity_id") or "")
        for entity in source_roster_record.get("entities") or []
        if isinstance(entity, dict)
    }


def table_rows(cells: list[list[str]]) -> str:
    return "\n".join(
        "        <tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in cells
    )


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


def manifest_step(
    step_id: str,
    layer: int,
    name: str,
    description: str,
    artifact_ids: list[str],
    parent_step_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": step_id,
        "layer": layer,
        "name": name,
        "description": description,
        "status": "complete",
        "started_at": CREATED_AT,
        "completed_at": CREATED_AT,
        "required_inputs": [],
        "artifact_ids": artifact_ids,
        "parent_step_ids": parent_step_ids,
    }


def manifest_artifact(
    artifact_id: str,
    layer: int,
    artifact_type: str,
    produced_by_step_id: str,
    parent_ids: list[str],
    file_path: str,
    slot: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "layer": layer,
        "type": artifact_type,
        "status": "complete",
        "created_at": CREATED_AT,
        "produced_by_step_id": produced_by_step_id,
        "parent_ids": parent_ids,
        "file_path": file_path,
        "params": {"slot": slot},
        "card": {
            "summary": summary,
            "tags": {"layer": f"P{layer}", "slot": slot},
        },
    }


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
            manifest_artifact("p4-report-docx", 4, "report_docx", "p4-report-docx-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "report-docx-view.html", "publication.report_docx", "EVP audit report view"),
            manifest_artifact("p4-audit-deck", 4, "audit_deck", "p4-audit-deck-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "audit-deck-view.html", "publication.audit_deck", "Companion audit deck view"),
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p2-evidence-matrix", "p1-capture-pack"], "data-workbook-view.html", "publication.data_workbook", "Evidence workbook view"),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"], "l4-publication.html", "publication.l4_publication", "Final L4 publication view"),
        ],
    }


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
            manifest_artifact("p4-report-docx", 4, "report_docx", "p4-report-docx-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "report-docx-view.html", "publication.report_docx", "Segment TVP report view"),
            manifest_artifact("p4-brand-strategy-deck", 4, "brand_strategy_deck", "p4-brand-strategy-deck-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "brand-strategy-deck-view.html", "publication.brand_strategy_deck", "Brand strategy deck view"),
            manifest_artifact("p4-social-platform-audit", 4, "social_platform_audit", "p4-social-platform-audit-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "social-platform-audit-view.html", "publication.social_platform_audit", "Social platform audit view"),
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p2-segment-evidence-matrix", "p1-segment-capture-pack"], "data-workbook-view.html", "publication.data_workbook", "Segment evidence workbook view"),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-tvp-analysis-pack", "p2-segment-evidence-matrix", "p1-segment-capture-pack"], "l4-publication.html", "publication.l4_publication", "Segment TVP L4 readout"),
        ],
    }


def generate_segment_tvp_audit_fixture(
    output_dir: Path = REPO_ROOT / "artifacts" / "segment-tvp-audit" / "latest",
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
            manifest_artifact("p4-data-workbook", 4, "data_workbook", "p4-data-workbook-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-workbook-extraction"], "data-workbook-view.html", "publication.data_workbook", "Workbook explorer view"),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-analysis-pack", "p2-evidence-matrix", "p1-workbook-extraction"], "l4-publication.html", "publication.l4_publication", "Workbook L4 readout"),
        ],
    }


def generate_competitor_messaging_workbook_fixture(
    output_dir: Path = REPO_ROOT / "artifacts" / "competitor-messaging-workbook" / "latest",
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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


def generate_publication_pipeline_fixture(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
    url_stage_manifest_path: Path | None = None,
    url_stage_manifest_paths: list[Path] | None = None,
    url_stage_entity_ids: list[str] | None = None,
) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
