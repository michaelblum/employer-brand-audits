#!/usr/bin/env python3
"""Capture a URL into a durable workbench web snapshot artifact."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "url-stage"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        return str(resolved.relative_to(REPO_ROOT))
    return str(path)


def slugify_stage_name(value: str) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.netloc:
        raw = f"{parsed.netloc}{parsed.path}"
    raw = raw.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return slug[:80].strip("-") or "url-stage"


def safe_stage_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT not in resolved.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {resolved}")
    return resolved


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def screenshot_rect(document_rect: dict[str, Any], *, scale_x: float, scale_y: float) -> dict[str, int]:
    return {
        "x": round(float(document_rect.get("x") or 0) * scale_x),
        "y": round(float(document_rect.get("y") or 0) * scale_y),
        "width": max(1, round(float(document_rect.get("width") or 0) * scale_x)),
        "height": max(1, round(float(document_rect.get("height") or 0) * scale_y)),
    }


def build_target_map(
    blueprint: dict[str, Any],
    *,
    screenshot_dimensions: dict[str, int],
    screenshot_path: str,
) -> dict[str, Any]:
    document = blueprint.get("document") if isinstance(blueprint.get("document"), dict) else {}
    document_width = max(1, float(document.get("width") or screenshot_dimensions["width"]))
    document_height = max(1, float(document.get("height") or screenshot_dimensions["height"]))
    scale_x = float(screenshot_dimensions["width"]) / document_width
    scale_y = float(screenshot_dimensions["height"]) / document_height
    targets = []
    for index, element in enumerate(blueprint.get("elements") or [], start=1):
        if not isinstance(element, dict) or not isinstance(element.get("document_rect"), dict):
            continue
        label = str(
            element.get("accessible_name")
            or element.get("text")
            or element.get("tag")
            or f"target {index}"
        ).strip()
        targets.append(
            {
                "id": str(element.get("uid") or f"target-{index}"),
                "label": label[:160],
                "role": str(element.get("role") or ""),
                "tag": str(element.get("tag") or ""),
                "text": str(element.get("text") or "")[:240],
                "target_kind": str(element.get("target_kind") or "element"),
                "rect": screenshot_rect(element["document_rect"], scale_x=scale_x, scale_y=scale_y),
                "selector_candidates": [
                    str(item)
                    for item in element.get("selector_candidates") or []
                    if str(item)
                ],
                "confidence": float(element.get("confidence") or 0.5),
            }
        )
    return {
        "schema_version": "url_stage_target_map.v0",
        "coordinate_space": "screenshot",
        "source_url": str(blueprint.get("url") or ""),
        "viewport": blueprint.get("viewport") or {},
        "screenshot": {
            "path": screenshot_path,
            "dimensions": screenshot_dimensions,
        },
        "targets": targets,
    }


def build_web_snapshot_html(target_map: dict[str, Any]) -> str:
    screenshot = target_map.get("screenshot") if isinstance(target_map.get("screenshot"), dict) else {}
    dimensions = screenshot.get("dimensions") if isinstance(screenshot.get("dimensions"), dict) else {}
    image_path = "/" + str(screenshot.get("path") or "").lstrip("/")
    width = int(dimensions.get("width") or 1)
    height = int(dimensions.get("height") or 1)
    target_html = []
    for target in target_map.get("targets") or []:
        rect = target.get("rect") if isinstance(target.get("rect"), dict) else {}
        style = (
            f"left:{int(rect.get('x') or 0)}px;"
            f"top:{int(rect.get('y') or 0)}px;"
            f"width:{max(1, int(rect.get('width') or 1))}px;"
            f"height:{max(1, int(rect.get('height') or 1))}px"
        )
        metadata = html.escape(json.dumps(target, sort_keys=True))
        label = html.escape(str(target.get("label") or target.get("id") or "web target"))
        target_html.append(
            f'<button class="web-target" type="button" '
            f'data-web-target-id="{html.escape(str(target.get("id") or ""))}" '
            f'data-web-target="{metadata}" style="{style}" '
            f'aria-label="{label}" title="{label}"></button>'
        )
    return (
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8"><style>\n'
        "html,body{margin:0;background:#0f1115;}\n"
        ".web-snapshot-stage{position:relative;display:block;line-height:0;}\n"
        ".web-snapshot-stage img{display:block;width:100%;height:auto;}\n"
        ".web-target{position:absolute;border:0;background:rgba(70,132,255,0.01);padding:0;cursor:crosshair;}\n"
        ".web-target:hover,.web-target:focus{outline:2px solid #58a6ff;outline-offset:0;background:rgba(88,166,255,0.12);}\n"
        "</style></head><body>\n"
        f'<div class="web-snapshot-stage" data-web-snapshot-stage="true" style="width:{width}px;height:{height}px">\n'
        f'<img src="{html.escape(image_path)}" width="{width}" height="{height}" alt="Captured web page snapshot">\n'
        f"{''.join(target_html)}\n"
        "</div>\n"
        "</body></html>\n"
    )


def write_url_stage_manifest(
    *,
    output_dir: Path,
    slug: str,
    url: str,
    status: str,
    viewport: dict[str, Any],
    paths: dict[str, Path],
    screenshot_dimensions: dict[str, int],
) -> Path:
    manifest = {
        "schema_version": "url_stage_capture.v0",
        "slug": slug,
        "url": url,
        "status": status,
        "viewport": viewport,
        "screenshot": {
            "path": repo_relative(paths["page_screenshot"]),
            "dimensions": screenshot_dimensions,
        },
        "blueprint": {"path": repo_relative(paths["blueprint"])},
        "artifacts": {key: repo_relative(path) for key, path in sorted(paths.items())},
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path
