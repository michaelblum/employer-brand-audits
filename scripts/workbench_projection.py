#!/usr/bin/env python3
"""Project source manifests into a normalized workflow artifact workbench payload."""

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
        "label": "Review Summary",
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


def repository_file_path(path_value: str) -> Path | None:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.exists() or (resolved != REPO_ROOT and REPO_ROOT not in resolved.parents):
        return None
    return resolved


def markdown_has_mermaid(path_value: str) -> bool:
    path = repository_file_path(path_value)
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

    This is intentionally an adapter, not an ADR-002 audit manifest parser. TODO:
    add a sibling ADR-002 adapter once the capture pipeline writes audit manifests.
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
        page_reviewable_artifact_ids: list[str] = []

        workflow_steps.append(
            {
                "id": step_id,
                "name": f"Capture {slug}",
                "description": "Capture public page screenshots, text, and supporting review files.",
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
                page_reviewable_artifact_ids.append(artifact_id)
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

        if page_reviewable_artifact_ids:
            group_id = f"composite:page:{slug}"
            group = {
                "id": group_id,
                "kind": "source_page_bundle",
                "label": f"{slug} source bundle",
                "artifact_ids": page_reviewable_artifact_ids,
                "edge_ids": [f"edge:{group_id}:{artifact_id}" for artifact_id in page_reviewable_artifact_ids],
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
                for artifact_id in page_reviewable_artifact_ids
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
            "audit_manifest_adapter": "TODO: project ADR-002 steps/artifacts without matrix assumptions.",
            "artifact_provenance": "TODO: replace matrix placeholders with artifact parent_ids when available.",
            "workflow_slots": "TODO: move slot definitions to workflow-pack metadata when packs exist.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump a normalized workbench projection for a Playwright matrix manifest."
    )
    parser.add_argument("manifest", type=Path, help="Path to aggregate matrix manifest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = project_matrix_manifest(args.manifest)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
