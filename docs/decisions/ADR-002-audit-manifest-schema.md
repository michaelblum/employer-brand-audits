# ADR-002: Audit Manifest Schema

**Date:** 2026-06-10  
**Status:** Accepted  

---

## Context

[ADR-001](ADR-001-workflow-graph-as-ui.md) established that the audit manifest's step graph is the single source of truth for every user-facing surface (intake, live ops, view/clone, bounded edit, guided tour). That ADR sketched a step node but left the full schema "forthcoming." This ADR pins it down, because the schema is what the pipeline writes, what every render mode reads, and what `save_artifact` validates against. Getting it consistent now is cheap; retrofitting it after code and reports depend on it is not.

ADR-001's inline example had one loose detail: an artifact's `parent_ids` pointed at a *step* id (`["l0-url-discovery"]`). That conflated two different relationships. This ADR resolves it.

## Decision

A manifest is one JSON file per audit (`manifest.json` in the audit directory). It has two node collections — **steps** (units of work, forming the DAG that drives the UI) and **artifacts** (immutable outputs, forming a provenance chain).

### Top-level

```json
{
  "schema_version": "1.0",
  "audit_id": "acme-corp-2026-06-10",
  "company": "Acme Corp",
  "domain": "acme.com",
  "template_id": "standard-audit",
  "talent_segment": "Technology & Product",
  "created_at": "2026-06-10T14:00:00Z",
  "steps": [ /* Step */ ],
  "artifacts": [ /* Artifact */ ]
}
```

`talent_segment` is nullable. `schema_version` exists so the renderer and migration code can branch on shape.

### Step

```json
{
  "id": "l1-text-capture",
  "layer": 1,
  "name": "Page text capture",
  "description": "Extract prose and copy from the selected careers pages as clean markdown",
  "status": "pending",
  "started_at": null,
  "completed_at": null,
  "error": null,
  "required_inputs": [
    { "id": "target_urls", "label": "URLs to capture", "status": "pending", "value": null }
  ],
  "artifact_ids": [],
  "parent_step_ids": ["l0-url-discovery"]
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable, kebab, convention `l{layer}-{slug}`. Never reused. |
| `layer` | int 0–5 | For render grouping; mirrors the layer model. |
| `name` | string | Short human label. |
| `description` | string | **Intent-addressable** (ADR-001): the durable *what*, agent-refined from raw user input. Drives the diagram label and runtime healing. |
| `status` | enum | `pending` \| `running` \| `complete` \| `failed` \| `blocked`. |
| `started_at` / `completed_at` | ISO 8601 \| null | |
| `error` | string \| null | Populated on `failed`/`blocked` for surfacing in live ops. |
| `required_inputs[]` | object[] | Each: `id`, `label`, `status` (`pending`\|`filled`), `value`. Unfilled inputs render the step as locked. |
| `artifact_ids[]` | string[] | Back-reference to artifacts this step produced. |
| `parent_step_ids[]` | string[] | Steps that must be `complete` before this step is available. **These are the DAG edges.** |

### Artifact

```json
{
  "id": "l1-careers-main-screenshot",
  "layer": 1,
  "type": "screenshot",
  "status": "complete",
  "created_at": "2026-06-10T14:05:00Z",
  "produced_by_step_id": "l1-screenshot-capture",
  "parent_ids": ["l0-urls"],
  "params": { "url": "https://careers.acme.com", "drive_file_id": "1AbC..." },
  "file_path": "artifacts/l1-careers-main-screenshot.png"
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string | Convention `l{layer}-{source}-{type}`. |
| `layer` | int 0–5 | |
| `type` | enum | `url_list` \| `text` \| `screenshot` \| `crop` \| `kilos_analysis` \| `synthesis` \| `report`. |
| `status` | enum | `pending` \| `complete` \| `failed`. (Artifacts don't have `running`/`blocked` — those are step states.) |
| `created_at` | ISO 8601 | |
| `produced_by_step_id` | string | The single step that created this artifact. |
| `parent_ids[]` | string[] | **Artifact ids only** — the upstream artifacts this one was derived from. This is the provenance chain. |
| `params` | object | Free-form. Holds the source URL, the Drive `fileId` (recorded after upload via the connected Drive MCP), crop rects, etc. |
| `file_path` | string | Relative to the audit directory. |

### The two-relationship rule (resolves ADR-001's ambiguity)

- **Step → step** dependency uses `parent_step_ids[]`. This is the DAG the UI walks to decide availability.
- **Artifact → artifact** provenance uses `parent_ids[]`, which references **artifact ids only**, never step ids.
- The artifact-to-step link is the single `produced_by_step_id`, with `Step.artifact_ids[]` as its inverse.

ADR-001's example (artifact `parent_ids: ["l0-url-discovery"]`, a step id) is **superseded** by this rule. The equivalent now is `produced_by_step_id` plus `parent_ids: ["l0-urls"]` (the artifact).

## Consequences

- **`save_artifact` is the one write path.** Every artifact — whether produced by Claude in Chrome (L0/L1), the skill's inline analysis (L2/L3), or a Python tool (stitched/cropped images, report) — is recorded through `save_artifact`. The manifest never distinguishes "MCP-produced" from "agent-produced" artifacts; producer identity lives only in `produced_by_step_id`. This is what lets the renderer treat all layers uniformly.
- **Provenance is queryable both ways.** Forward (what did this step produce?) via `artifact_ids`; backward (what was this derived from?) via `parent_ids`. The L4 report's rich citations walk `parent_ids` to the source `url_list`/`text` artifact and surface its `params.url`.
- **Selective re-runs are well-defined.** Re-running a layer means re-executing its steps and writing new artifacts; downstream artifacts whose `parent_ids` changed are stale and flagged. (The staleness sweep is implementation detail, not schema.)
- **The schema is additive.** New artifact `type`s or step fields extend the enums/objects without breaking the renderer, which is why `schema_version` is present from 1.0.

## Related

- [ADR-001: The Workflow Graph Is The UI](ADR-001-workflow-graph-as-ui.md) — the consumer of this schema
- [ADR-004: Layered Artifact DAG](ADR-004-layered-artifact-dag.md) — why layers and reuse exist at all
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
