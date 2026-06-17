#!/usr/bin/env python3
"""Project source manifests into a normalized artifact workbench payload."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from workbench_bounded_input import (
        bounded_input_overlay_definition as workflow_input_overlay,
        bounded_input_overlay_definitions_for_step as workflow_input_overlays_for_step,
    )
except ModuleNotFoundError:
    from scripts.workbench_bounded_input import (
        bounded_input_overlay_definition as workflow_input_overlay,
        bounded_input_overlay_definitions_for_step as workflow_input_overlays_for_step,
    )


REPO_ROOT = Path(__file__).resolve().parent.parent
MERMAID_FENCE_RE = re.compile(r"^```\s*mermaid\s*$", re.IGNORECASE | re.MULTILINE)
MERMAID_SCAN_MAX_BYTES = 512 * 1024
URL_RESOURCE_ID_SLUG_MAX_LENGTH = 80

IMAGE_SLOTS = {
    "viewport": {
        "label": "Viewport Screenshot",
        "slot": "capture.viewport",
        "artifact_type": "image",
        "layer": 1,
    },
    "full_page": {
        "label": "Full Page Screenshot",
        "slot": "capture.full_page",
        "artifact_type": "image",
        "layer": 1,
    },
    "element": {
        "label": "Element Screenshot",
        "slot": "capture.element",
        "artifact_type": "image",
        "layer": 1,
    },
}

TEXT_SLOTS = {
    "summary": {
        "label": "Workflow Summary",
        "slot": "page.summary",
        "artifact_type": "markdown",
        "layer": 2,
    },
    "markdown": {
        "label": "Markdown",
        "slot": "page.markdown",
        "artifact_type": "markdown",
        "layer": 1,
    },
    "md": {
        "label": "Markdown",
        "slot": "page.markdown",
        "artifact_type": "markdown",
        "layer": 1,
    },
    "report": {
        "label": "Report",
        "slot": "report.markdown",
        "artifact_type": "markdown",
        "layer": 4,
    },
    "analysis": {
        "label": "Analysis",
        "slot": "analysis.markdown",
        "artifact_type": "markdown",
        "layer": 2,
    },
    "synthesis": {
        "label": "Synthesis",
        "slot": "synthesis.markdown",
        "artifact_type": "markdown",
        "layer": 3,
    },
    "visible_text_stdout": {
        "label": "Visible Text",
        "slot": "capture.visible_text",
        "artifact_type": "text",
        "layer": 1,
    },
    "snapshot": {
        "label": "Snapshot",
        "slot": "capture.snapshot",
        "artifact_type": "text",
        "layer": 1,
    },
    "log": {
        "label": "Capture Log",
        "slot": "debug.log",
        "artifact_type": "log",
        "layer": 1,
    },
}

RESOURCE_FILE_KEYS = {
    "url": "source.url_file",
    "manifest": "source.page_manifest",
    "settle_stdout": "debug.settle_stdout",
    "hide_stdout": "debug.hide_stdout",
    "restore_stdout": "debug.restore_stdout",
}

URL_STAGE_ARTIFACT_SLOTS = {
    "web_snapshot": {
        "label": "Web Snapshot",
        "slot": "web.snapshot",
        "artifact_type": "html",
        "kind": "web_snapshot",
        "layer": 1,
    },
    "web_snapshot_data": {
        "label": "Web Snapshot Data",
        "slot": "web.snapshot.data",
        "artifact_type": "json",
        "kind": "web_snapshot_data",
        "layer": 1,
    },
}

URL_STAGE_SUPPORT_RESOURCE_SLOTS = {
    "page_screenshot": "capture.full_page",
    "capture_log": "debug.log",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def page_host(url: Any) -> str | None:
    parsed = urlparse(str(url or ""))
    return parsed.netloc.lower() or None


def matrix_artifact_id(slug: str, key: str) -> str:
    return f"{slug}:{key}"


def workflow_step_id(slug: str) -> str:
    return f"step:capture-page:{slug}"


def source_url_resource_id(slug: str) -> str:
    return f"resource:url:{slug}"


def file_resource_id(slug: str, key: str) -> str:
    return f"resource:file:{slug}:{key}"


def mime_type_for(path_value: str) -> str:
    if Path(path_value).suffix.lower() == ".mmd":
        return "text/vnd.mermaid"
    if Path(path_value).suffix.lower() in {".md", ".markdown"}:
        return "text/markdown"
    return mimetypes.guess_type(path_value)[0] or "application/octet-stream"


def repository_file_path(path_value: str, base_dir: Path | None = None) -> Path | None:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = (base_dir or REPO_ROOT) / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.exists() or (resolved != REPO_ROOT and REPO_ROOT not in resolved.parents):
        return None
    return resolved


def repository_relative_path(path_value: str, base_dir: Path | None = None) -> str:
    path = repository_file_path(path_value, base_dir)
    if path is None:
        return path_value
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path_value


def markdown_has_mermaid(path_value: str, base_dir: Path | None = None) -> bool:
    path = repository_file_path(path_value, base_dir)
    if path is None:
        return False
    try:
        if path.stat().st_size > MERMAID_SCAN_MAX_BYTES:
            return False
        return bool(MERMAID_FENCE_RE.search(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


def classify_artifact(key: str, path_value: str) -> dict[str, Any] | None:
    if key in IMAGE_SLOTS:
        return IMAGE_SLOTS[key]
    if key in TEXT_SLOTS:
        return TEXT_SLOTS[key]
    suffix = Path(path_value).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return {
            "label": key.replace("_", " ").replace("-", " ").title(),
            "slot": f"page.{key}",
            "artifact_type": "markdown",
            "layer": 2,
        }
    return None


def audit_workbench_type(artifact_type: str, path_value: str) -> str:
    suffix = Path(path_value).suffix.lower()
    mime_type = mime_type_for(path_value)
    if artifact_type in {"screenshot", "crop"} or mime_type.startswith("image/"):
        return "image"
    if suffix in {".md", ".markdown"} or mime_type == "text/markdown":
        return "markdown"
    if suffix in {".html", ".htm"} or mime_type == "text/html" or artifact_type == "html":
        return "html"
    if suffix == ".json" or mime_type == "application/json":
        return "json"
    if mime_type.startswith("text/"):
        return "text"
    return artifact_type or "file"


def audit_artifact_slot(artifact: dict[str, Any]) -> str:
    params = artifact.get("params") if isinstance(artifact.get("params"), dict) else {}
    slot = str(params.get("slot") or "").strip()
    if slot:
        return slot
    artifact_type = str(artifact.get("type") or "artifact")
    layer = artifact.get("layer")
    if isinstance(layer, int):
        return f"l{layer}.{artifact_type}"
    return f"artifact.{artifact_type}"


def audit_artifact_name(artifact: dict[str, Any]) -> str:
    card = artifact.get("card")
    if isinstance(card, dict):
        summary = str(card.get("summary") or "").strip()
        if summary:
            return summary.splitlines()[0][:120]
    artifact_id = str(artifact.get("id") or "artifact")
    artifact_type = str(artifact.get("type") or "artifact").replace("_", " ")
    return f"{artifact_id} {artifact_type}".strip()


def derived_workflow_status(steps: list[dict[str, Any]]) -> str:
    statuses = {str(step.get("status") or "unknown") for step in steps}
    for status in ("failed", "blocked", "running", "pending"):
        if status in statuses:
            return status
    if statuses == {"complete"}:
        return "complete"
    return "unknown"


def collect_artifact_lineage_ids(
    root_ids: list[str],
    artifact_order: list[str],
    artifacts_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    seen: set[str] = set()
    pending = list(root_ids)
    while pending:
        artifact_id = pending.pop(0)
        if artifact_id in seen or artifact_id not in artifacts_by_id:
            continue
        seen.add(artifact_id)
        for parent_id in artifacts_by_id[artifact_id].get("parent_ids") or []:
            if parent_id not in seen:
                pending.append(str(parent_id))
    return [artifact_id for artifact_id in artifact_order if artifact_id in seen]


def audit_report_artifact_groups(
    workflow_steps: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_order = [str(artifact.get("id")) for artifact in artifacts if artifact.get("id")]
    artifacts_by_id = {str(artifact.get("id")): artifact for artifact in artifacts if artifact.get("id")}
    groups: list[dict[str, Any]] = []
    for step in workflow_steps:
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        step_artifact_ids = [
            artifact_id
            for artifact_id in (str(value) for value in (step.get("artifact_ids") or []))
            if artifact_id in artifacts_by_id
        ]
        report_artifact_ids = [
            artifact_id
            for artifact_id in step_artifact_ids
            if artifacts_by_id[artifact_id].get("layer") == 4
            or artifacts_by_id[artifact_id].get("kind") in {"report", "html"}
        ]
        if not report_artifact_ids:
            continue
        group_id = f"composite:audit-report:{step_id}"
        group_artifact_ids = collect_artifact_lineage_ids(report_artifact_ids, artifact_order, artifacts_by_id)
        if not group_artifact_ids:
            continue
        groups.append(
            {
                "id": group_id,
                "kind": "audit_report_bundle",
                "label": f"{step.get('name') or step_id} bundle",
                "artifact_ids": group_artifact_ids,
                "edge_ids": [f"edge:{group_id}:{artifact_id}" for artifact_id in group_artifact_ids],
                "source": {
                    "kind": "audit_report_step",
                    "step_id": step_id,
                    "artifact_ids": report_artifact_ids,
                },
                "slot": "audit.report.bundle",
            }
        )
    return groups


def add_slot_facet(slot_index: dict[str, dict[str, Any]], slot: str, label: str, artifact_id: str) -> None:
    slot_index.setdefault(
        slot,
        {
            "id": f"facet:slot:{slot}",
            "kind": "slot",
            "value": slot,
            "label": label,
            "artifact_ids": [],
        },
    )
    slot_index[slot]["artifact_ids"].append(artifact_id)


def add_host_facet(
    host_index: dict[str, dict[str, Any]],
    host: str | None,
    artifact_id: str | None = None,
) -> None:
    if not host:
        return
    host_index.setdefault(
        host,
        {
            "id": f"facet:host:{host}",
            "kind": "host",
            "value": host,
            "page_slugs": [],
            "artifact_ids": [],
        },
    )
    if artifact_id:
        host_index[host]["artifact_ids"].append(artifact_id)


def normalized_required_inputs(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def audit_url_resource_id(url: str) -> str:
    # TODO: include a short hash suffix so distinct long URLs cannot collide after slug truncation.
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-").lower()
    safe = slug[:URL_RESOURCE_ID_SLUG_MAX_LENGTH] or "url"
    return f"resource:url:{safe}"


def local_file_resource(slug: str, key: str, path_value: str, slot: str) -> dict[str, Any]:
    return {
        "id": file_resource_id(slug, key),
        "type": "file",
        "slot": slot,
        "path": path_value,
        "mime_type": mime_type_for(path_value),
        "source_page": {"slug": slug},
    }


def url_stage_artifact_id(slug: str, key: str) -> str:
    return f"{slug}:{key}"


def url_stage_resolved_path(path_value: str, manifest_dir: Path) -> Path | None:
    return repository_file_path(path_value) or repository_file_path(path_value, manifest_dir)


def url_stage_relative_path(path_value: str, manifest_dir: Path) -> str:
    resolved = url_stage_resolved_path(path_value, manifest_dir)
    if resolved is None:
        return path_value
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return path_value


def url_stage_manifest_context(manifest: dict[str, Any]) -> dict[str, Any]:
    context = (
        dict(manifest.get("workbench_context"))
        if isinstance(manifest.get("workbench_context"), dict)
        else {}
    )
    context.setdefault("artifact_control_policy", "read-only")
    return context


def url_stage_support_file_resources(
    slug: str,
    page_artifacts: dict[str, Any],
    manifest_dir: Path,
) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for key, slot in URL_STAGE_SUPPORT_RESOURCE_SLOTS.items():
        path_value_raw = page_artifacts.get(key)
        if not path_value_raw:
            continue
        resources.append(
            local_file_resource(
                slug,
                key,
                url_stage_relative_path(str(path_value_raw), manifest_dir),
                slot,
            )
        )
    return resources


def validate_url_stage_web_snapshot_data(data: dict[str, Any], *, path_value: str) -> dict[str, Any]:
    if data.get("schema_version") != "web_snapshot.v0":
        raise ValueError(f"URL stage web_snapshot_data has invalid schema_version: {path_value}")
    visual = data.get("visual") if isinstance(data.get("visual"), dict) else {}
    image = visual.get("image") if isinstance(visual.get("image"), dict) else {}
    dimensions = image.get("dimensions") if isinstance(image.get("dimensions"), dict) else {}
    if not dimensions.get("width") or not dimensions.get("height"):
        raise ValueError(f"URL stage web_snapshot_data is missing visual.image.dimensions: {path_value}")
    projections = data.get("projections") if isinstance(data.get("projections"), dict) else {}
    target_map = projections.get("target_map") if isinstance(projections.get("target_map"), dict) else {}
    if target_map.get("coordinate_space") != "screenshot":
        raise ValueError(f"URL stage web_snapshot_data target_map must use screenshot coordinates: {path_value}")
    targets = target_map.get("targets")
    if not isinstance(targets, list):
        raise ValueError(f"URL stage web_snapshot_data is missing projections.target_map.targets: {path_value}")
    return data


def read_url_stage_web_snapshot_data(path_value: str, manifest_dir: Path) -> dict[str, Any]:
    path = url_stage_resolved_path(path_value, manifest_dir)
    if path is None:
        raise ValueError(f"URL stage web_snapshot_data path is invalid: {path_value}")
    try:
        data = read_json(path)
    except OSError as error:
        raise ValueError(f"URL stage web_snapshot_data could not be read: {path_value}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"URL stage web_snapshot_data is invalid JSON: {path_value}") from error
    if not isinstance(data, dict):
        raise ValueError(f"URL stage web_snapshot_data must be an object: {path_value}")
    return validate_url_stage_web_snapshot_data(data, path_value=path_value)


def url_stage_web_snapshot_data_facets(data: dict[str, Any]) -> dict[str, Any]:
    projections = data.get("projections") if isinstance(data.get("projections"), dict) else {}
    target_map = projections.get("target_map") if isinstance(projections.get("target_map"), dict) else {}
    targets = target_map.get("targets") if isinstance(target_map.get("targets"), list) else []
    visual = data.get("visual") if isinstance(data.get("visual"), dict) else {}
    image = visual.get("image") if isinstance(visual.get("image"), dict) else {}
    dimensions = image.get("dimensions") if isinstance(image.get("dimensions"), dict) else {}
    ui_views = data.get("ui_views") if isinstance(data.get("ui_views"), list) else []
    projection_catalog = data.get("projection_catalog") if isinstance(data.get("projection_catalog"), dict) else {}
    return {
        "coordinate_space": str(visual.get("coordinate_space") or target_map.get("coordinate_space") or ""),
        "target_count": len(targets),
        "projection_count": len(projection_catalog),
        "ui_view_ids": [
            str(view.get("id"))
            for view in ui_views
            if isinstance(view, dict) and view.get("id")
        ],
        "visual_dimensions": dimensions,
    }


def project_url_stage_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Project a URL-stage capture manifest into the workbench payload.

    The staged page remains an HTML artifact generated over a screenshot. The
    target map is supporting evidence: its rects are durable screenshot
    coordinates, while selectors remain advisory replay hints.
    """
    path = Path(manifest_path).expanduser().resolve()
    manifest = read_json(path)
    if not isinstance(manifest, dict) or str(manifest.get("schema_version") or "") != "url_stage_capture.v0":
        raise ValueError(f"Expected URL stage capture manifest: {path}")

    manifest_dir = path.parent
    slug = str(manifest.get("slug") or path.parent.name or "url-stage")
    url = str(manifest.get("url") or "")
    host = page_host(url)
    source_manifest = str(path)
    workflow_id = f"workflow:url-stage:{slug}"
    step_id = f"step:url-stage:{slug}"
    status = str(manifest.get("status") or "unknown")
    workflow_status = "complete" if status == "passed" else status
    page_artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    screenshot = manifest.get("screenshot") if isinstance(manifest.get("screenshot"), dict) else {}
    screenshot_dimensions = (
        screenshot.get("dimensions")
        if isinstance(screenshot.get("dimensions"), dict)
        else {}
    )
    context = url_stage_manifest_context(manifest)

    source_resource_id = source_url_resource_id(slug)
    resources: list[dict[str, Any]] = [
        {
            "id": source_resource_id,
            "type": "url",
            "slot": "source.url",
            "url": url,
            "host": host,
            "source_page": {"slug": slug},
        }
    ]
    artifacts: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    host_index: dict[str, dict[str, Any]] = {}
    slot_index: dict[str, dict[str, Any]] = {}
    if host:
        host_index[host] = {
            "id": f"facet:host:{host}",
            "kind": "host",
            "value": host,
            "page_slugs": [slug],
            "artifact_ids": [],
        }

    support_resources = url_stage_support_file_resources(slug, page_artifacts, manifest_dir)
    resources.extend(support_resources)
    edges.extend(
        {
            "id": f"edge:{resource['id']}:{step_id}",
            "kind": "supports",
            "from": resource["id"],
            "to": step_id,
        }
        for resource in support_resources
    )

    projected_artifact_ids: list[str] = []
    web_snapshot_data_key = "web_snapshot_data"
    web_snapshot_data_raw = page_artifacts.get(web_snapshot_data_key)
    if not web_snapshot_data_raw:
        raise ValueError(f"URL stage manifest is missing required artifact: {web_snapshot_data_key}")
    web_snapshot_data = read_url_stage_web_snapshot_data(str(web_snapshot_data_raw), manifest_dir)
    web_snapshot_data_facets = url_stage_web_snapshot_data_facets(web_snapshot_data)
    # URL-stage is an adapter at this boundary: below this point it projects
    # capture-specific files into generic workbench resources, artifacts,
    # facets, and groups so the browser shell avoids URL-stage registrations.
    parent_ids_by_key = {
        "web_snapshot": [web_snapshot_data_key],
    }
    for key, config in URL_STAGE_ARTIFACT_SLOTS.items():
        path_value_raw = page_artifacts.get(key)
        if not path_value_raw:
            continue
        path_value = url_stage_relative_path(str(path_value_raw), manifest_dir)
        artifact_id = url_stage_artifact_id(slug, key)
        projected_artifact_ids.append(artifact_id)
        file_resource = local_file_resource(slug, key, path_value, f"artifact.{key}")
        resources.append(file_resource)
        resource_ids = [source_resource_id, file_resource["id"]]
        artifact_type = str(config["artifact_type"])
        slot = str(config["slot"])
        add_slot_facet(slot_index, slot, str(config["label"]), artifact_id)
        add_host_facet(host_index, host, artifact_id)
        parent_ids = [
            url_stage_artifact_id(slug, parent_key)
            for parent_key in parent_ids_by_key.get(key, [])
            if page_artifacts.get(parent_key)
        ]
        capabilities = ["view"]
        if artifact_type in {"image", "html"}:
            capabilities.append("annotate")

        facets: dict[str, Any] = {
            "host": host,
            "page_slug": slug,
            "artifact_type": artifact_type,
            "artifact_kind": config["kind"],
            "slot": slot,
            "source_url": url,
        }
        if key == "web_snapshot":
            facets["data_artifact_id"] = url_stage_artifact_id(slug, web_snapshot_data_key)
            facets.update(web_snapshot_data_facets)
            facets["intent_spine"] = "annotation_overlays"
            facets["selector_policy"] = "advisory"
        if key == web_snapshot_data_key:
            facets.update(web_snapshot_data_facets)

        artifact: dict[str, Any] = {
            "id": artifact_id,
            "name": f"{slug} {config['label']}",
            "type": artifact_type,
            "kind": config["kind"],
            "slot": slot,
            "layer": config["layer"],
            "status": workflow_status,
            "path": path_value,
            "mime_type": mime_type_for(path_value),
            "produced_by_step_id": step_id,
            "parent_ids": parent_ids,
            "resource_ids": resource_ids,
            "source_page": {"slug": slug, "url": url, "host": host},
            "facets": facets,
            "capabilities": capabilities,
        }
        if key == "web_snapshot":
            artifact["mime_type"] = "text/html"
            visual_dimensions = web_snapshot_data_facets.get("visual_dimensions")
            if isinstance(visual_dimensions, dict):
                artifact["dimensions"] = visual_dimensions
        if key == web_snapshot_data_key:
            artifact["mime_type"] = "application/json"
        artifacts.append(artifact)
        edges.extend(
            [
                {
                    "id": f"edge:{file_resource['id']}:{artifact_id}",
                    "kind": "supports",
                    "from": file_resource["id"],
                    "to": artifact_id,
                },
                {
                    "id": f"edge:{step_id}:{artifact_id}",
                    "kind": "produced_by",
                    "from": step_id,
                    "to": artifact_id,
                },
                {
                    "id": f"edge:{artifact_id}:{source_resource_id}",
                    "kind": "observes",
                    "from": artifact_id,
                    "to": source_resource_id,
                },
            ]
        )
        edges.extend(
            {
                "id": f"edge:{artifact_id}:{parent_id}",
                "kind": "derived_from",
                "from": artifact_id,
                "to": parent_id,
            }
            for parent_id in parent_ids
        )

    group_id = f"composite:url-stage:{slug}"
    artifact_groups = []
    if projected_artifact_ids:
        artifact_groups.append(
            {
                "id": group_id,
                "kind": "web_snapshot_bundle",
                "label": f"{slug} web snapshot bundle",
                "artifact_ids": projected_artifact_ids,
                "edge_ids": [f"edge:{group_id}:{artifact_id}" for artifact_id in projected_artifact_ids],
                "source": {"kind": "url_stage_manifest", "slug": slug, "url": url, "host": host},
                "slot": "web.snapshot.bundle",
            }
        )
        edges.extend(
            {
                "id": f"edge:{group_id}:{artifact_id}",
                "kind": "contains",
                "from": group_id,
                "to": artifact_id,
            }
            for artifact_id in projected_artifact_ids
        )

    return {
        "schema_version": "workbench_projection.v0",
        "source": {
            "format": "url_stage_capture",
            "manifest_path": source_manifest,
            "adapter": "project_url_stage_manifest",
            "source_schema_version": manifest.get("schema_version"),
            "workbench_context": context,
        },
        "workflow": {
            "id": workflow_id,
            "name": f"{slug} URL stage",
            "status": workflow_status,
            "source_manifest": source_manifest,
            "slug": slug,
            "url": url,
            "steps": [
                {
                    "id": step_id,
                    "name": "Capture staged URL",
                    "description": "Capture a live URL into durable screenshot, target map, text, and synthetic HTML artifacts.",
                    "status": workflow_status,
                    "layer": 1,
                    "required_inputs": [
                        {
                            "id": "url",
                            "label": "Source URL",
                            "status": "filled" if url else "pending",
                            "value": url or None,
                        }
                    ],
                    "artifact_ids": projected_artifact_ids,
                    "parent_step_ids": [],
                    "source_page": {"slug": slug, "url": url, "host": host},
                }
            ],
        },
        "resources": resources,
        "artifacts": artifacts,
        "artifact_groups": artifact_groups,
        "edges": edges,
        "facets": {
            "hosts": sorted(host_index.values(), key=lambda item: item["value"]),
            "slots": sorted(slot_index.values(), key=lambda item: item["value"]),
        },
        "extension_points": {
            "intent_spine": "Natural-language overlays are the primary durable interaction record for web snapshots.",
            "selector_replay": "Selectors in target maps are advisory Playwright CLI replay and mining hints.",
        },
    }


def project_matrix_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Project a Playwright public-page matrix manifest into workbench concepts.

    This is intentionally a legacy adapter, not an ADR-002 audit manifest
    parser. ADR-002 manifests are handled by project_audit_manifest().
    """
    path = Path(manifest_path).expanduser().resolve()
    manifest = read_json(path)
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    if not isinstance(pages, list):
        raise ValueError(f"Expected matrix manifest with pages[]: {path}")

    source_manifest = str(path)
    workflow_id = "workflow:playwright-public-page-matrix"
    workflow_steps: list[dict[str, Any]] = [
        {
            "id": "step:url-discovery",
            "name": "URL discovery",
            "description": "Seed the capture matrix with public employer-brand pages.",
            "status": "complete" if pages else "pending",
            "layer": 0,
            "required_inputs": [],
            "artifact_ids": [],
            "parent_step_ids": [],
        }
    ]
    resources: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    artifact_groups: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    host_index: dict[str, dict[str, Any]] = {}
    slot_index: dict[str, dict[str, Any]] = {}

    for page in pages:
        if not isinstance(page, dict):
            continue
        slug = str(page.get("slug") or "page")
        url = str(page.get("url") or "")
        host = page_host(url)
        page_status = str(page.get("status") or "unknown")
        step_id = workflow_step_id(slug)
        source_resource_id = source_url_resource_id(slug)
        page_artifacts = page.get("artifacts") if isinstance(page.get("artifacts"), dict) else {}
        dimensions = (
            page.get("screenshot_dimensions")
            if isinstance(page.get("screenshot_dimensions"), dict)
            else {}
        )
        page_workbench_artifact_ids: list[str] = []

        workflow_steps.append(
            {
                "id": step_id,
                "name": f"Capture {slug}",
                "description": "Capture public page screenshots, text, and supporting workflow artifacts.",
                "status": "complete" if page_status == "passed" else page_status,
                "layer": 1,
                "required_inputs": [
                    {
                        "id": "url",
                        "label": "Source URL",
                        "status": "filled" if url else "pending",
                        "value": url or None,
                    }
                ],
                "artifact_ids": [],
                "parent_step_ids": ["step:url-discovery"],
                "source_page": {"slug": slug, "url": url, "host": host},
            }
        )
        edges.append(
            {
                "id": f"edge:step:url-discovery:{step_id}",
                "kind": "depends_on",
                "from": step_id,
                "to": "step:url-discovery",
            }
        )

        resources.append(
            {
                "id": source_resource_id,
                "type": "url",
                "slot": "source.url",
                "url": url,
                "host": host,
                "source_page": {"slug": slug},
            }
        )

        if host:
            host_index.setdefault(
                host,
                {
                    "id": f"facet:host:{host}",
                    "kind": "host",
                    "value": host,
                    "page_slugs": [],
                    "artifact_ids": [],
                },
            )
            host_index[host]["page_slugs"].append(slug)

        for key, path_value_raw in page_artifacts.items():
            if not path_value_raw:
                continue
            key = str(key)
            path_value = str(path_value_raw)
            resource_slot = RESOURCE_FILE_KEYS.get(key)
            if resource_slot:
                resources.append(local_file_resource(slug, key, path_value, resource_slot))
                edges.append(
                    {
                        "id": f"edge:{file_resource_id(slug, key)}:{step_id}",
                        "kind": "supports",
                        "from": file_resource_id(slug, key),
                        "to": step_id,
                    }
                )

            classification = classify_artifact(key, path_value)
            if classification is None:
                continue

            artifact_id = matrix_artifact_id(slug, key)
            slot = str(classification["slot"])
            artifact_type = str(classification["artifact_type"])
            workflow_steps[-1]["artifact_ids"].append(artifact_id)

            slot_index.setdefault(
                slot,
                {
                    "id": f"facet:slot:{slot}",
                    "kind": "slot",
                    "value": slot,
                    "label": classification["label"],
                    "artifact_ids": [],
                },
            )
            slot_index[slot]["artifact_ids"].append(artifact_id)
            if host:
                host_index[host]["artifact_ids"].append(artifact_id)

            artifact_resource_ids = [source_resource_id]
            if resource_slot:
                artifact_resource_ids.append(file_resource_id(slug, key))

            artifact = {
                "id": artifact_id,
                "name": f"{slug} {classification['label']}",
                "type": artifact_type,
                "kind": key,
                "slot": slot,
                "layer": classification["layer"],
                "status": "complete" if page_status == "passed" else page_status,
                "path": path_value,
                "mime_type": mime_type_for(path_value),
                "produced_by_step_id": step_id,
                "parent_ids": [],
                "resource_ids": artifact_resource_ids,
                "source_page": {
                    "slug": slug,
                    "url": url,
                    "host": host,
                    "target_used": page.get("target_used"),
                },
                "facets": {
                    "host": host,
                    "page_slug": slug,
                    "artifact_type": artifact_type,
                    "artifact_kind": key,
                    "slot": slot,
                },
            }
            if artifact_type in {"image", "markdown"}:
                page_workbench_artifact_ids.append(artifact_id)
            if key in IMAGE_SLOTS:
                artifact["dimensions"] = dimensions.get(key)
                artifact["capabilities"] = ["view", "annotate"]
            elif artifact_type == "markdown":
                artifact["capabilities"] = ["view", "edit", "annotate"]
                if markdown_has_mermaid(path_value):
                    artifact["capabilities"].append("render")
                    artifact["facets"]["diagram_kind"] = "mermaid"
            else:
                artifact["capabilities"] = ["view"]
            artifacts.append(artifact)

            edges.extend(
                [
                    {
                        "id": f"edge:{step_id}:{artifact_id}",
                        "kind": "produced_by",
                        "from": step_id,
                        "to": artifact_id,
                    },
                    {
                        "id": f"edge:{artifact_id}:{source_resource_id}",
                        "kind": "observes",
                        "from": artifact_id,
                        "to": source_resource_id,
                    },
                ]
            )

        if page_workbench_artifact_ids:
            group_id = f"composite:page:{slug}"
            group = {
                "id": group_id,
                "kind": "source_page_bundle",
                "label": f"{slug} source bundle",
                "artifact_ids": page_workbench_artifact_ids,
                "edge_ids": [f"edge:{group_id}:{artifact_id}" for artifact_id in page_workbench_artifact_ids],
                "source": {"kind": "matrix_page", "slug": slug, "url": url, "host": host},
                "slot": "page.bundle",
            }
            artifact_groups.append(group)
            edges.extend(
                {
                    "id": f"edge:{group_id}:{artifact_id}",
                    "kind": "contains",
                    "from": group_id,
                    "to": artifact_id,
                }
                for artifact_id in page_workbench_artifact_ids
            )

    return {
        "schema_version": "workbench_projection.v0",
        "source": {
            "format": "playwright_public_page_matrix",
            "manifest_path": source_manifest,
            "adapter": "project_matrix_manifest",
        },
        "workflow": {
            "id": workflow_id,
            "name": "Playwright public-page matrix",
            "status": manifest.get("status", "unknown"),
            "source_manifest": source_manifest,
            "steps": workflow_steps,
        },
        "resources": resources,
        "artifacts": artifacts,
        "artifact_groups": artifact_groups,
        "edges": edges,
        "facets": {
            "hosts": sorted(host_index.values(), key=lambda item: item["value"]),
            "slots": sorted(slot_index.values(), key=lambda item: item["value"]),
        },
        "extension_points": {
            "audit_manifest_adapter": "Use project_audit_manifest for ADR-002 steps/artifacts without matrix assumptions.",
            "artifact_provenance": "TODO: replace matrix placeholders with artifact parent_ids when available.",
            "workflow_slots": "TODO: move slot definitions to workflow-pack metadata when packs exist.",
        },
    }


def project_audit_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Project an ADR-002 audit manifest into workbench concepts.

    This adapter preserves ADR-002's two-relationship rule: step dependencies
    remain step-to-step edges, while artifact parent_ids remain artifact
    provenance edges.

    TODO: define the missing-file path contract before wiring this adapter to
    server artifact reads; unresolved audit-relative paths currently remain as
    authored instead of being rejected or normalized.
    """
    path = Path(manifest_path).expanduser().resolve()
    manifest = read_json(path)
    if not isinstance(manifest, dict):
        raise ValueError(f"Expected ADR-002 audit manifest object: {path}")
    steps_raw = manifest.get("steps")
    artifacts_raw = manifest.get("artifacts")
    if not isinstance(steps_raw, list) or not isinstance(artifacts_raw, list):
        raise ValueError(f"Expected ADR-002 audit manifest with steps[] and artifacts[]: {path}")

    source_manifest = str(path)
    manifest_dir = path.parent
    audit_id = str(manifest.get("audit_id") or path.parent.name or path.stem)
    company = str(manifest.get("company") or audit_id)
    domain = str(manifest.get("domain") or "")
    workflow_id = f"workflow:audit:{audit_id}"
    workflow_steps: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    workflow_input_overlays: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    host_index: dict[str, dict[str, Any]] = {}
    slot_index: dict[str, dict[str, Any]] = {}
    url_resource_ids: dict[str, str] = {}

    if domain:
        add_host_facet(host_index, domain.lower())

    for step in steps_raw:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        required_inputs = normalized_required_inputs(step.get("required_inputs"))
        workflow_input_overlays.extend(workflow_input_overlays_for_step(step_id, required_inputs))
        parent_step_ids = [
            str(parent_id)
            for parent_id in (step.get("parent_step_ids") or [])
            if parent_id
        ]
        workflow_steps.append(
            {
                "id": step_id,
                "name": str(step.get("name") or step_id),
                "description": str(step.get("description") or ""),
                "status": str(step.get("status") or "unknown"),
                "layer": step.get("layer"),
                "started_at": step.get("started_at"),
                "completed_at": step.get("completed_at"),
                "error": step.get("error"),
                "required_inputs": required_inputs,
                "artifact_ids": [
                    str(artifact_id)
                    for artifact_id in (step.get("artifact_ids") or [])
                    if artifact_id
                ],
                "parent_step_ids": parent_step_ids,
            }
        )
        edges.extend(
            {
                "id": f"edge:step:{parent_step_id}:{step_id}",
                "kind": "depends_on",
                "from": step_id,
                "to": parent_step_id,
            }
            for parent_step_id in parent_step_ids
        )

    for artifact in artifacts_raw:
        if not isinstance(artifact, dict):
            continue
        artifact_id = str(artifact.get("id") or "")
        if not artifact_id:
            continue
        artifact_type = str(artifact.get("type") or "artifact")
        file_path = str(artifact.get("file_path") or artifact.get("path") or "")
        normalized_path = repository_relative_path(file_path, manifest_dir) if file_path else ""
        params = artifact.get("params") if isinstance(artifact.get("params"), dict) else {}
        source_url = str(params.get("url") or "")
        host = page_host(source_url) or (domain.lower() if domain else None)
        workbench_type = audit_workbench_type(artifact_type, file_path)
        slot = audit_artifact_slot(artifact)
        produced_by_step_id = str(artifact.get("produced_by_step_id") or "")
        parent_ids = [
            str(parent_id)
            for parent_id in (artifact.get("parent_ids") or [])
            if parent_id
        ]
        resource_ids: list[str] = []

        if file_path:
            file_resource = {
                "id": f"resource:file:{artifact_id}",
                "type": "file",
                "slot": "artifact.file",
                "path": normalized_path,
                "mime_type": mime_type_for(file_path),
                "artifact_id": artifact_id,
            }
            resources.append(file_resource)
            resource_ids.append(file_resource["id"])
            # TODO: settle supports-edge direction before any consumer relies on resource edges.
            edges.append(
                {
                    "id": f"edge:{file_resource['id']}:{artifact_id}",
                    "kind": "supports",
                    "from": file_resource["id"],
                    "to": artifact_id,
                }
            )

        if source_url:
            url_resource_id = url_resource_ids.setdefault(source_url, audit_url_resource_id(source_url))
            if not any(resource.get("id") == url_resource_id for resource in resources):
                resources.append(
                    {
                        "id": url_resource_id,
                        "type": "url",
                        "slot": "source.url",
                        "url": source_url,
                        "host": host,
                    }
                )
            resource_ids.append(url_resource_id)
            edges.append(
                {
                    "id": f"edge:{artifact_id}:{url_resource_id}",
                    "kind": "observes",
                    "from": artifact_id,
                    "to": url_resource_id,
                }
            )

        add_slot_facet(slot_index, slot, slot.replace(".", " ").title(), artifact_id)
        add_host_facet(host_index, host, artifact_id)

        capabilities = ["view"]
        if workbench_type in {"image", "markdown", "html"}:
            capabilities.append("annotate")
        if workbench_type == "markdown":
            capabilities.append("edit")

        facets = {
            "host": host,
            "artifact_type": workbench_type,
            "artifact_kind": artifact_type,
            "slot": slot,
            "layer": artifact.get("layer"),
        }
        if workbench_type == "markdown" and file_path and markdown_has_mermaid(file_path, manifest_dir):
            capabilities.append("render")
            facets["diagram_kind"] = "mermaid"

        artifacts.append(
            {
                "id": artifact_id,
                "name": audit_artifact_name(artifact),
                "type": workbench_type,
                "kind": artifact_type,
                "slot": slot,
                "layer": artifact.get("layer"),
                "status": str(artifact.get("status") or "unknown"),
                "created_at": artifact.get("created_at"),
                "path": normalized_path,
                "mime_type": mime_type_for(file_path) if file_path else "application/octet-stream",
                "produced_by_step_id": produced_by_step_id or None,
                "parent_ids": parent_ids,
                "resource_ids": resource_ids,
                "card": artifact.get("card") if isinstance(artifact.get("card"), dict) else None,
                "params": params,
                "facets": facets,
                "capabilities": capabilities,
            }
        )

        if produced_by_step_id:
            edges.append(
                {
                    "id": f"edge:{produced_by_step_id}:{artifact_id}",
                    "kind": "produced_by",
                    "from": produced_by_step_id,
                    "to": artifact_id,
                }
            )
        edges.extend(
            # TODO: namespace edge ids by kind/source once edge consumers need stable ids across edge families.
            {
                "id": f"edge:{artifact_id}:{parent_id}",
                "kind": "derived_from",
                "from": artifact_id,
                "to": parent_id,
            }
            for parent_id in parent_ids
        )

    artifact_groups = audit_report_artifact_groups(workflow_steps, artifacts)
    edges.extend(
        {
            "id": edge_id,
            "kind": "contains",
            "from": group["id"],
            "to": artifact_id,
        }
        for group in artifact_groups
        for artifact_id, edge_id in zip(group["artifact_ids"], group["edge_ids"])
    )

    return {
        "schema_version": "workbench_projection.v0",
        "source": {
            "format": "adr_002_audit_manifest",
            "manifest_path": source_manifest,
            "adapter": "project_audit_manifest",
            "source_schema_version": manifest.get("schema_version"),
            "workbench_context": manifest.get("workbench_context")
            if isinstance(manifest.get("workbench_context"), dict)
            else {},
        },
        "workflow": {
            "id": workflow_id,
            "name": f"{company} audit",
            "status": str(manifest.get("status") or derived_workflow_status(workflow_steps)),
            "source_manifest": source_manifest,
            "audit_id": audit_id,
            "company": manifest.get("company"),
            "domain": manifest.get("domain"),
            "template_id": manifest.get("template_id"),
            "talent_segment": manifest.get("talent_segment"),
            "steps": workflow_steps,
            "input_overlays": workflow_input_overlays,
        },
        "resources": resources,
        "artifacts": artifacts,
        "artifact_groups": artifact_groups,
        "edges": edges,
        "facets": {
            "hosts": sorted(host_index.values(), key=lambda item: item["value"]),
            "slots": sorted(slot_index.values(), key=lambda item: item["value"]),
        },
        "extension_points": {
            "workflow_slots": "TODO: move slot definitions to workflow-pack metadata when packs exist.",
            "artifact_groups": "Projection-only report bundles derive from ADR-002 report steps and artifact provenance.",
        },
    }


def project_workbench_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Project a supported source manifest into the normalized workbench payload."""
    path = Path(manifest_path).expanduser().resolve()
    manifest = read_json(path)
    if isinstance(manifest, dict) and manifest.get("schema_version") == "url_stage_capture.v0":
        return project_url_stage_manifest(path)
    if isinstance(manifest, dict) and isinstance(manifest.get("pages"), list):
        return project_matrix_manifest(path)
    if isinstance(manifest, dict) and isinstance(manifest.get("steps"), list) and isinstance(manifest.get("artifacts"), list):
        return project_audit_manifest(path)
    raise ValueError(f"Unsupported workbench manifest shape: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump a normalized workbench projection for a supported source manifest."
    )
    parser.add_argument("manifest", type=Path, help="Path to matrix or ADR-002 audit manifest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = project_workbench_manifest(args.manifest)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
