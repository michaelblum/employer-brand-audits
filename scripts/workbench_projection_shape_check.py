#!/usr/bin/env python3
"""Assert the normalized workbench projection shape for Mermaid/composites."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

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
    summary_path = page_dir / "review-summary.md"
    summary_path.write_text(
        """# Fixture Review Summary

```mermaid
flowchart TD
  capture[Capture] --> project[Project]
  project --> review[Review]
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


def audit_fixture_manifest(root: Path) -> Path:
    audit_dir = root / "audit-fixture"
    audit_dir.mkdir(parents=True, exist_ok=True)
    urls_path = audit_dir / "l0-urls.json"
    screenshot_path = audit_dir / "l1-careers-screenshot.png"
    analysis_path = audit_dir / "l2-analysis.md"
    report_path = audit_dir / "l4-report.md"
    urls_path.write_text('["https://example.com/careers/"]\n', encoding="utf-8")
    screenshot_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    analysis_path.write_text("# Analysis\n\nUseful source notes.\n", encoding="utf-8")
    report_path.write_text(
        """# Report

```mermaid
flowchart TD
  urls[URLs] --> capture[Capture]
  capture --> analysis[Analysis]
  analysis --> report[Report]
```
""",
        encoding="utf-8",
    )
    manifest_path = audit_dir / "manifest.json"
    write_json(
        manifest_path,
        {
            "schema_version": "1.0",
            "audit_id": "fixture-audit",
            "company": "Fixture Co",
            "domain": "example.com",
            "template_id": "standard-audit",
            "talent_segment": "Technology",
            "created_at": "2026-06-12T20:00:00Z",
            "steps": [
                {
                    "id": "l0-url-discovery",
                    "layer": 0,
                    "name": "URL discovery",
                    "description": "Collect source URLs.",
                    "status": "complete",
                    "started_at": "2026-06-12T20:00:00Z",
                    "completed_at": "2026-06-12T20:01:00Z",
                    "error": None,
                    "required_inputs": [],
                    "artifact_ids": ["l0-urls"],
                    "parent_step_ids": [],
                },
                {
                    "id": "l1-screenshot-capture",
                    "layer": 1,
                    "name": "Screenshot capture",
                    "description": "Capture the careers page.",
                    "status": "complete",
                    "started_at": "2026-06-12T20:01:00Z",
                    "completed_at": "2026-06-12T20:02:00Z",
                    "error": None,
                    "required_inputs": [],
                    "artifact_ids": ["l1-careers-screenshot"],
                    "parent_step_ids": ["l0-url-discovery"],
                },
                {
                    "id": "l2-analysis",
                    "layer": 2,
                    "name": "KILOS analysis",
                    "description": "Analyze captured source material.",
                    "status": "complete",
                    "started_at": "2026-06-12T20:02:00Z",
                    "completed_at": "2026-06-12T20:03:00Z",
                    "error": None,
                    "required_inputs": [],
                    "artifact_ids": ["l2-analysis"],
                    "parent_step_ids": ["l1-screenshot-capture"],
                },
                {
                    "id": "l4-report",
                    "layer": 4,
                    "name": "Report",
                    "description": "Render the final report.",
                    "status": "complete",
                    "started_at": "2026-06-12T20:03:00Z",
                    "completed_at": "2026-06-12T20:04:00Z",
                    "error": None,
                    "required_inputs": [],
                    "artifact_ids": ["l4-report"],
                    "parent_step_ids": ["l2-analysis"],
                },
            ],
            "artifacts": [
                {
                    "id": "l0-urls",
                    "layer": 0,
                    "type": "url_list",
                    "status": "complete",
                    "created_at": "2026-06-12T20:01:00Z",
                    "produced_by_step_id": "l0-url-discovery",
                    "parent_ids": [],
                    "card": {"summary": "Seed URL list", "tags": {"source": "example.com"}},
                    "params": {"url": "https://example.com/careers/"},
                    "file_path": "l0-urls.json",
                },
                {
                    "id": "l1-careers-screenshot",
                    "layer": 1,
                    "type": "screenshot",
                    "status": "complete",
                    "created_at": "2026-06-12T20:02:00Z",
                    "produced_by_step_id": "l1-screenshot-capture",
                    "parent_ids": ["l0-urls"],
                    "card": {"summary": "Careers page screenshot", "tags": {"source": "example.com"}},
                    "params": {"url": "https://example.com/careers/"},
                    "file_path": "l1-careers-screenshot.png",
                },
                {
                    "id": "l2-analysis",
                    "layer": 2,
                    "type": "kilos_analysis",
                    "status": "complete",
                    "created_at": "2026-06-12T20:03:00Z",
                    "produced_by_step_id": "l2-analysis",
                    "parent_ids": ["l1-careers-screenshot"],
                    "card": {"summary": "KILOS analysis", "tags": {"source": "example.com"}},
                    "params": {"url": "https://example.com/careers/"},
                    "file_path": "l2-analysis.md",
                },
                {
                    "id": "l4-report",
                    "layer": 4,
                    "type": "report",
                    "status": "complete",
                    "created_at": "2026-06-12T20:04:00Z",
                    "produced_by_step_id": "l4-report",
                    "parent_ids": ["l2-analysis"],
                    "card": {"summary": "Final report", "tags": {"source": "example.com"}},
                    "params": {"url": "https://example.com/careers/"},
                    "file_path": "l4-report.md",
                },
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
    edges = payload.get("edges") or []
    groups = payload.get("artifact_groups")
    facets = payload.get("facets") or {}
    report = next((artifact for artifact in artifacts if artifact.get("id") == "l4-report"), None)
    screenshot = next(
        (artifact for artifact in artifacts if artifact.get("id") == "l1-careers-screenshot"),
        None,
    )
    require(isinstance(groups, list), "ADR-002 projection must emit artifact_groups as a list")
    require(groups == [], "ADR-002 fixture must not derive artifact_groups from provenance parent_ids")
    require("composites" not in facets, "ADR-002 projection must not restore facets.composites")
    require(isinstance(report, dict), "Missing ADR-002 report artifact")
    require(report.get("type") == "markdown", "ADR-002 report should project as markdown")
    require(report.get("kind") == "report", "ADR-002 artifact semantic type should be preserved as kind")
    require("render" in (report.get("capabilities") or []), "ADR-002 Mermaid report should expose render")
    require(
        report.get("facets", {}).get("diagram_kind") == "mermaid",
        "ADR-002 Mermaid report should expose facets.diagram_kind=mermaid",
    )
    require(isinstance(screenshot, dict), "Missing ADR-002 screenshot artifact")
    require(screenshot.get("type") == "image", "ADR-002 screenshot should project as image")
    require(screenshot.get("parent_ids") == ["l0-urls"], "ADR-002 artifact parent_ids drifted")
    require(
        any(
            edge.get("id") == "edge:step:l0-url-discovery:l1-screenshot-capture"
            and edge.get("kind") == "depends_on"
            and edge.get("from") == "l1-screenshot-capture"
            and edge.get("to") == "l0-url-discovery"
            for edge in edges
        ),
        "Missing ADR-002 step dependency edge",
    )
    require(
        any(
            edge.get("id") == "edge:l1-careers-screenshot:l0-urls"
            and edge.get("kind") == "derived_from"
            for edge in edges
        ),
        "Missing ADR-002 artifact provenance edge",
    )
    require(
        all("l0-url-discovery" not in (artifact.get("parent_ids") or []) for artifact in artifacts),
        "ADR-002 artifact parent_ids must not point at step ids",
    )
    require(
        any(step.get("id") == "l1-screenshot-capture" for step in steps),
        "Missing ADR-002 projected workflow step",
    )
    return {
        "status": "passed",
        "audit_manifest_adapter": payload.get("source", {}).get("adapter"),
        "report_artifact_id": report.get("id"),
        "screenshot_artifact_id": screenshot.get("id"),
    }


def main() -> int:
    ARTIFACT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=".workbench-projection-shape-", dir=ARTIFACT_TMP_ROOT))
    try:
        matrix_path = fixture_manifest(root)
        audit_path = audit_fixture_manifest(root)
        matrix_payload = project_matrix_manifest(matrix_path)
        audit_payload = project_audit_manifest(audit_path)
        autodetected_audit_payload = project_workbench_manifest(audit_path)
        require(
            autodetected_audit_payload.get("source", {}).get("adapter") == "project_audit_manifest",
            "Workbench projection auto-detection did not select the ADR-002 adapter",
        )
        result = {
            "status": "passed",
            "matrix": assert_matrix_projection_shape(matrix_payload),
            "audit_manifest": assert_audit_projection_shape(audit_payload),
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
