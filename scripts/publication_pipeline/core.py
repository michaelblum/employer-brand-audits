#!/usr/bin/env python3
"""Shared primitives for publication pipeline fixture generation."""

from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "publication-pipeline" / "latest"
KILOS_PATH = REPO_ROOT / "data" / "kilos-framework.json"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
DEFAULT_SAMPLE_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-healthcare-evp.json"
PIPELINE_TEMPLATE_ID = "publication-pipeline.evp-client-immersion-competitor-audit"
PIPELINE_KEY = "evp-client-immersion-competitor-audit"
PIPELINE_LABEL = "EVP Client Data Immersion and Competitor Messaging Audit"
SEGMENT_TVP_TEMPLATE_ID = "publication-pipeline.segment-tvp-audit"
SEGMENT_TVP_KEY = "segment-tvp-audit"
SEGMENT_TVP_LABEL = "Segment-Specific Talent Value Proposition Audit"
SEGMENT_TVP_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-tech-product-tvp.json"
COMPETITOR_WORKBOOK_TEMPLATE_ID = "publication-pipeline.competitor-messaging-workbook"
COMPETITOR_WORKBOOK_KEY = "competitor-messaging-workbook"
COMPETITOR_WORKBOOK_LABEL = "Competitor Messaging Workbook"
COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-competitor-workbook.json"
DEI_COMPETITOR_AUDIT_TEMPLATE_ID = "publication-pipeline.dei-competitor-audit"
DEI_COMPETITOR_AUDIT_KEY = "dei-competitor-audit"
DEI_COMPETITOR_AUDIT_LABEL = "DEI Competitor Audit"
DEI_COMPETITOR_AUDIT_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-dei-competitor-audit.json"
CAMPAIGN_DESK_RESEARCH_TEMPLATE_ID = "publication-pipeline.campaign-desk-research-comp-audit"
CAMPAIGN_DESK_RESEARCH_KEY = "campaign-desk-research-comp-audit"
CAMPAIGN_DESK_RESEARCH_LABEL = "DEI Campaign Desk Research and Competitor Audit"
CAMPAIGN_DESK_RESEARCH_DEFAULT_PROFILE_PATH = REPO_ROOT / "data" / "publication-pipeline-profiles" / "sample-campaign-desk-research.json"
KILOS_METHODOLOGY_TEMPLATE_ID = "publication-pipeline.kilos-methodology"
KILOS_METHODOLOGY_KEY = "kilos-methodology"
KILOS_METHODOLOGY_LABEL = "KILOS Ontology and Methodology Publication"
CREATED_AT = "2026-06-18T12:00:00Z"
OUTPUT_MARKER_NAME = ".publication-fixture-output"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def prepare_output_dir(output_dir: Path, *, allow_unmarked_cleanup: bool = False) -> Path:
    resolved = output_dir.expanduser().resolve()
    artifacts_root = ARTIFACTS_ROOT.resolve()
    try:
        resolved.relative_to(artifacts_root)
    except ValueError as exc:
        raise ValueError(f"publication output_dir must be under {artifacts_root}") from exc
    if resolved == artifacts_root:
        raise ValueError("publication output_dir must be a child of artifacts/, not artifacts/ itself")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"publication output_dir exists and is not a directory: {resolved}")
    if resolved.exists():
        marker = resolved / OUTPUT_MARKER_NAME
        has_children = any(resolved.iterdir())
        if marker.exists() or allow_unmarked_cleanup:
            shutil.rmtree(resolved)
        elif has_children:
            raise ValueError(
                "publication output_dir is non-empty and is not marker-owned: "
                f"{resolved} (missing {OUTPUT_MARKER_NAME})"
            )
    resolved.mkdir(parents=True, exist_ok=True)
    write_text(resolved / OUTPUT_MARKER_NAME, "publication fixture output\n")
    return resolved


def is_default_output_dir(output_dir: Path, default_output_dir: Path) -> bool:
    return output_dir.expanduser().resolve() == default_output_dir.expanduser().resolve()


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
    return load_project_profile(DEFAULT_SAMPLE_PROFILE_PATH)


def load_project_profile(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = DEFAULT_SAMPLE_PROFILE_PATH
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

def table_rows(cells: list[list[str]]) -> str:
    rows = []
    for row in cells:
        rows.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>")
    return "\n".join(rows)


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
    *,
    composite_group: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = {
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
    if composite_group is not None:
        artifact["facets"] = {"composite_group": composite_group}
    return artifact
