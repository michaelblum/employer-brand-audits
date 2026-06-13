#!/usr/bin/env python3
"""Assert the normalized workbench projection shape for Mermaid/composites."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from workbench_projection import project_matrix_manifest


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


def assert_projection_shape(payload: dict[str, Any]) -> dict[str, Any]:
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


def main() -> int:
    ARTIFACT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=".workbench-projection-shape-", dir=ARTIFACT_TMP_ROOT))
    try:
        payload = project_matrix_manifest(fixture_manifest(root))
        result = assert_projection_shape(payload)
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
