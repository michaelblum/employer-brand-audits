#!/usr/bin/env python3
"""Assert the normalized workbench projection shape for Mermaid/composites."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from easy_audit_fixture import generate_easy_audit_fixture
from playwright_cli_workbench_server import build_collection
from workbench_projection import project_audit_manifest, project_matrix_manifest, project_workbench_manifest


REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_TMP_ROOT = REPO_ROOT / "artifacts"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fixture_manifest(root: Path) -> Path:
    page_dir = root / "fixture-page"
    page_dir.mkdir(parents=True, exist_ok=True)
    summary_path = page_dir / "artifact-summary.md"
    summary_path.write_text(
        """# Fixture Artifact Summary

```mermaid
flowchart TD
  capture[Capture] --> project[Project]
  project --> workbench[Workbench]
```
""",
        encoding="utf-8",
    )
    manifest_path = root / "manifest.json"
    write_json(
        manifest_path,
        {
            "status": "passed",
            "page_count": 1,
            "passed_count": 1,
            "pages": [
                {
                    "slug": "fixture-page",
                    "url": "https://example.com/careers/",
                    "status": "passed",
                    "target_used": "main",
                    "screenshot_dimensions": {
                        "viewport": {"width": 1365, "height": 900},
                        "full_page": {"width": 1365, "height": 2400},
                        "element": {"width": 900, "height": 600},
                    },
                    "artifacts": {
                        "viewport": str((page_dir / "viewport.png").relative_to(REPO_ROOT)),
                        "full_page": str((page_dir / "full-page.png").relative_to(REPO_ROOT)),
                        "element": str((page_dir / "element.png").relative_to(REPO_ROOT)),
                        "summary": str(summary_path.relative_to(REPO_ROOT)),
                        "url": str((page_dir / "url.txt").relative_to(REPO_ROOT)),
                        "manifest": str((page_dir / "manifest.json").relative_to(REPO_ROOT)),
                    },
                }
            ],
        },
    )
    return manifest_path


def url_stage_fixture_manifest(root: Path) -> Path:
    stage_dir = root / "url-stage-basic"
    stage_dir.mkdir(parents=True, exist_ok=True)
    web_snapshot = stage_dir / "web-snapshot.html"
    page_screenshot = stage_dir / "page.full-page.png"
    web_snapshot_data = stage_dir / "web-snapshot-data.json"
    capture_log = stage_dir / "capture.log"

    web_snapshot.write_text(
        """<!doctype html>
<html><body>
  <div data-web-snapshot-stage="true">
    <img src="/artifact/artifacts/url-stage/url-stage-basic/latest/page.full-page.png" alt="Captured web page snapshot">
    <button class="web-target" data-web-target-id="target-1" aria-label="Apply now"></button>
  </div>
</body></html>
""",
        encoding="utf-8",
    )
    page_screenshot.write_bytes(b"fixture screenshot bytes")
    write_json(
        web_snapshot_data,
        {
            "schema_version": "web_snapshot.v0",
            "source_url": "https://example.com/careers/",
            "visual": {
                "coordinate_space": "screenshot",
                "image": {
                    "path": str(page_screenshot.relative_to(REPO_ROOT)),
                    "dimensions": {"width": 1200, "height": 1600},
                },
                "viewport": {"width": 1200, "height": 900, "devicePixelRatio": 1},
                "document": {"width": 1200, "height": 1600},
            },
            "source_trees": {
                "dom": {"schema_version": "web_snapshot_dom_tree.v0", "root": {"id": "dom:document", "children": []}},
                "ax": {"schema_version": "web_snapshot_ax_tree.v0", "root": None, "nodes": []},
            },
            "projections": {
                "target_map": {
                    "schema_version": "url_stage_target_map.v0",
                    "coordinate_space": "screenshot",
                    "source_url": "https://example.com/careers/",
                    "screenshot": {
                        "path": str(page_screenshot.relative_to(REPO_ROOT)),
                        "dimensions": {"width": 1200, "height": 1600},
                    },
                    "targets": [
                        {
                            "id": "target-1",
                            "label": "Apply now",
                            "target_kind": "link",
                            "rect": {"x": 80, "y": 120, "width": 140, "height": 48},
                            "selector_candidates": ["#apply-now", "a.primary"],
                            "confidence": 0.91,
                        }
                    ],
                },
                "visible_text": {
                    "schema_version": "web_snapshot_visible_text.v0",
                    "lines": ["Apply now", "Engineering careers"],
                },
                "page_snapshot": {
                    "schema_version": "web_snapshot_page_snapshot.v0",
                    "text": "button Apply now [ref=e1]\n",
                },
            },
            "projection_catalog": {
                "target_map": {"coordinate_space": "screenshot"},
                "visible_text": {},
                "structure": {},
                "page_snapshot": {},
            },
            "ui_views": [
                {"id": "snapshot", "label": "Snapshot", "projection": "target_map"},
                {"id": "text", "label": "Text", "projection": "visible_text"},
                {"id": "structure", "label": "Structure", "projection": "structure"},
            ],
        },
    )
    capture_log.write_text("captured fixture\n", encoding="utf-8")

    manifest_path = stage_dir / "manifest.json"
    write_json(
        manifest_path,
        {
            "schema_version": "url_stage_capture.v0",
            "slug": "url-stage-basic",
            "url": "https://example.com/careers/",
            "status": "passed",
            "viewport": {"width": 1200, "height": 900, "devicePixelRatio": 1},
            "screenshot": {
                "path": str(page_screenshot.relative_to(REPO_ROOT)),
                "dimensions": {"width": 1200, "height": 1600},
            },
            "artifacts": {
                "web_snapshot": str(web_snapshot.relative_to(REPO_ROOT)),
                "page_screenshot": str(page_screenshot.relative_to(REPO_ROOT)),
                "web_snapshot_data": str(web_snapshot_data.relative_to(REPO_ROOT)),
                "capture_log": str(capture_log.relative_to(REPO_ROOT)),
            },
        },
    )
    return manifest_path


def assert_matrix_projection_shape(payload: dict[str, Any]) -> dict[str, Any]:
    artifacts = payload.get("artifacts") or []
    edges = payload.get("edges") or []
    groups = payload.get("artifact_groups") or []
    mermaid_id = "fixture-page:summary"
    group_id = "composite:page:fixture-page"
    mermaid = next((artifact for artifact in artifacts if artifact.get("id") == mermaid_id), None)
    require(isinstance(mermaid, dict), f"Missing Mermaid markdown artifact: {mermaid_id}")
    require(mermaid.get("type") == "markdown", "Mermaid fixture must remain a markdown artifact")
    require("render" in (mermaid.get("capabilities") or []), "Mermaid markdown must expose render capability")
    require(
        mermaid.get("facets", {}).get("diagram_kind") == "mermaid",
        "Mermaid markdown must expose facets.diagram_kind=mermaid",
    )
    require(
        "diagram" not in mermaid,
        "Mermaid markdown must not emit undocumented artifact.diagram metadata",
    )

    group = next((item for item in groups if item.get("id") == group_id), None)
    require(isinstance(group, dict), f"Missing projection-only composite group: {group_id}")
    require(
        "composites" not in (payload.get("facets") or {}),
        "facets.composites must not duplicate the canonical artifact_groups list",
    )
    require(group.get("kind") == "source_page_bundle", "Composite group kind drifted")
    expected_ids = {
        "fixture-page:element",
        "fixture-page:full_page",
        "fixture-page:summary",
        "fixture-page:viewport",
    }
    require(set(group.get("artifact_ids") or []) == expected_ids, "Composite group artifact ids drifted")
    require(
        not any(artifact.get("id") == group_id for artifact in artifacts),
        "Composite group must not be emitted as a durable artifact",
    )
    for artifact_id in expected_ids:
        require(
            any(
                edge.get("id") == f"edge:{group_id}:{artifact_id}"
                and edge.get("kind") == "contains"
                for edge in edges
            ),
            f"Missing contains edge for {artifact_id}",
        )
    return {
        "status": "passed",
        "mermaid_artifact_id": mermaid_id,
        "composite_group_id": group_id,
        "composite_artifact_ids": sorted(expected_ids),
    }


def assert_url_stage_projection_shape(payload: dict[str, Any]) -> dict[str, Any]:
    require(
        payload.get("source", {}).get("format") == "url_stage_capture",
        "URL stage source format drifted",
    )
    require(
        payload.get("source", {}).get("adapter") == "project_url_stage_manifest",
        "URL stage adapter drifted",
    )
    require(
        payload.get("source", {}).get("workbench_context") == {"artifact_control_policy": "read-only"},
        "URL stage should default to read-only type controls",
    )
    artifacts = payload.get("artifacts") or []
    edges = payload.get("edges") or []
    groups = payload.get("artifact_groups") or []
    resources = payload.get("resources") or []
    web_snapshot = next((artifact for artifact in artifacts if artifact.get("id") == "url-stage-basic:web_snapshot"), None)
    web_snapshot_data = next((artifact for artifact in artifacts if artifact.get("id") == "url-stage-basic:web_snapshot_data"), None)
    expected_artifact_ids = {
        "url-stage-basic:web_snapshot",
        "url-stage-basic:web_snapshot_data",
    }
    require(
        {artifact.get("id") for artifact in artifacts} == expected_artifact_ids,
        "URL stage projected artifact ids drifted",
    )
    require(isinstance(web_snapshot, dict), "Missing URL stage web snapshot artifact")
    require(web_snapshot.get("type") == "html", "URL stage web snapshot must project through HTML renderer")
    require(web_snapshot.get("kind") == "web_snapshot", "URL stage web snapshot semantic kind drifted")
    require(web_snapshot.get("slot") == "web.snapshot", "URL stage web snapshot slot drifted")
    require(web_snapshot.get("mime_type") == "text/html", "URL stage web snapshot MIME type drifted")
    require(web_snapshot.get("parent_ids") == ["url-stage-basic:web_snapshot_data"], "URL stage web snapshot parents drifted")
    require(web_snapshot.get("dimensions") == {"width": 1200, "height": 1600}, "URL stage web snapshot dimensions drifted")
    require("annotate" in (web_snapshot.get("capabilities") or []), "URL stage web snapshot should expose annotate")
    require("edit" not in (web_snapshot.get("capabilities") or []), "URL stage web snapshot should not expose edit")
    require(web_snapshot.get("facets", {}).get("target_count") == 1, "URL stage target count drifted")
    require(web_snapshot.get("facets", {}).get("coordinate_space") == "screenshot", "URL stage coordinate space drifted")
    require(web_snapshot.get("facets", {}).get("data_artifact_id") == "url-stage-basic:web_snapshot_data", "URL stage data artifact pointer drifted")
    require(isinstance(web_snapshot_data, dict), "Missing URL stage web snapshot data artifact")
    require(web_snapshot_data.get("type") == "json", "URL stage web snapshot data must project as json")
    require(web_snapshot_data.get("kind") == "web_snapshot_data", "URL stage web snapshot data kind drifted")
    require(web_snapshot_data.get("facets", {}).get("projection_count") == 4, "URL stage projection count drifted")
    require(web_snapshot_data.get("facets", {}).get("ui_view_ids") == ["snapshot", "text", "structure"], "URL stage UI views drifted")
    require(
        len([resource for resource in resources if resource.get("type") == "url"]) == 1,
        "URL stage URL resources must be deduplicated",
    )
    resource_slots = {
        resource.get("id"): resource.get("slot")
        for resource in resources
    }
    expected_support_resource_slots = {
        "resource:file:url-stage-basic:page_screenshot": "capture.full_page",
        "resource:file:url-stage-basic:capture_log": "debug.log",
    }
    for resource_id, slot in expected_support_resource_slots.items():
        require(resource_slots.get(resource_id) == slot, f"URL stage support resource drifted: {resource_id}")
        require(
            any(
                edge.get("id") == f"edge:{resource_id}:step:url-stage:url-stage-basic"
                and edge.get("kind") == "supports"
                for edge in edges
            ),
            f"Missing URL stage support edge for {resource_id}",
        )
    group = next((item for item in groups if item.get("id") == "composite:url-stage:url-stage-basic"), None)
    require(isinstance(group, dict), "Missing URL stage composite group")
    require(group.get("kind") == "web_snapshot_bundle", "URL stage composite kind drifted")
    require(set(group.get("artifact_ids") or []) == expected_artifact_ids, "URL stage composite artifact ids drifted")
    for parent_id in web_snapshot.get("parent_ids") or []:
        require(
            any(
                edge.get("id") == f"edge:url-stage-basic:web_snapshot:{parent_id}"
                and edge.get("kind") == "derived_from"
                for edge in edges
            ),
            f"Missing URL stage derived_from edge for {parent_id}",
        )
    for artifact_id in expected_artifact_ids:
        require(
            any(
                edge.get("id") == f"edge:composite:url-stage:url-stage-basic:{artifact_id}"
                and edge.get("kind") == "contains"
                for edge in edges
            ),
            f"Missing URL stage contains edge for {artifact_id}",
        )
    return {
        "status": "passed",
        "adapter": payload.get("source", {}).get("adapter"),
        "web_snapshot_artifact_id": web_snapshot.get("id"),
        "projected_artifact_ids": sorted(expected_artifact_ids),
    }


def assert_url_stage_server_collection(manifest_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    collection = build_collection(manifest_path, payload)
    artifacts = collection.get("artifacts") or []
    web_snapshot = next((artifact for artifact in artifacts if artifact.get("id") == "url-stage-basic:web_snapshot"), None)
    web_snapshot_data = next((artifact for artifact in artifacts if artifact.get("id") == "url-stage-basic:web_snapshot_data"), None)
    require(isinstance(web_snapshot, dict), "URL stage web snapshot missing from server collection")
    require(isinstance(web_snapshot_data, dict), "URL stage data missing from server collection")
    require(web_snapshot.get("dimensions") == {"width": 1200, "height": 1600}, "URL stage collection dimensions drifted")
    require(
        web_snapshot.get("facets", {}).get("ui_view_ids") == ["snapshot", "text", "structure"],
        "URL stage collection facets must retain UI view ids",
    )
    require(
        web_snapshot.get("facets", {}).get("data_artifact_id") == "url-stage-basic:web_snapshot_data",
        "URL stage collection facets must retain data artifact pointer",
    )
    return {
        "status": "passed",
        "artifact_ids": sorted(artifact.get("id") for artifact in artifacts),
    }


def assert_audit_projection_shape(payload: dict[str, Any]) -> dict[str, Any]:
    require(
        payload.get("source", {}).get("format") == "adr_002_audit_manifest",
        "ADR-002 adapter source format drifted",
    )
    steps = payload.get("workflow", {}).get("steps") or []
    artifacts = payload.get("artifacts") or []
    resources = payload.get("resources") or []
    edges = payload.get("edges") or []
    groups = payload.get("artifact_groups")
    facets = payload.get("facets") or {}
    report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-final-report"), None)
    intake_flow = next((artifact for artifact in artifacts if artifact.get("id") == "l0-intake-flow"), None)
    screenshot = next(
        (artifact for artifact in artifacts if artifact.get("id") == "l1-careers-screenshot"),
        None,
    )
    document_artifacts = {
        artifact.get("id"): artifact.get("type")
        for artifact in artifacts
        if artifact.get("type") in {"json", "text"}
    }
    step_ids = {step.get("id") for step in steps}
    expected_step_ids = {
        "l0-seed-intake",
        "l0-url-discovery",
        "l1-source-capture",
        "l2-kilos-analysis",
        "l3-synthesis",
        "l4-report",
    }
    artifact_ids = {artifact.get("id") for artifact in artifacts}
    require(isinstance(groups, list), "ADR-002 projection must emit artifact_groups as a list")
    require("composites" not in facets, "ADR-002 projection must not restore facets.composites")
    group_id = "composite:audit-report:l4-report"
    report_bundle = next((group for group in groups if group.get("id") == group_id), None)
    expected_report_bundle_ids = {
        "l0-intake-flow",
        "l0-source-urls",
        "l1-careers-text",
        "l1-careers-screenshot",
        "l2-kilos-json",
        "l2-kilos-analysis",
        "l3-synthesis-notes",
        "l4-final-report",
    }
    require(isinstance(report_bundle, dict), f"Missing ADR-002 report composite group: {group_id}")
    require(report_bundle.get("kind") == "audit_report_bundle", "ADR-002 report composite kind drifted")
    require(report_bundle.get("slot") == "audit.report.bundle", "ADR-002 report composite slot drifted")
    require(
        report_bundle.get("source") == {
            "kind": "audit_report_step",
            "step_id": "l4-report",
            "artifact_ids": ["l4-final-report"],
        },
        "ADR-002 report composite source drifted",
    )
    require(
        set(report_bundle.get("artifact_ids") or []) == expected_report_bundle_ids,
        "ADR-002 report composite artifact ids drifted",
    )
    require(
        not any(artifact.get("id") == group_id for artifact in artifacts),
        "ADR-002 report composite must not be emitted as a durable artifact",
    )
    for artifact_id in expected_report_bundle_ids:
        require(
            any(
                edge.get("id") == f"edge:{group_id}:{artifact_id}"
                and edge.get("kind") == "contains"
                for edge in edges
            ),
            f"Missing ADR-002 report composite contains edge for {artifact_id}",
        )
    require(payload.get("workflow", {}).get("status") == "complete", "ADR-002 workflow status drifted")
    require(step_ids == expected_step_ids, "Easy-audit step graph drifted")
    input_overlays = payload.get("workflow", {}).get("input_overlays")
    require(isinstance(input_overlays, list), "ADR-002 projection must expose workflow.input_overlays")
    require(
        [item.get("id") for item in input_overlays]
        == [
            "input:l0-seed-intake:company",
            "input:l0-seed-intake:domain_hint",
            "input:l0-seed-intake:workflow_template",
            "input:l0-seed-intake:talent_segment",
        ],
        "Easy-audit intake bounded input overlay ids drifted",
    )
    require(
        all(item.get("subtype") == "bounded_input" for item in input_overlays),
        "Easy-audit intake overlays must use bounded_input subtype",
    )
    require(
        all(item.get("anchor", {}).get("artifact_id") == "l0-intake-flow" for item in input_overlays),
        "Easy-audit intake overlays must anchor to the intake flow artifact",
    )
    require(
        payload.get("workflow", {}).get("template_id") == "employer-brand-audit.easy",
        "Easy-audit template id drifted",
    )
    require(
        payload.get("workflow", {}).get("talent_segment") == "Senior robotics engineers",
        "Easy-audit talent segment drifted",
    )
    require(
        len([resource for resource in resources if resource.get("type") == "url"]) == 1,
        "ADR-002 URL resources must be deduplicated",
    )
    require(isinstance(report, dict), "Missing ADR-002 report artifact")
    require(report.get("type") == "html", "ADR-002 report should project as html")
    require(report.get("kind") == "report", "ADR-002 artifact semantic type should be preserved as kind")
    require(report.get("mime_type") == "text/html", "ADR-002 report MIME type should be text/html")
    require("annotate" in (report.get("capabilities") or []), "ADR-002 HTML report should expose annotate")
    require("edit" not in (report.get("capabilities") or []), "ADR-002 HTML report should not expose edit")
    require("render" not in (report.get("capabilities") or []), "ADR-002 HTML report should not expose Mermaid render")
    require(
        "diagram_kind" not in (report.get("facets") or {}),
        "ADR-002 HTML report should not expose Mermaid diagram facets",
    )
    require(isinstance(screenshot, dict), "Missing ADR-002 screenshot artifact")
    require(screenshot.get("type") == "image", "ADR-002 screenshot should project as image")
    require(screenshot.get("parent_ids") == ["l0-source-urls"], "ADR-002 artifact parent_ids drifted")
    require(
        document_artifacts
        == {
            "l0-source-urls": "json",
            "l1-careers-text": "text",
            "l2-kilos-json": "json",
            "l3-synthesis-notes": "text",
        },
        "Easy-audit JSON/text projection drifted",
    )
    require(isinstance(intake_flow, dict), "Missing ADR-002 intake flow artifact")
    require(intake_flow.get("type") == "markdown", "ADR-002 intake flow should project as markdown")
    require(intake_flow.get("kind") == "intake_flow", "ADR-002 intake flow semantic kind should be preserved")
    require("render" in (intake_flow.get("capabilities") or []), "ADR-002 intake flow should expose Mermaid render")
    for artifact in (report, screenshot):
        projected_path = Path(str(artifact.get("path") or ""))
        require(not projected_path.is_absolute(), f"{artifact.get('id')} path must be repo-root-relative")
        require((REPO_ROOT / projected_path).exists(), f"{artifact.get('id')} path must resolve under repo root")
    require(
        any(
            edge.get("id") == "edge:step:l0-url-discovery:l1-source-capture"
            and edge.get("kind") == "depends_on"
            and edge.get("from") == "l1-source-capture"
            and edge.get("to") == "l0-url-discovery"
            for edge in edges
        ),
        "Missing ADR-002 step dependency edge",
    )
    require(
        any(
            edge.get("id") == "edge:l1-careers-screenshot:l0-source-urls"
            and edge.get("kind") == "derived_from"
            for edge in edges
        ),
        "Missing ADR-002 artifact provenance edge",
    )
    require(
        all("l0-url-discovery" not in (artifact.get("parent_ids") or []) for artifact in artifacts),
        "ADR-002 artifact parent_ids must not point at step ids",
    )
    for edge in edges:
        if edge.get("kind") == "derived_from":
            require(edge.get("to") in artifact_ids, "derived_from edges must point to artifact ids")
        if edge.get("kind") == "depends_on":
            require(edge.get("to") in step_ids, "depends_on edges must point to step ids")
    return {
        "status": "passed",
        "audit_manifest_adapter": payload.get("source", {}).get("adapter"),
        "report_artifact_id": report.get("id"),
        "screenshot_artifact_id": screenshot.get("id"),
        "document_projected_artifact_ids": sorted(document_artifacts),
    }


def assert_audit_server_collection(manifest_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    collection = build_collection(manifest_path, payload)
    artifacts = collection.get("artifacts") or []
    artifact_ids = {artifact.get("id") for artifact in artifacts}
    require(
        collection.get("source_format") == "adr_002_audit_manifest",
        "Server collection must preserve ADR-002 source format",
    )
    require(
        artifact_ids
        == {
            "l0-intake-flow",
            "l0-source-urls",
            "l1-careers-text",
            "l1-careers-screenshot",
            "l2-kilos-json",
            "l2-kilos-analysis",
            "l3-synthesis-notes",
            "l4-final-report",
        },
        "Server collection must expose projected ADR-002 image, markdown, HTML report, JSON, and text artifacts",
    )
    report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-final-report"), None)
    intake_flow = next((artifact for artifact in artifacts if artifact.get("id") == "l0-intake-flow"), None)
    screenshot = next((artifact for artifact in artifacts if artifact.get("id") == "l1-careers-screenshot"), None)
    source_urls = next((artifact for artifact in artifacts if artifact.get("id") == "l0-source-urls"), None)
    careers_text = next((artifact for artifact in artifacts if artifact.get("id") == "l1-careers-text"), None)
    kilos_json = next((artifact for artifact in artifacts if artifact.get("id") == "l2-kilos-json"), None)
    synthesis_notes = next((artifact for artifact in artifacts if artifact.get("id") == "l3-synthesis-notes"), None)
    require(isinstance(report, dict), "ADR-002 report missing from server collection")
    require(isinstance(intake_flow, dict), "ADR-002 intake flow missing from server collection")
    require(intake_flow.get("type") == "markdown", "ADR-002 intake flow collection type drifted")
    require("render" in (intake_flow.get("capabilities") or []), "ADR-002 intake flow render capability missing in collection")
    require(report.get("type") == "html", "ADR-002 report collection type drifted")
    require(report.get("path", "").endswith("l4-final-report.html"), "ADR-002 report collection path drifted")
    require("annotate" in (report.get("capabilities") or []), "ADR-002 report annotate capability missing in collection")
    require("render" not in (report.get("capabilities") or []), "ADR-002 HTML report should not expose render in collection")
    require(isinstance(screenshot, dict), "ADR-002 screenshot missing from server collection")
    require(screenshot.get("type") == "image", "ADR-002 screenshot collection type drifted")
    require(isinstance(source_urls, dict), "ADR-002 source URLs JSON missing from server collection")
    require(source_urls.get("type") == "json", "ADR-002 source URLs collection type drifted")
    require(isinstance(kilos_json, dict), "ADR-002 KILOS JSON missing from server collection")
    require(kilos_json.get("type") == "json", "ADR-002 KILOS JSON collection type drifted")
    require(isinstance(careers_text, dict), "ADR-002 careers text missing from server collection")
    require(careers_text.get("type") == "text", "ADR-002 careers text collection type drifted")
    require(isinstance(synthesis_notes, dict), "ADR-002 synthesis notes missing from server collection")
    require(synthesis_notes.get("type") == "text", "ADR-002 synthesis notes collection type drifted")
    require(collection.get("artifact_count") == len(artifacts), "Server collection artifact_count drifted")
    return {
        "status": "passed",
        "artifact_ids": sorted(artifact_ids),
    }


def main() -> int:
    ARTIFACT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=".workbench-projection-shape-", dir=ARTIFACT_TMP_ROOT))
    try:
        matrix_path = fixture_manifest(root)
        audit_path = generate_easy_audit_fixture(root / "easy-audit")
        url_stage_path = url_stage_fixture_manifest(root)
        matrix_payload = project_matrix_manifest(matrix_path)
        audit_payload = project_audit_manifest(audit_path)
        autodetected_matrix_payload = project_workbench_manifest(matrix_path)
        autodetected_audit_payload = project_workbench_manifest(audit_path)
        autodetected_url_stage_payload = project_workbench_manifest(url_stage_path)
        require(
            autodetected_matrix_payload.get("source", {}).get("adapter") == "project_matrix_manifest",
            "Workbench projection auto-detection did not select the matrix adapter",
        )
        require(
            autodetected_audit_payload.get("source", {}).get("adapter") == "project_audit_manifest",
            "Workbench projection auto-detection did not select the ADR-002 adapter",
        )
        require(
            autodetected_url_stage_payload.get("source", {}).get("adapter") == "project_url_stage_manifest",
            "Workbench projection auto-detection did not select the URL stage adapter",
        )
        result = {
            "status": "passed",
            "matrix": assert_matrix_projection_shape(matrix_payload),
            "audit_manifest": assert_audit_projection_shape(audit_payload),
            "url_stage": assert_url_stage_projection_shape(autodetected_url_stage_payload),
            "url_stage_server_collection": assert_url_stage_server_collection(
                url_stage_path,
                autodetected_url_stage_payload,
            ),
            "audit_server_collection": assert_audit_server_collection(audit_path, audit_payload),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Projection shape check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
