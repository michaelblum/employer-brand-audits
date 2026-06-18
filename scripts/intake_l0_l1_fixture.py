#!/usr/bin/env python3
"""Generate a blank L0/L1 intake workflow fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.url_stage_capture import REPO_ROOT
except ModuleNotFoundError:
    from url_stage_capture import REPO_ROOT


DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "intake-l0-l1" / "blank" / "latest"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        return str(resolved.relative_to(REPO_ROOT))
    return str(path)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def intake_anchor() -> dict[str, Any]:
    return {
        "artifact_id": "l0-intake-flow",
        "selector_candidates": [
            "[data-workflow-step-id=\"l0-seed-intake\"]",
            "g.node[data-node=\"true\"][data-id=\"intake\"]",
        ],
    }


def intake_markdown() -> str:
    return """# L0 Intake

```mermaid
flowchart TB
  intake["L0 seed intake<br/>blank bounded inputs"]
  ready["User says ready in chat"]
  discover["L0 URL discovery"]
  capture["L1 source capture<br/>text + screenshot + web snapshot"]
  intake --> ready --> discover --> capture
```

Fill the bounded input overlay, then tell the agent `ready in workbench`.
"""


def blank_input(input_id: str, label: str, input_type: str = "text", **extra: Any) -> dict[str, Any]:
    return {
        "id": input_id,
        "label": label,
        "status": "pending",
        "value": None,
        "input_type": input_type,
        "artifact_id": "l0-intake-flow",
        "anchor": intake_anchor(),
        **extra,
    }


def build_manifest() -> dict[str, Any]:
    required_inputs = [
        blank_input("company", "Company"),
        blank_input("domain_hint", "Domain or careers URL"),
        blank_input(
            "workflow_template",
            "Workflow template",
            "select",
            value="standard-audit",
            options=[
                {"value": "standard-audit", "label": "Standard audit"},
                {"value": "tech-talent-audit", "label": "Tech talent audit"},
            ],
        ),
        blank_input("talent_segment", "Talent segment or scope"),
    ]
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": "intake-l0-l1-blank",
        "company": "Blank intake",
        "domain": "",
        "template_id": "intake-l0-l1",
        "talent_segment": "",
        "status": "pending",
        "created_at": "2026-06-18T00:00:00Z",
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "mermaid_source_visibility": "preview-hidden",
        },
        "required_inputs": required_inputs,
        "steps": [
            {
                "id": "l0-seed-intake",
                "layer": 0,
                "name": "L0 seed intake",
                "description": "Collect blank bounded inputs; the agent reads saved overlay values after the user says ready.",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "required_inputs": required_inputs,
                "artifact_ids": ["l0-intake-flow"],
                "parent_step_ids": [],
            },
            {
                "id": "l0-url-discovery",
                "layer": 0,
                "name": "L0 URL discovery",
                "description": "Derive and probe likely careers entry points from the filled intake values.",
                "status": "blocked",
                "started_at": None,
                "completed_at": None,
                "required_inputs": ["company", "domain_hint"],
                "artifact_ids": [],
                "parent_step_ids": ["l0-seed-intake"],
            },
            {
                "id": "l1-source-capture",
                "layer": 1,
                "name": "L1 source capture",
                "description": "Capture text, screenshot, and web snapshot evidence from selected L0 URLs.",
                "status": "blocked",
                "started_at": None,
                "completed_at": None,
                "required_inputs": [],
                "artifact_ids": [],
                "parent_step_ids": ["l0-url-discovery"],
            },
        ],
        "artifacts": [
            {
                "id": "l0-intake-flow",
                "layer": 0,
                "type": "intake_flow",
                "status": "pending",
                "created_at": "2026-06-18T00:00:00Z",
                "produced_by_step_id": "l0-seed-intake",
                "parent_ids": [],
                "file_path": "l0-intake-flow.md",
                "params": {"slot": "intake.flow"},
                "card": {"summary": "Blank L0/L1 intake", "tags": {"layer": "L0"}},
            }
        ],
    }


def generate_intake_l0_l1_fixture(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "l0-intake-flow.md").write_text(intake_markdown(), encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_manifest())
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = generate_intake_l0_l1_fixture(args.output_dir)
    payload = {
        "status": "generated",
        "fixture": "intake-l0-l1",
        "manifest": repo_relative(manifest_path),
        "artifact_root": repo_relative(manifest_path.parent),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Generated intake-l0-l1 fixture: {payload['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
