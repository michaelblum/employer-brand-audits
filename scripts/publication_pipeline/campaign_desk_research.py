#!/usr/bin/env python3
"""Campaign desk research and competitor audit publication archetype."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .core import (
    CAMPAIGN_DESK_RESEARCH_DEFAULT_PROFILE_PATH,
    CAMPAIGN_DESK_RESEARCH_KEY,
    CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID,
    CREATED_AT,
    REPO_ROOT,
    is_default_output_dir,
    load_project_profile,
    manifest_artifact,
    manifest_step,
    prepare_output_dir,
    project_profile_entities,
    render_publication_html,
    slugify,
    source_urls_from_entity,
    write_json,
    write_text,
)
from .projection_groups import publication_composite_group
from .segment_tvp import segment_tvp_table_body


CAMPAIGN_DESK_RESEARCH_OUTPUT_DIR = REPO_ROOT / "artifacts" / "campaign-desk-research-comp-audit" / "latest"


def load_campaign_profile(path: Path | None = None) -> dict[str, Any]:
    profile = load_project_profile(path or CAMPAIGN_DESK_RESEARCH_DEFAULT_PROFILE_PATH)
    profile.setdefault("campaign_goal", "Increase representation and applications from women in engineering")
    profile.setdefault("target_population", "Women in engineering and energy roles")
    profile.setdefault("channel_scope", ["careers site", "paid social", "organic social", "events", "partnerships"])
    profile.setdefault("geography_scope", "United Kingdom")
    return profile


def campaign_intake(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID,
        "pipeline_key": CAMPAIGN_DESK_RESEARCH_KEY,
        "client": {
            "name": str(profile.get("client_full_name") or profile.get("client_name") or "Client"),
            "sector": str(profile.get("industry") or "Energy"),
            "geography": str(profile.get("geography") or "United Kingdom"),
            "domain": str(profile.get("domain") or f"{slugify(str(profile.get('client_name') or 'client'))}.example"),
            "audience": str(profile.get("audience") or profile.get("target_population") or "Target talent"),
        },
        "objective": "Build a desk-research-backed DEI campaign recommendation from labor context, competitor cases, and channel tactics.",
        "campaign_goal": str(profile.get("campaign_goal") or ""),
        "target_population": str(profile.get("target_population") or ""),
        "labor_market_sources": ["global_uk_gender", "energy_engineering", "dei_practice"],
        "campaign_case_sources": "competitor and comparator campaign cases",
        "channel_scope": list(profile.get("channel_scope") or []),
        "geography_scope": str(profile.get("geography_scope") or profile.get("geography") or ""),
        "desired_outputs": ["desk_research_evidence_pack", "campaign_case_matrix", "channel_tactic_opportunity_map", "campaign_recommendation_readout", "l4_publication"],
        "review_requirements": {"manual_review_gates": ["source authority", "case relevance", "channel feasibility", "recommendation evidence lineage"]},
    }


def campaign_research_sources(profile: dict[str, Any]) -> dict[str, Any]:
    groups = {
        "global_uk_gender": ["ONS", "OECD", "United Nations", "PwC Women in Work", "McKinsey Diversity Matters", "WEF Global Gender Gap", "Oxera"],
        "energy_engineering": ["Energy & Utility Skills", "Royal Academy of Engineering", "EngineeringUK", "IET"],
        "dei_practice": ["Women's Engineering Society", "Great Place to Work", "POWERful Women", "UN Women"],
    }
    sources = []
    for group, names in groups.items():
        for name in names:
            sources.append(
                {
                    "source_id": f"source:{slugify(name)}",
                    "source_name": name,
                    "source_group": group,
                    "source_kind": "desk_research",
                    "authority_tier": "primary" if group != "dei_practice" else "practice",
                    "geography": str(profile.get("geography_scope") or "United Kingdom"),
                    "topic_tags": ["gender", "energy", "campaign"],
                    "citation_url": f"https://sources.example/{slugify(name)}",
                    "deck_slide_refs": [3 + len(sources) % 14],
                    "evidence_uses": ["labor_market_stat", "policy_or_context_signal"],
                }
            )
    return {
        "project_id": str(profile.get("project_id") or ""),
        "source_group_counts": {key: len(value) for key, value in groups.items()},
        "desk_research_sources": sources,
    }


def campaign_evidence_pack(profile: dict[str, Any], sources_record: dict[str, Any]) -> dict[str, Any]:
    sources = list(sources_record.get("desk_research_sources") or [])
    stats = [
        {
            "stat_id": f"stat:{index + 1:03d}",
            "source_id": source["source_id"],
            "headline": f"{source['source_name']} labor market signal",
            "value": f"{42 + index}%",
            "topic": source["source_group"],
            "deck_slide_refs": source["deck_slide_refs"],
        }
        for index, source in enumerate(sources[:10])
    ]
    signals = [
        {
            "signal_id": f"signal:{index + 1:03d}",
            "source_id": source["source_id"],
            "headline": f"{source['source_name']} context signal",
            "summary": "Policy, practice, or business-case context for campaign planning.",
            "deck_slide_refs": source["deck_slide_refs"],
        }
        for index, source in enumerate(sources[10:])
    ]
    return {
        "project_id": str(profile.get("project_id") or ""),
        "slide_count": 49,
        "section_ranges": [
            "1-2",
            "3-8",
            "9-16",
            "17-22",
            "23-27",
            "28-42",
            "43-48",
            "49",
        ],
        "labor_market_stats": stats,
        "policy_or_context_signals": signals,
    }


def campaign_case_matrix(profile: dict[str, Any]) -> dict[str, Any]:
    names = ["BT", "National Grid", "SSEN", "SSE", "EDF", "E.ON", "bp", "Entain x McLaren", "McLaren", "JLR", "Network Rail", "ScotRail"]
    cases = [
        {
            "case_id": f"case:{slugify(name)}",
            "organization": name,
            "campaign_name": f"{name} inclusive talent campaign",
            "target_population": str(profile.get("target_population") or "Women in engineering"),
            "role_family": "engineering",
            "goal": str(profile.get("campaign_goal") or "increase applications"),
            "barrier_or_insight": "Representation, awareness, and confidence barriers",
            "creative_strategy": "employee storytelling and proof-led creative",
            "channels": ["careers_site", "paid_social", "events"],
            "tactics": ["hero_video", "employee_story", "partner_amplification"],
            "partner_orgs": ["industry network"],
            "launch_moment": "campaign burst",
            "proof_metrics": ["applications", "engagement"],
            "source_ids": [f"source:{index + 1:03d}"],
            "lessons": ["make barriers visible", "show role models"],
        }
        for index, name in enumerate(names)
    ]
    return {"project_id": str(profile.get("project_id") or ""), "campaign_case_studies": cases}


def campaign_channel_tactics(profile: dict[str, Any]) -> dict[str, Any]:
    families = ["hero video", "employee storytelling", "careers-site hub", "paid media", "organic social", "OOH", "niche placement", "ERG resharing", "always-on reactivation", "events", "awards", "partnerships"]
    tactics = [
        {
            "tactic_id": f"tactic:{slugify(name)}",
            "channel_family": name,
            "execution_pattern": f"{name} execution pattern",
            "audience": str(profile.get("target_population") or "target talent"),
            "funnel_stage": ["awareness", "consideration", "conversion"][index % 3],
            "dependencies": ["source proof", "creative assets"],
            "proof_metric": "engagement",
            "case_ids": [f"case:{slugify(case_name)}" for case_name in ["BT", "National Grid", "SSEN"][0 : 1 + index % 3]],
            "recommendation_fit": "high" if index < 6 else "medium",
        }
        for index, name in enumerate(families)
    ]
    return {"project_id": str(profile.get("project_id") or ""), "channel_tactics": tactics}


def campaign_analysis_pack(profile: dict[str, Any], evidence_record: dict[str, Any], cases_record: dict[str, Any], tactics_record: dict[str, Any]) -> dict[str, Any]:
    stats = list(evidence_record.get("labor_market_stats") or [])
    signals = list(evidence_record.get("policy_or_context_signals") or [])
    cases = list(cases_record.get("campaign_case_studies") or [])
    tactics = list(tactics_record.get("channel_tactics") or [])
    recommendations = []
    for index, headline in enumerate(["Build proof-led role model stories", "Pair campaign bursts with always-on reactivation", "Use partner networks to reach underrepresented candidates", "Make engineering career paths concrete"]):
        recommendations.append(
            {
                "recommendation_id": f"campaign-recommendation:{index + 1:03d}",
                "headline": headline,
                "summary": "Recommendation combines labor-market context, campaign case evidence, and channel tactics.",
                "supporting_stat_or_signal_ids": [stats[index % len(stats)]["stat_id"], signals[index % len(signals)]["signal_id"]],
                "supporting_case_ids": [cases[index % len(cases)]["case_id"]],
                "supporting_tactic_ids": [tactics[index % len(tactics)]["tactic_id"]],
            }
        )
    return {
        "project_id": str(profile.get("project_id") or ""),
        "campaign_lessons": [case["lessons"] for case in cases[:4]],
        "campaign_recommendations": recommendations,
    }


def campaign_recommendation_body(analysis_record: dict[str, Any]) -> str:
    rows = [[item["headline"], item["summary"], ", ".join(item["supporting_tactic_ids"])] for item in analysis_record.get("campaign_recommendations") or []]
    return segment_tvp_table_body("Campaign Recommendation Readout", rows)


def campaign_l4_body(profile: dict[str, Any], analysis_record: dict[str, Any]) -> str:
    return f"""    <section>
      <h2>Campaign Desk Research Readout</h2>
      <p>{escape(str(profile.get("client_full_name") or profile.get("client_name") or "Client"))} recommendations combine labor-market context, campaign cases, and channel tactics.</p>
    </section>
{campaign_recommendation_body(analysis_record)}
"""



def build_campaign_manifest(profile: dict[str, Any]) -> dict[str, Any]:
    client_name = str(profile.get("client_full_name") or profile.get("client_name") or "Client")
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"publication-pipeline-{slugify(client_name)}-campaign-desk-research",
        "company": client_name,
        "domain": str(profile.get("domain") or f"{slugify(client_name)}.example"),
        "template_id": CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID,
        "talent_segment": str(profile.get("target_population") or profile.get("audience") or "target talent"),
        "framework_id": "KILOS",
        "framework_version": "1.0",
        "status": "complete",
        "created_at": CREATED_AT,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "publication_pipeline": CAMPAIGN_DESK_RESEARCH_KEY,
        },
        "steps": [
            manifest_step("p0-pipeline-intake", 0, "Pipeline intake", "Normalize the campaign desk-research request.", ["p0-pipeline-intake"], []),
            manifest_step("p0-research-source-roster", 0, "Research source roster", "Group desk-research sources by authority and topic.", ["p0-research-source-roster"], ["p0-pipeline-intake"]),
            manifest_step("p1-desk-research-evidence-pack", 1, "Desk research evidence pack", "Stage labor-market stats and policy/context signals.", ["p1-desk-research-evidence-pack"], ["p0-research-source-roster"]),
            manifest_step("p2-campaign-case-matrix", 2, "Campaign case matrix", "Normalize competitor and comparator campaign cases.", ["p2-campaign-case-matrix"], ["p1-desk-research-evidence-pack"]),
            manifest_step("p2-channel-tactic-opportunity-map", 2, "Channel tactic opportunity map", "Map channel tactics to campaign cases and funnel stages.", ["p2-channel-tactic-opportunity-map"], ["p2-campaign-case-matrix"]),
            manifest_step("p3-campaign-lessons-analysis-pack", 3, "Campaign lessons analysis pack", "Derive campaign lessons and recommendations.", ["p3-campaign-lessons-analysis-pack"], ["p2-channel-tactic-opportunity-map"]),
            manifest_step("p4-campaign-recommendation-readout", 4, "Campaign recommendation readout", "Render campaign recommendations.", ["p4-campaign-recommendation-readout"], ["p3-campaign-lessons-analysis-pack"]),
            manifest_step("p4-l4-publication-view", 4, "L4 publication view", "Render the campaign publication readout.", ["p4-l4-publication"], ["p3-campaign-lessons-analysis-pack"]),
        ],
        "artifacts": [
            manifest_artifact("p0-pipeline-intake", 0, "pipeline_intake", "p0-pipeline-intake", [], "pipeline-intake.json", "publication.pipeline_intake", "Campaign intake"),
            manifest_artifact("p0-research-source-roster", 0, "research_source_roster", "p0-research-source-roster", ["p0-pipeline-intake"], "research-source-roster.json", "publication.research_source_roster", "Desk research source roster"),
            manifest_artifact("p1-desk-research-evidence-pack", 1, "desk_research_evidence_pack", "p1-desk-research-evidence-pack", ["p0-research-source-roster"], "desk-research-evidence-pack.json", "publication.desk_research_evidence_pack", "Desk research evidence pack"),
            manifest_artifact("p2-campaign-case-matrix", 2, "campaign_case_matrix", "p2-campaign-case-matrix", ["p1-desk-research-evidence-pack"], "campaign-case-matrix.json", "publication.campaign_case_matrix", "Campaign case matrix"),
            manifest_artifact("p2-channel-tactic-opportunity-map", 2, "channel_tactic_opportunity_map", "p2-channel-tactic-opportunity-map", ["p2-campaign-case-matrix"], "channel-tactic-opportunity-map.json", "publication.channel_tactic_opportunity_map", "Channel tactic opportunity map"),
            manifest_artifact("p3-campaign-lessons-analysis-pack", 3, "campaign_lessons_analysis_pack", "p3-campaign-lessons-analysis-pack", ["p2-channel-tactic-opportunity-map", "p2-campaign-case-matrix", "p1-desk-research-evidence-pack"], "campaign-lessons-analysis-pack.json", "publication.campaign_lessons_analysis_pack", "Campaign lessons analysis pack"),
            manifest_artifact("p4-campaign-recommendation-readout", 4, "html", "p4-campaign-recommendation-readout", ["p3-campaign-lessons-analysis-pack"], "campaign-recommendation-readout.html", "publication.campaign_recommendation_readout", "Campaign recommendation readout", composite_group=publication_composite_group("campaign_recommendation_readout")),
            manifest_artifact("p4-l4-publication", 4, "l4_publication", "p4-l4-publication-view", ["p3-campaign-lessons-analysis-pack", "p2-channel-tactic-opportunity-map", "p2-campaign-case-matrix"], "l4-publication.html", "publication.l4_publication", "Campaign L4 publication readout", composite_group=publication_composite_group("l4_publication")),
        ],
    }


def generate_campaign_desk_research_fixture(
    output_dir: Path = CAMPAIGN_DESK_RESEARCH_OUTPUT_DIR,
    *,
    project_profile_path: Path | None = None,
) -> Path:
    output_dir = prepare_output_dir(
        output_dir,
        allow_unmarked_cleanup=is_default_output_dir(output_dir, CAMPAIGN_DESK_RESEARCH_OUTPUT_DIR),
    )

    profile = load_campaign_profile(project_profile_path)
    intake_record = campaign_intake(profile)
    sources_record = campaign_research_sources(profile)
    evidence_record = campaign_evidence_pack(profile, sources_record)
    cases_record = campaign_case_matrix(profile)
    tactics_record = campaign_channel_tactics(profile)
    analysis_record = campaign_analysis_pack(profile, evidence_record, cases_record, tactics_record)

    write_json(output_dir / "pipeline-intake.json", intake_record)
    write_json(output_dir / "research-source-roster.json", sources_record)
    write_json(output_dir / "desk-research-evidence-pack.json", evidence_record)
    write_json(output_dir / "campaign-case-matrix.json", cases_record)
    write_json(output_dir / "channel-tactic-opportunity-map.json", tactics_record)
    write_json(output_dir / "campaign-lessons-analysis-pack.json", analysis_record)
    write_text(output_dir / "campaign-recommendation-readout.html", render_publication_html("Campaign Recommendation Readout", campaign_recommendation_body(analysis_record)))
    write_text(output_dir / "l4-publication.html", render_publication_html("Campaign Desk Research Readout", campaign_l4_body(profile, analysis_record)))

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_campaign_manifest(profile))
    return manifest_path



__all__ = ["CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID", "generate_campaign_desk_research_fixture"]
