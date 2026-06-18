#!/usr/bin/env python3
"""Capture a URL into a durable workbench web snapshot artifact."""

from __future__ import annotations

import html
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "url-stage"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"
BLUEPRINT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-web-blueprint.js"

STAGE_NAME_MAX_LENGTH = 80
SOURCE_NODE_NAME_MAX_LENGTH = 180
SOURCE_NODE_TEXT_MAX_LENGTH = 240
TARGET_LABEL_MAX_LENGTH = 160
TARGET_TEXT_MAX_LENGTH = 240
SITE_FINGERPRINT_TARGET_LIMIT = 80
SITE_FINGERPRINT_HEX_LENGTH = 16


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
    return slug[:STAGE_NAME_MAX_LENGTH].strip("-") or "url-stage"


def safe_stage_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT not in resolved.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {resolved}")
    return resolved


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_playwright_cli_result(stdout: str) -> Any | None:
    marker = "### Result"
    marker_index = stdout.find(marker)
    if marker_index < 0:
        return None
    result_lines = stdout[marker_index + len(marker) :].splitlines()
    result_text = next((line.strip() for line in result_lines if line.strip()), "")
    if not result_text:
        return None
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        return result_text


def png_dimensions(path: Path) -> dict[str, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Not a PNG file: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return {"width": int(width), "height": int(height)}


def command_for(session: str, *args: str | int | Path) -> list[str]:
    return [sys.executable, str(WRAPPER), *[str(arg) for arg in args], "--session", session]


def run_step(
    label: str,
    cmd: list[str],
    log_path: Path,
    stdout_path: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"[url-stage] {label}")
    print("+ " + " ".join(str(part) for part in cmd))
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {label}\n")
        handle.write("+ " + " ".join(str(part) for part in cmd) + "\n")
        if completed.stdout:
            handle.write("\n[stdout]\n")
            handle.write(completed.stdout)
            if not completed.stdout.endswith("\n"):
                handle.write("\n")
        if completed.stderr:
            handle.write("\n[stderr]\n")
            handle.write(completed.stderr)
            if not completed.stderr.endswith("\n"):
                handle.write("\n")
        handle.write(f"\n[exit_code] {completed.returncode}\n")
    if stdout_path is not None:
        stdout_path.write_text(completed.stdout, encoding="utf-8")
    cli_reported_error = "### Error" in completed.stdout or "### Error" in completed.stderr
    if check and (completed.returncode != 0 or cli_reported_error):
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    return completed


def screenshot_rect(document_rect: dict[str, Any], *, scale_x: float, scale_y: float) -> dict[str, int]:
    return {
        "x": round(float(document_rect.get("x") or 0) * scale_x),
        "y": round(float(document_rect.get("y") or 0) * scale_y),
        "width": max(1, round(float(document_rect.get("width") or 0) * scale_x)),
        "height": max(1, round(float(document_rect.get("height") or 0) * scale_y)),
    }


def compact_lines(value: str) -> list[str]:
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def source_tree_node_from_element(element: dict[str, Any], index: int) -> dict[str, Any]:
    rect = element.get("document_rect") if isinstance(element.get("document_rect"), dict) else {}
    return {
        "id": f"dom:{element.get('uid') or index}",
        "capture_id": str(element.get("uid") or f"target-{index}"),
        "kind": "element",
        "tag": str(element.get("tag") or ""),
        "role": str(element.get("role") or ""),
        "name": str(element.get("accessible_name") or element.get("text") or "")[
            :SOURCE_NODE_NAME_MAX_LENGTH
        ],
        "text": str(element.get("text") or "")[:SOURCE_NODE_TEXT_MAX_LENGTH],
        "target_kind": str(element.get("target_kind") or "element"),
        "document_rect": {
            "x": round(float(rect.get("x") or 0)),
            "y": round(float(rect.get("y") or 0)),
            "width": max(1, round(float(rect.get("width") or 0))),
            "height": max(1, round(float(rect.get("height") or 0))),
        },
        "selector_candidates": [
            str(item)
            for item in element.get("selector_candidates") or []
            if str(item)
        ],
        "children": [],
    }


def build_dom_source_tree(blueprint: dict[str, Any]) -> dict[str, Any] | None:
    existing = blueprint.get("dom_tree")
    if isinstance(existing, dict):
        result = dict(existing)
        result.setdefault("schema_version", "web_snapshot_dom_tree.v0")
        return result
    return None


def build_extracted_structure_nodes(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        source_tree_node_from_element(element, index)
        for index, element in enumerate(blueprint.get("elements") or [], start=1)
        if isinstance(element, dict)
    ]


def build_ax_source_tree(blueprint: dict[str, Any]) -> dict[str, Any] | None:
    existing = blueprint.get("ax_tree")
    if isinstance(existing, dict):
        result = dict(existing)
        result.setdefault("schema_version", "web_snapshot_ax_tree.v0")
        return result
    return None


def build_source_trees(blueprint: dict[str, Any]) -> dict[str, Any]:
    source_trees: dict[str, Any] = {}
    dom_tree = build_dom_source_tree(blueprint)
    ax_tree = build_ax_source_tree(blueprint)
    if dom_tree is not None:
        source_trees["dom"] = dom_tree
    if ax_tree is not None:
        source_trees["ax"] = ax_tree
    return source_trees


def flatten_dom_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: Any, depth: int) -> None:
        if not isinstance(node, dict):
            return
        nodes.append(
            {
                "id": node.get("id"),
                "depth": depth,
                "kind": node.get("kind"),
                "tag": node.get("tag"),
                "role": node.get("role"),
                "name": node.get("name"),
                "target_kind": node.get("target_kind"),
                "document_rect": node.get("document_rect"),
            }
        )
        for child in node.get("children") or []:
            visit(child, depth + 1)

    visit(tree.get("root"), 0)
    return nodes


def site_fingerprint_for(blueprint: dict[str, Any], target_map: dict[str, Any]) -> dict[str, Any]:
    parsed = urlparse(str(blueprint.get("url") or ""))
    targets = target_map.get("targets") if isinstance(target_map.get("targets"), list) else []
    target_shape = "|".join(
        f"{target.get('target_kind')}:{target.get('role')}:{target.get('label')}"
        for target in targets[:SITE_FINGERPRINT_TARGET_LIMIT]
    )
    # Non-security fingerprinting only: this short digest is a stable structural
    # grouping hint, not an authenticity or collision-resistance boundary.
    digest = (
        hashlib.sha1(target_shape.encode("utf-8")).hexdigest()[:SITE_FINGERPRINT_HEX_LENGTH]
        if target_shape
        else ""
    )
    return {
        "origin": parsed.netloc.lower(),
        "url_pattern": parsed.path or "/",
        "structural_hashes": {
            "interactive_targets": digest,
        },
        "recurring_component_hints": [],
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
                "label": label[:TARGET_LABEL_MAX_LENGTH],
                "role": str(element.get("role") or ""),
                "tag": str(element.get("tag") or ""),
                "text": str(element.get("text") or "")[:TARGET_TEXT_MAX_LENGTH],
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


def build_web_snapshot_data(
    blueprint: dict[str, Any],
    *,
    screenshot_dimensions: dict[str, int],
    screenshot_path: str,
    visible_text: str = "",
    page_snapshot: str = "",
) -> dict[str, Any]:
    target_map = build_target_map(
        blueprint,
        screenshot_dimensions=screenshot_dimensions,
        screenshot_path=screenshot_path,
    )
    source_trees = build_source_trees(blueprint)
    visible_lines = compact_lines(visible_text)
    structure_nodes = (
        flatten_dom_nodes(source_trees["dom"])
        if isinstance(source_trees.get("dom"), dict)
        else build_extracted_structure_nodes(blueprint)
    )
    return {
        "schema_version": "web_snapshot.v0",
        "source_url": str(blueprint.get("url") or ""),
        "title": str(blueprint.get("title") or ""),
        "visual": {
            "coordinate_space": "screenshot",
            "image": {
                "path": screenshot_path,
                "dimensions": screenshot_dimensions,
            },
            "viewport": blueprint.get("viewport") or {},
            "document": blueprint.get("document") or {},
        },
        "source_trees": source_trees,
        "projection_catalog": {
            "target_map": {
                "schema_version": "url_stage_target_map.v0",
                "coordinate_space": "screenshot",
                "description": "Hit-testable regions in frozen screenshot coordinates.",
            },
            "visible_text": {
                "schema_version": "web_snapshot_visible_text.v0",
                "description": "Human-readable visible text lines extracted from the captured page.",
            },
            "structure": {
                "schema_version": "web_snapshot_structure.v0",
                "description": "Normalized extracted structure records for quick agent and UI traversal.",
            },
            "page_snapshot": {
                "schema_version": "web_snapshot_page_snapshot.v0",
                "description": "Playwright snapshot text captured for semantic replay hints.",
            },
        },
        "projections": {
            "target_map": target_map,
            "visible_text": {
                "schema_version": "web_snapshot_visible_text.v0",
                "lines": visible_lines,
                "text": "\n".join(visible_lines),
            },
            "structure": {
                "schema_version": "web_snapshot_structure.v0",
                "source": "dom_tree" if isinstance(source_trees.get("dom"), dict) else "normalized_blueprint_elements",
                "nodes": structure_nodes,
            },
            "page_snapshot": {
                "schema_version": "web_snapshot_page_snapshot.v0",
                "source": "playwright_snapshot_text",
                "text": str(page_snapshot or ""),
            },
        },
        "ui_views": [
            {"id": "snapshot", "label": "Snapshot", "projection": "target_map", "default": True},
            {"id": "text", "label": "Text", "projection": "visible_text"},
            {"id": "structure", "label": "Structure", "projection": "structure"},
        ],
        "replay_policy": {
            "snapshot_replay": "coordinates_authoritative",
            "live_replay": "semantic_selectors_first_coordinates_advisory",
        },
        "site_fingerprint": site_fingerprint_for(blueprint, target_map),
    }


def build_web_snapshot_html(target_map: dict[str, Any]) -> str:
    screenshot = target_map.get("screenshot") if isinstance(target_map.get("screenshot"), dict) else {}
    dimensions = screenshot.get("dimensions") if isinstance(screenshot.get("dimensions"), dict) else {}
    image_path = "/artifact/" + str(screenshot.get("path") or "").lstrip("/")
    width = int(dimensions.get("width") or 1)
    height = int(dimensions.get("height") or 1)
    target_html = []
    # .web-target buttons are deliberately transparent proxy hit areas over a
    # frozen screenshot: the screenshot remains the visual truth, while real DOM
    # targets give annotation and replay code stable same-origin anchors.
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
        "@property --web-target-chase-angle{syntax:'<angle>';inherits:false;initial-value:0deg;}\n"
        "@keyframes web-target-chase-border{to{--web-target-chase-angle:360deg;}}\n"
        ".web-snapshot-stage{position:relative;display:block;line-height:0;}\n"
        f".web-snapshot-stage img{{display:block;width:{width}px;height:{height}px;}}\n"
        ".web-target{position:absolute;border:0;background:transparent;padding:0;cursor:crosshair;}\n"
        ".web-target::before{content:\"\";position:absolute;inset:-3px;padding:2px;border-radius:8px;"
        "background:conic-gradient(from var(--web-target-chase-angle),rgba(56,189,248,0.08) 0deg,"
        "#38bdf8 40deg,#93c5fd 70deg,#22d3ee 94deg,rgba(56,189,248,0.08) 140deg,"
        "rgba(56,189,248,0.08) 360deg);"
        "-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);"
        "-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;opacity:0;"
        "filter:drop-shadow(0 0 5px rgba(56,189,248,0.45));}\n"
        ".web-target:hover,.web-target:focus-visible{outline:0;background:transparent;}\n"
        ".web-target:hover::before,.web-target:focus-visible::before{opacity:1;"
        "animation:web-target-chase-border 3.9s linear infinite;}\n"
        "</style></head><body>\n"
        f'<div class="web-snapshot-stage" data-web-snapshot-stage="true" style="width:{width}px;height:{height}px">\n'
        f'<img src="{html.escape(image_path)}" width="{width}" height="{height}" alt="Captured web page snapshot">\n'
        f"{''.join(target_html)}\n"
        "</div>\n"
        "</body></html>\n"
    )


def build_web_snapshot_html_from_data(web_snapshot_data: dict[str, Any]) -> str:
    projections = (
        web_snapshot_data.get("projections")
        if isinstance(web_snapshot_data.get("projections"), dict)
        else {}
    )
    target_map = projections.get("target_map") if isinstance(projections.get("target_map"), dict) else None
    if not target_map:
        raise ValueError("web snapshot data is missing projections.target_map")
    return build_web_snapshot_html(target_map)


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
    artifact_keys = ["web_snapshot", "web_snapshot_data", "page_screenshot", "capture_log"]
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
        "artifacts": {
            key: repo_relative(paths[key])
            for key in artifact_keys
            if key in paths
        },
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def capture_url_stage(
    url: str,
    *,
    slug: str,
    output_dir: Path,
    session: str = "eba-url-stage",
    width: int = 1365,
    height: int = 900,
) -> Path:
    resolved_output = safe_stage_output_dir(output_dir)
    shutil.rmtree(resolved_output, ignore_errors=True)
    resolved_output.mkdir(parents=True, exist_ok=True)

    paths = {
        "web_snapshot": resolved_output / "web-snapshot.html",
        "web_snapshot_data": resolved_output / "web-snapshot-data.json",
        "page_screenshot": resolved_output / "page.full-page.png",
        "page_snapshot_tmp": resolved_output / ".page-snapshot.tmp.txt",
        "capture_log": resolved_output / "capture.log",
    }

    opened = False
    failed = False
    try:
        run_step(
            "open URL stage",
            command_for(session, "open", url, "--no-persistent"),
            paths["capture_log"],
        )
        opened = True
        run_step(
            "resize URL stage viewport",
            command_for(session, "resize", width, height),
            paths["capture_log"],
        )
        run_step(
            "settle URL stage",
            command_for(session, "run-code", SETTLE_SNIPPET),
            paths["capture_log"],
        )
        run_step(
            "hide obscuring elements",
            command_for(session, "run-code", HIDE_SNIPPET),
            paths["capture_log"],
        )
        blueprint_result = run_step(
            "extract web blueprint",
            command_for(session, "run-code", BLUEPRINT_SNIPPET),
            paths["capture_log"],
        )
        blueprint = parse_playwright_cli_result(blueprint_result.stdout)
        if not isinstance(blueprint, dict):
            raise RuntimeError("extract web blueprint did not return an object")
        run_step(
            "write page snapshot",
            command_for(session, "snapshot", paths["page_snapshot_tmp"]),
            paths["capture_log"],
        )
        page_snapshot = paths["page_snapshot_tmp"].read_text(encoding="utf-8")
        text_result = run_step(
            "extract visible text",
            command_for(session, "run-code", TEXT_SNIPPET),
            paths["capture_log"],
        )
        visible_text = parse_playwright_cli_result(text_result.stdout)
        run_step(
            "write full-page screenshot",
            command_for(session, "screenshot", paths["page_screenshot"], "--full-page"),
            paths["capture_log"],
        )
        screenshot_dimensions = png_dimensions(paths["page_screenshot"])
        web_snapshot_data = build_web_snapshot_data(
            blueprint,
            screenshot_dimensions=screenshot_dimensions,
            screenshot_path=repo_relative(paths["page_screenshot"]),
            visible_text=str(visible_text or ""),
            page_snapshot=page_snapshot,
        )
        write_json(paths["web_snapshot_data"], web_snapshot_data)
        paths["web_snapshot"].write_text(build_web_snapshot_html_from_data(web_snapshot_data), encoding="utf-8")
        paths["page_snapshot_tmp"].unlink(missing_ok=True)
        run_step(
            "restore page",
            command_for(session, "run-code", RESTORE_SNIPPET),
            paths["capture_log"],
        )
        return write_url_stage_manifest(
            output_dir=resolved_output,
            slug=slug,
            url=url,
            status="passed",
            viewport=blueprint.get("viewport") or {"width": width, "height": height},
            paths=paths,
            screenshot_dimensions=screenshot_dimensions,
        )
    except RuntimeError:
        failed = True
        raise
    finally:
        if opened:
            close_result = run_step(
                "close session",
                command_for(session, "close"),
                paths["capture_log"],
                check=False,
            )
            if failed and close_result.returncode != 0:
                print("[url-stage] close session failed after capture error", file=sys.stderr)
