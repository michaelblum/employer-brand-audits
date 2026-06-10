# ADR-001: The Workflow Graph Is The UI

**Date:** 2026-06-10  
**Status:** Accepted  

---

## Context

During design, we recognised that the intake wizard, the live pipeline status view, the workflow editor, and the report surface all drew from the same underlying data: the audit manifest. Rather than building these as separate UI systems, we identified a unifying principle.

## Decision

The audit manifest's step graph is the single source of truth for all user-facing surfaces. Every UI mode is a different render of the same data — not a different system.

## The Principle

**One graph. Multiple render modes.**

| Render mode | What the user sees | What's happening |
|---|---|---|
| **Intake form** | Graph with unfilled nodes — pulsating rects, callout questions, live input cursors | `required_inputs[]` with `status: pending` |
| **Live ops** | Graph with animated state — nodes lighting up, progress indicators, log tail | Step `status` updating in real-time as pipeline runs |
| **View / clone** | Completed graph — artifacts at each node, provenance links, timestamps | Manifest read-only render |
| **Bounded edit** | Graph with selectable nodes — user points at a node, asks agent to mutate | Agent mediates all changes; guardrails are implicit in what the agent will accept |
| **Guided tour** | Graph as narrative — agent drives, callouts injected into live browser surfaces | L3 provenance data anchors annotations to real page elements |

All of these are the same renderer with different interaction modes toggled. None require a separate data model.

## Implications

### Manifest schema must support this from day one

Each step node in the manifest needs:
```json
{
  "id": "l1-text-capture",
  "name": "Page text capture",
  "description": "Extract prose and copy from selected pages as markdown",
  "status": "pending | running | complete | failed",
  "started_at": null,
  "completed_at": null,
  "required_inputs": [
    { "id": "target_urls", "label": "URLs to capture", "status": "pending", "value": null }
  ],
  "artifact_ids": [],
  "parent_step_ids": ["l0-url-discovery"]
}
```

This is cheap to add now and expensive to retrofit later.

### Progressive disclosure is structural, not designed

Steps with unfilled `required_inputs` render as locked. Steps whose `parent_step_ids` are not yet complete render as unavailable. The pipeline's dependency graph determines what the user can interact with — no separate UI logic needed.

### The agent mediates all mutations

There is no "free edit" mode. The user selects a node and makes a request in natural language. The agent interprets it, decides if it's within acceptable bounds, and makes the change. This means guardrails are a function of the agent's judgment, not a UI permission system. Deliberately lightweight.

### Diagram-with-blanks is V1.1, schema is V1

The conversational wizard (skill asking questions in sequence) ships in V1. The visual diagram-with-blanks render ships in V1.1 — it's a new renderer over the same data, not a migration. Getting the schema right in V1 is what makes V1.1 easy.

## What this is not

- Not a workflow engine (the pipeline is Python code, not a data-driven interpreter)
- Not a drag-and-drop flow builder (mutations are natural language → agent, not direct manipulation)
- Not a separate system for each surface (one manifest, one renderer, many modes)

## Related

- [Issue #2: V2 vision — browser as collaborative agent-human surface](https://github.com/michaelblum/employer-brand-audits/issues/2)
- ADR-002 (forthcoming): Audit manifest schema
