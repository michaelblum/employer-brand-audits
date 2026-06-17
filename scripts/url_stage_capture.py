#!/usr/bin/env python3
"""Capture a URL into a durable workbench web snapshot artifact."""

from __future__ import annotations

import html
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
    image_path = "/artifact/" + str(screenshot.get("path") or "").lstrip("/")
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
        "blueprint": resolved_output / "web-blueprint.json",
        "target_map": resolved_output / "target-map.json",
        "web_snapshot": resolved_output / "web-snapshot.html",
        "page_screenshot": resolved_output / "page.full-page.png",
        "visible_text": resolved_output / "visible-text.txt",
        "page_snapshot": resolved_output / "page-snapshot.txt",
        "capture_log": resolved_output / "capture.log",
        "settle_stdout": resolved_output / "settle.stdout.txt",
        "hide_stdout": resolved_output / "hide-obscuring.stdout.txt",
        "restore_stdout": resolved_output / "restore-page.stdout.txt",
        "blueprint_stdout": resolved_output / "web-blueprint.stdout.txt",
        "visible_text_stdout": resolved_output / "visible-text.stdout.txt",
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
            stdout_path=paths["settle_stdout"],
        )
        run_step(
            "hide obscuring elements",
            command_for(session, "run-code", HIDE_SNIPPET),
            paths["capture_log"],
            stdout_path=paths["hide_stdout"],
        )
        blueprint_result = run_step(
            "extract web blueprint",
            command_for(session, "run-code", BLUEPRINT_SNIPPET),
            paths["capture_log"],
            stdout_path=paths["blueprint_stdout"],
        )
        blueprint = parse_playwright_cli_result(blueprint_result.stdout)
        if not isinstance(blueprint, dict):
            raise RuntimeError("extract web blueprint did not return an object")
        write_json(paths["blueprint"], blueprint)
        run_step(
            "write page snapshot",
            command_for(session, "snapshot", paths["page_snapshot"]),
            paths["capture_log"],
        )
        text_result = run_step(
            "extract visible text",
            command_for(session, "run-code", TEXT_SNIPPET),
            paths["capture_log"],
            stdout_path=paths["visible_text_stdout"],
        )
        visible_text = parse_playwright_cli_result(text_result.stdout)
        paths["visible_text"].write_text(str(visible_text or ""), encoding="utf-8")
        run_step(
            "write full-page screenshot",
            command_for(session, "screenshot", paths["page_screenshot"], "--full-page"),
            paths["capture_log"],
        )
        screenshot_dimensions = png_dimensions(paths["page_screenshot"])
        target_map = build_target_map(
            blueprint,
            screenshot_dimensions=screenshot_dimensions,
            screenshot_path=repo_relative(paths["page_screenshot"]),
        )
        write_json(paths["target_map"], target_map)
        paths["web_snapshot"].write_text(build_web_snapshot_html(target_map), encoding="utf-8")
        run_step(
            "restore page",
            command_for(session, "run-code", RESTORE_SNIPPET),
            paths["capture_log"],
            stdout_path=paths["restore_stdout"],
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
