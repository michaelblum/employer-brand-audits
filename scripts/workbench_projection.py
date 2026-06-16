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


REPO_ROOT = Path(__file__).resolve().parent.parent
MERMAID_FENCE_RE = re.compile(r"^```\s*mermaid\s*$", re.IGNORECASE | re.MULTILINE)
MERMAID_SCAN_MAX_BYTES = 512 * 1024

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
    if suffix == ".json" or mime_type == "application/json":
        return "json"
    if mime_type.startswith("text/"):
        return "text"
    return artifact_type or "file"


def audit_artifact_slot(artifact: dict[str, Any]) -> str:
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


def audit_url_resource_id(url: str) -> str:
    # TODO: include a short hash suffix so distinct long URLs cannot collide after slug truncation.
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-").lower()[:80] or "url"
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
                "required_inputs": step.get("required_inputs") if isinstance(step.get("required_inputs"), list) else [],
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
        if workbench_type in {"image", "markdown"}:
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

    return {
        "schema_version": "workbench_projection.v0",
        "source": {
            "format": "adr_002_audit_manifest",
            "manifest_path": source_manifest,
            "adapter": "project_audit_manifest",
            "source_schema_version": manifest.get("schema_version"),
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
        },
        "resources": resources,
        "artifacts": artifacts,
        "artifact_groups": [],
        "edges": edges,
        "facets": {
            "hosts": sorted(host_index.values(), key=lambda item: item["value"]),
            "slots": sorted(slot_index.values(), key=lambda item: item["value"]),
        },
        "extension_points": {
            "workflow_slots": "TODO: move slot definitions to workflow-pack metadata when packs exist.",
            "artifact_groups": "TODO: derive audit-native workbench subjects from real artifact provenance when needed.",
        },
    }


def project_workbench_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Project a supported source manifest into the normalized workbench payload."""
    path = Path(manifest_path).expanduser().resolve()
    manifest = read_json(path)
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
