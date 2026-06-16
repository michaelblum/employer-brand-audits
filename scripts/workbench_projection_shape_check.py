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
    html_report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-final-report-html"), None)
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
        "l0-url-discovery",
        "l1-source-capture",
        "l2-kilos-analysis",
        "l3-synthesis",
        "l4-report",
    }
    artifact_ids = {artifact.get("id") for artifact in artifacts}
    require(isinstance(groups, list), "ADR-002 projection must emit artifact_groups as a list")
    require(groups == [], "ADR-002 fixture must not derive artifact_groups from provenance parent_ids")
    require("composites" not in facets, "ADR-002 projection must not restore facets.composites")
    require(payload.get("workflow", {}).get("status") == "complete", "ADR-002 workflow status drifted")
    require(step_ids == expected_step_ids, "Easy-audit step graph drifted")
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
    require(report.get("type") == "markdown", "ADR-002 report should project as markdown")
    require(report.get("kind") == "report", "ADR-002 artifact semantic type should be preserved as kind")
    require("diagram" not in report, "ADR-002 Mermaid report must not emit artifact.diagram metadata")
    require("render" in (report.get("capabilities") or []), "ADR-002 Mermaid report should expose render")
    require(
        report.get("facets", {}).get("diagram_kind") == "mermaid",
        "ADR-002 Mermaid report should expose facets.diagram_kind=mermaid",
    )
    require(isinstance(html_report, dict), "Missing ADR-002 HTML report artifact")
    require(html_report.get("type") == "html", "ADR-002 HTML report should project as html")
    require("annotate" in (html_report.get("capabilities") or []), "ADR-002 HTML report should expose annotate")
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
            "l0-source-urls",
            "l1-careers-text",
            "l1-careers-screenshot",
            "l2-kilos-json",
            "l2-kilos-analysis",
            "l3-synthesis-notes",
            "l4-final-report",
            "l4-final-report-html",
        },
        "Server collection must expose projected ADR-002 image, markdown, HTML, JSON, and text artifacts",
    )
    report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-final-report"), None)
    html_report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-final-report-html"), None)
    screenshot = next((artifact for artifact in artifacts if artifact.get("id") == "l1-careers-screenshot"), None)
    source_urls = next((artifact for artifact in artifacts if artifact.get("id") == "l0-source-urls"), None)
    careers_text = next((artifact for artifact in artifacts if artifact.get("id") == "l1-careers-text"), None)
    kilos_json = next((artifact for artifact in artifacts if artifact.get("id") == "l2-kilos-json"), None)
    synthesis_notes = next((artifact for artifact in artifacts if artifact.get("id") == "l3-synthesis-notes"), None)
    require(isinstance(report, dict), "ADR-002 report missing from server collection")
    require(report.get("type") == "markdown", "ADR-002 report collection type drifted")
    require("render" in (report.get("capabilities") or []), "ADR-002 report render capability missing in collection")
    require(isinstance(html_report, dict), "ADR-002 HTML report missing from server collection")
    require(html_report.get("type") == "html", "ADR-002 HTML report collection type drifted")
    require("annotate" in (html_report.get("capabilities") or []), "ADR-002 HTML report annotate capability missing in collection")
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
        matrix_payload = project_matrix_manifest(matrix_path)
        audit_payload = project_audit_manifest(audit_path)
        autodetected_matrix_payload = project_workbench_manifest(matrix_path)
        autodetected_audit_payload = project_workbench_manifest(audit_path)
        require(
            autodetected_matrix_payload.get("source", {}).get("adapter") == "project_matrix_manifest",
            "Workbench projection auto-detection did not select the matrix adapter",
        )
        require(
            autodetected_audit_payload.get("source", {}).get("adapter") == "project_audit_manifest",
            "Workbench projection auto-detection did not select the ADR-002 adapter",
        )
        result = {
            "status": "passed",
            "matrix": assert_matrix_projection_shape(matrix_payload),
            "audit_manifest": assert_audit_projection_shape(audit_payload),
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
