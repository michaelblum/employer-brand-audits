# Publication Pipeline Reference Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reproducible publication pipeline pack from tracked KILOS data and staged capture records, then expose capture-pack, evidence-matrix, analysis-pack, report/deck/workbook, and L4 publication views through the existing ADR-002 workbench manifest path. The pipeline shape is the generic EVP client immersion and competitor messaging audit; runnable defaults use fictional sample profiles, while reference publications provide structural shape only. `--project-profile <profile.json>` must let the same minimum data shape be generated for an arbitrary company without inheriting reference-source labels or defaults.

**Architecture:** Keep the canonical records in a deterministic Python-generated publication pack and project them through the existing `steps[]` plus `artifacts[]` audit manifest contract. The first implementation uses fixture data and tracked `data/kilos-framework.json`; later capture ingestion reads URL-stage manifests as source artifacts. Workbench support stays adapter-based in `scripts/workbench_projection.py` so publication views are grouped without inventing a separate runtime.

**Tech Stack:** Python 3 standard library, ADR-002 audit manifests, tracked KILOS JSON, existing `./eba dev demo --fixture ...` route, existing workbench projection, focused Python tests, `git diff --check`, and `./eba dev validate` after implementation changes.

---

## File Structure

- Create `scripts/publication_pipeline_fixture.py`: deterministic publication-pack generator, KILOS loader, company profile loader, fixture records, ADR-002 manifest writer, and HTML/Markdown/JSON view writers.
- Create `data/publication-pipeline-profiles/sample-healthcare-evp.json`: tracked fictional sample profile for the default fixture seed.
- Create `tests/test_publication_pipeline_fixture.py`: fixture, schema, provenance, KILOS, projection, and CLI route coverage.
- Modify `scripts/eba_cli.py`: register `publication-pipeline` as a named fixture, add the new script to compile validation, and add the test to the validation ladder.
- Modify `scripts/workbench_projection.py`: generalize layer-4 artifact groups so report, deck, workbook, and L4 publication view bundles have accurate labels and slots.
- Modify `scripts/AGENTS.md`: record the local contract once publication-pipeline fixture and CLI behavior exist.
- Keep `docs/superpowers/specs/2026-06-18-publication-pipeline-reference-workflow.md` as the source spec for this work.

## Non-Goals

- Do not depend on `reference_publications/` at runtime; it is local-only source material.
- Do not generate binary DOCX/PPTX/XLSX in the first implementation slice.
- Do not publish images, push branches, open PRs, or update GitHub issues unless the user explicitly asks.
- Do not add a second workbench manifest format for publication packs.
- Do not route image bytes through prompts, tool arguments, or tool results.

## Task 1: Publication Pipeline Fixture Contract

**Files:**
- Create: `scripts/publication_pipeline_fixture.py`
- Create: `tests/test_publication_pipeline_fixture.py`

- [ ] **Step 1: Write failing fixture tests**

Create `tests/test_publication_pipeline_fixture.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.publication_pipeline_fixture import (
    REPO_ROOT,
    generate_publication_pipeline_fixture,
    load_kilos_terms,
)
from scripts.workbench_projection import project_audit_manifest


class PublicationPipelineFixtureTests(unittest.TestCase):
    def test_load_kilos_terms_uses_tracked_data(self) -> None:
        terms = load_kilos_terms(REPO_ROOT / "data" / "kilos-framework.json")

        self.assertEqual(len(terms), 29)
        self.assertEqual(terms[0]["framework_id"], "KILOS")
        self.assertEqual(terms[0]["pillar_id"], "K")
        self.assertEqual(terms[0]["factor_id"], "K1")
        self.assertIn("pillar_color", terms[0])

    def test_fixture_writes_full_publication_manifest(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["schema_version"], "adr-002.audit-manifest.v1")
        self.assertEqual(manifest["template_id"], "publication-pipeline.evp-client-immersion-competitor-audit")
        self.assertEqual(manifest["framework_id"], "KILOS")
        self.assertEqual(manifest["framework_version"], "1.0")
        self.assertNotIn("reference_publications", json.dumps(manifest))
        self.assertEqual(
            [step["id"] for step in manifest["steps"]],
            [
                "p0-project-frame",
                "p0-source-roster",
                "p1-capture-pack",
                "p2-evidence-matrix",
                "p3-analysis-pack",
                "p4-report-docx-view",
                "p4-audit-deck-view",
                "p4-data-workbook-view",
                "p4-l4-publication-view",
            ],
        )

    def test_fixture_preserves_evidence_lineage_to_publication_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            root = manifest_path.parent
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            required_files = [
                "project-frame.json",
                "source-roster.json",
                "capture-pack.json",
                "evidence-matrix.json",
                "analysis-pack.json",
                "report-docx-view.html",
                "audit-deck-view.html",
                "data-workbook-view.html",
                "l4-publication.html",
            ]
            for relative_path in required_files:
                self.assertTrue((root / relative_path).exists(), relative_path)

        artifacts_by_id = {artifact["id"]: artifact for artifact in manifest["artifacts"]}
        self.assertEqual(
            artifacts_by_id["p4-l4-publication"]["parent_ids"],
            ["p3-analysis-pack", "p2-evidence-matrix", "p1-capture-pack"],
        )

    def test_projection_groups_publication_views(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-pipeline")
            projection = project_audit_manifest(manifest_path)

        group_slots = [group["slot"] for group in projection["artifact_groups"]]
        self.assertIn("publication.report_docx.bundle", group_slots)
        self.assertIn("publication.audit_deck.bundle", group_slots)
        self.assertIn("publication.data_workbook.bundle", group_slots)
        self.assertIn("publication.l4_publication.bundle", group_slots)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```bash
python3 tests/test_publication_pipeline_fixture.py
```

Expected: failure because `scripts.publication_pipeline_fixture` does not exist.

- [ ] **Step 3: Implement the fixture generator**

Create `scripts/publication_pipeline_fixture.py` with these public entrypoints and record shapes:

```python
#!/usr/bin/env python3
"""Generate a deterministic publication pipeline fixture."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "publication-pipeline" / "latest"
KILOS_PATH = REPO_ROOT / "data" / "kilos-framework.json"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_kilos_terms(path: Path = KILOS_PATH) -> list[dict[str, Any]]:
    framework = json.loads(path.read_text(encoding="utf-8"))
    terms: list[dict[str, Any]] = []
    for pillar in framework["pillars"]:
        for factor in pillar["factors"]:
            terms.append(
                {
                    "framework_id": framework["framework"],
                    "framework_version": framework["version"],
                    "pillar_id": pillar["id"],
                    "pillar_name": pillar["name"],
                    "pillar_color": pillar["color"],
                    "factor_id": factor["id"],
                    "factor_name": factor["name"],
                    "theme_label": f"{pillar['name']} / {factor['name']}",
                    "aliases": factor.get("survey_labels", []),
                    "description": factor["description"],
                }
            )
    return terms
```

Implement helper functions named `project_frame()`, `source_roster()`, `capture_pack()`, `evidence_matrix(kilos_terms)`, `analysis_pack()`, `render_publication_html(title, body)`, `build_manifest()`, and `generate_publication_pipeline_fixture(output_dir=DEFAULT_OUTPUT_DIR)`.

The generated `build_manifest()` must include these artifact records:

```python
[
    {"id": "p0-project-frame", "layer": 0, "type": "publication_project", "file_path": "project-frame.json"},
    {"id": "p0-source-roster", "layer": 0, "type": "source_roster", "file_path": "source-roster.json"},
    {"id": "p1-capture-pack", "layer": 1, "type": "capture_pack", "file_path": "capture-pack.json"},
    {"id": "p2-evidence-matrix", "layer": 2, "type": "evidence_matrix", "file_path": "evidence-matrix.json"},
    {"id": "p3-analysis-pack", "layer": 3, "type": "analysis_pack", "file_path": "analysis-pack.json"},
    {"id": "p4-report-docx", "layer": 4, "type": "report_docx", "file_path": "report-docx-view.html"},
    {"id": "p4-audit-deck", "layer": 4, "type": "audit_deck", "file_path": "audit-deck-view.html"},
    {"id": "p4-data-workbook", "layer": 4, "type": "data_workbook", "file_path": "data-workbook-view.html"},
    {"id": "p4-l4-publication", "layer": 4, "type": "l4_publication", "file_path": "l4-publication.html"},
]
```

Each artifact record must also include `status`, `created_at`, `produced_by_step_id`, `parent_ids`, `params.slot`, and a short `card.summary`.

- [ ] **Step 4: Run fixture tests**

Run:

```bash
python3 tests/test_publication_pipeline_fixture.py
```

Expected: all tests pass except the projection grouping assertion until Task 2 lands.

## Task 2: Publication View Bundle Projection

**Files:**
- Modify: `scripts/publication_pipeline/projection_groups.py`
- Modify: `scripts/publication_pipeline/base_evp.py`
- Modify: `scripts/workbench_projection.py`
- Modify: `tests/test_publication_pipeline_structure.py`

- [ ] **Step 1: Declare publication grouping metadata from the manifest producer**

Keep publication view kind metadata in
`scripts/publication_pipeline/projection_groups.py` and have manifest builders
write it onto view artifacts:

```python
manifest_artifact(
    "p4-report-docx",
    4,
    "report_docx",
    ...,
    composite_group=publication_composite_group("report_docx"),
)
```

- [ ] **Step 2: Generalize `audit_report_artifact_groups` without publication imports**

Inside `audit_report_artifact_groups`, read
`artifact["facets"]["composite_group"]` when present. For legacy report
artifacts, keep the current `audit_report_bundle` behavior. The generic
projection module must not import `publication_pipeline.projection_groups`.

Use this shape for manifest-declared groups:

```python
groups.append(
    {
        "id": f"composite:manifest-declared:{step_id}:{artifact_id}",
        "kind": config["kind"],
        "label": f"{config['label']} bundle",
        "artifact_ids": group_artifact_ids,
        "edge_ids": [f"edge:composite:manifest-declared:{step_id}:{artifact_id}:{item_id}" for item_id in group_artifact_ids],
        "source": {
            "kind": "manifest_declared_composite_group",
            "step_id": step_id,
            "artifact_ids": [artifact_id],
        },
        "slot": config["slot"],
    }
)
```

- [ ] **Step 3: Run projection-focused tests**

Run:

```bash
python3 tests/test_publication_pipeline_fixture.py
python3 tests/test_easy_audit_fixture.py
```

Expected: publication groups exist and existing easy-audit report grouping still passes.

## Task 3: Fixture Command Surface And Validation

**Files:**
- Modify: `scripts/fixture_registry.py`
- Modify: `scripts/validation_registry.py`
- Modify: `scripts/eba_cli.py`
- Modify: `tests/test_publication_pipeline_fixture.py`

- [ ] **Step 1: Register the new fixture and validation commands through registries**

Add publication fixture generators to `scripts/fixture_registry.py`; keep
`scripts/eba_cli.py` importing the registry rather than individual fixture
families.

Add compile targets and focused tests to `scripts/validation_registry.py`; keep
`scripts/eba_cli.py` importing `COMPILE_TARGETS` and `validation_commands`
from the registry.

For example, fixture registration belongs in:

```python
FIXTURE_GENERATORS = {
    "publication-pipeline": generate_publication_pipeline_fixture,
}
```

Validation targets belong in:

```python
COMPILE_TARGETS = [
    "scripts/publication_pipeline_fixture.py",
]
```

- [ ] **Step 2: Add CLI route test**

Append this test to `tests/test_publication_pipeline_fixture.py`:

```python
    def test_publication_pipeline_fixture_is_registered_in_command_surface(self) -> None:
        from scripts.eba_cli import FIXTURE_GENERATORS, validation_commands
        from scripts.fixture_registry import FIXTURE_GENERATORS as REGISTRY_FIXTURES

        self.assertIs(FIXTURE_GENERATORS, REGISTRY_FIXTURES)
        self.assertIn("publication-pipeline", FIXTURE_GENERATORS)
        compile_command = validation_commands()[0]
        self.assertIn("scripts/publication_pipeline_fixture.py", compile_command)
        self.assertTrue(
            any(command[-1] == "tests/test_publication_pipeline_fixture.py" for command in validation_commands())
        )
```

- [ ] **Step 3: Run command-surface checks**

Run:

```bash
python3 tests/test_publication_pipeline_fixture.py
./eba dev situation --fixture publication-pipeline --json
```

Expected: JSON includes `artifact_workbench.manifest` ending in `artifacts/publication-pipeline/latest/manifest.json`.

## Task 4: Capture-Pack To Evidence-Matrix Importer

**Files:**
- Modify: `scripts/publication_pipeline_fixture.py`
- Create: `tests/test_publication_capture_pack.py`

- [ ] **Step 1: Add failing importer tests**

Create `tests/test_publication_capture_pack.py`:

```python
from __future__ import annotations

import unittest

from scripts.publication_pipeline_fixture import (
    evidence_items_from_capture_pack,
    source_artifacts_from_url_stage_manifest,
)


class PublicationCapturePackTests(unittest.TestCase):
    def test_source_artifacts_from_url_stage_manifest_preserves_stage_paths(self) -> None:
        manifest = {
            "schema_version": "url_stage_capture.v0",
            "slug": "patagonia-careers-live",
            "url": "https://www.patagonia.com/jobs/",
            "captured_at": "2026-06-18T12:00:00Z",
            "artifacts": {
                "web_snapshot_data": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json",
                "web_snapshot": "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot.html",
                "page_screenshot": "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png",
            },
        }

        source_artifacts = source_artifacts_from_url_stage_manifest(
            manifest,
            project_id="url-stage-capture-pack",
            entity_id="competitor-patagonia",
        )

        self.assertEqual(source_artifacts[0]["artifact_id"], "source:patagonia-careers-live")
        self.assertEqual(source_artifacts[0]["source_url"], "https://www.patagonia.com/jobs/")
        self.assertEqual(source_artifacts[0]["screenshot_path"], "artifacts/url-stage/patagonia-careers-live/latest/page.full-page.png")
        self.assertEqual(source_artifacts[0]["snapshot_path"], "artifacts/url-stage/patagonia-careers-live/latest/web-snapshot-data.json")

    def test_evidence_items_from_capture_pack_maps_kilos_and_contextual_items(self) -> None:
        capture_pack = {
            "source_artifacts": [
                {
                    "artifact_id": "source:patagonia-careers-live",
                    "project_id": "url-stage-capture-pack",
                    "entity_id": "competitor-patagonia",
                    "source_url": "https://www.patagonia.com/jobs/",
                }
            ],
            "excerpts": [
                {
                    "section": "careers_messaging",
                    "evidence_text": "We offer paid time off for activism and community action.",
                    "pillar_id": "I",
                    "factor_id": "I1",
                    "theme_label": "Impact / Meaningful Work for People",
                    "confidence": "high",
                },
                {
                    "section": "notes",
                    "evidence_text": "The page has a prominent video hero.",
                    "pillar_id": "",
                    "factor_id": "",
                    "theme_label": "visual context",
                    "confidence": "medium",
                },
            ],
        }

        items = evidence_items_from_capture_pack(capture_pack)

        self.assertEqual([item["evidence_id"] for item in items], ["evidence:001", "evidence:002"])
        self.assertEqual(items[0]["pillar_id"], "I")
        self.assertEqual(items[1]["kilos_status"], "non_kilos_context")
```

- [ ] **Step 2: Implement importer helpers**

Add to `scripts/publication_pipeline_fixture.py`:

```python
def source_artifacts_from_url_stage_manifest(
    manifest: dict[str, Any],
    *,
    project_id: str,
    entity_id: str,
) -> list[dict[str, Any]]:
    slug = str(manifest.get("slug") or "source")
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    return [
        {
            "artifact_id": f"source:{slug}",
            "project_id": project_id,
            "entity_id": entity_id,
            "source_url": str(manifest.get("url") or ""),
            "source_type": "careers_page",
            "captured_at": str(manifest.get("captured_at") or ""),
            "text_path": str(artifacts.get("visible_text") or ""),
            "screenshot_path": str(artifacts.get("page_screenshot") or ""),
            "snapshot_path": str(artifacts.get("web_snapshot_data") or artifacts.get("web_snapshot") or ""),
            "citation_label": slug.replace("-", " ").title(),
        }
    ]
```

Add `evidence_items_from_capture_pack(capture_pack)` that enumerates `capture_pack["excerpts"]`, uses the first `source_artifacts` record for provenance, writes IDs as `evidence:001`, `evidence:002`, preserves KILOS fields when present, and sets `kilos_status` to `non_kilos_context` when `pillar_id` or `factor_id` is blank.

- [ ] **Step 3: Wire importer tests into validation**

Add `tests/test_publication_capture_pack.py` to
`scripts/validation_registry.py` after
`tests/test_publication_pipeline_fixture.py`, then run:

```bash
python3 tests/test_publication_capture_pack.py
./eba dev validate
```

Expected: validation passes.

## Task 5: Demo Recipe And DOX Closeout

**Files:**
- Modify: `scripts/AGENTS.md`
- Modify: `scripts/eba_cli.py`

- [ ] **Step 1: Add the durable local contract**

In `scripts/AGENTS.md`, add a concise bullet under Local Contracts:

```markdown
- `./eba dev demo --fixture publication-pipeline` generates a deterministic
  publication-pipeline ADR-002 manifest from tracked KILOS data and fixture
  records. It must not depend on local-only `reference_publications/` files.
```

- [ ] **Step 2: Add a self-guided demo recipe for the fixture**

In `command_demo`, add a branch before the `easy-audit` branch:

```python
        if args.fixture == "publication-pipeline" or manifest.resolve() == (
            REPO_ROOT / "artifacts" / "publication-pipeline" / "latest" / "manifest.json"
        ).resolve():
            print("1. Confirm the workflow shows project frame, capture pack, evidence matrix, analysis pack, and four publication views.")
            print("2. Open Evidence Matrix and confirm every KILOS-coded item has pillar/factor provenance.")
            print("3. Open Analysis Pack and confirm findings link back to evidence ids.")
            print("4. Open L4 Publication and confirm it is a view over the same upstream records, not a separate source.")
```

- [ ] **Step 3: Run final verification**

Run:

```bash
python3 tests/test_publication_pipeline_fixture.py
python3 tests/test_publication_capture_pack.py
python3 tests/test_easy_audit_fixture.py
python3 scripts/workbench_projection_shape_check.py
./eba dev validate
./eba dev demo --fixture publication-pipeline --no-browser
git diff --check
```

Expected: every command exits `0`. The demo command prints a recipe for the publication pipeline fixture.

- [ ] **Step 4: Close the EBA turn**

Run:

```bash
./eba end --worker-id publication-pipeline-next
```

Expected: status is `closed`, the corridor passes, and the SOP sweep gate reports no blocking instruction drift.

## Execution Notes

- Use tracked `data/kilos-framework.json` as the runtime ontology.
- Use `reference_publications/` only as human-read local source material during design decisions.
- Keep the generated manifest ADR-002-shaped so `project_audit_manifest()` remains the workbench bridge.
- Treat fixture HTML views as inspectable projections for report/deck/workbook/L4 milestones; binary export can be a later plan after the record contract is working.
- Checkpoint only if the user accepts that option; do not push or publish during this plan without explicit approval.
