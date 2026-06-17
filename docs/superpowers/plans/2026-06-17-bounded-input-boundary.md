# Bounded Input Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the bounded-input and workflow-pairing behavior from ambient projection, server, and app-shell logic into explicit boundaries without weakening the current workbench behavior.

**Architecture:** Keep generated workflow input projection in Python, saved-state sanitization in the workbench server, and browser interaction in JavaScript, but move each into a named boundary with focused tests. Do not start with broad file decomposition; split large files only when a new boundary owns real behavior.

**Tech Stack:** Python 3 standard library/unittest, browser-loaded JavaScript primitives, Node checks, Playwright CLI workbench smoke, `./eba dev validate`.

---

### Task 1: Python Bounded Input Contract

**Files:**
- Create: `scripts/workbench_bounded_input.py`
- Modify: `scripts/workbench_projection.py`
- Modify: `scripts/playwright_cli_workbench_server.py`
- Test: `tests/test_workbench_bounded_input.py`
- Update if contract changes: `scripts/AGENTS.md`

- [x] **Step 1: Write failing projection-contract tests**

Add tests proving:

```python
from scripts.workbench_bounded_input import (
    bounded_input_key,
    bounded_input_overlay_definition,
    bounded_input_state,
    clean_bounded_input_overlay,
)
```

Expected missing-module failure:

```bash
python3 tests/test_workbench_bounded_input.py
```

- [x] **Step 2: Extract projection definition helpers**

Move the current `workflow_input_overlay()` and `workflow_input_overlays_for_step()` behavior behind:

```python
bounded_input_overlay_definition(step_id: str, item: Any) -> dict[str, Any] | None
bounded_input_overlay_definitions_for_step(step_id: str, required_inputs: list[Any]) -> list[dict[str, Any]]
```

Keep emitted ids, `workflow_input` anchors, selector candidates, options, default values, and `target_link` passthrough identical.

- [x] **Step 3: Extract server sanitization helpers**

Move the current bounded-input saved-state behavior behind:

```python
bounded_input_key(overlay: dict[str, Any]) -> tuple[str, str]
bounded_input_value(overlay: dict[str, Any] | None, default: Any = None) -> str
clean_bounded_input_overlay(overlay: dict[str, Any], artifact_ids: set[str], definition_keys: set[tuple[str, str]]) -> dict[str, Any] | None
bounded_input_state(definitions: list[dict[str, Any]], overlays: list[dict[str, Any]]) -> dict[str, Any]
```

`playwright_cli_workbench_server.py` should delegate to these helpers and keep annotation cleaning local.

- [x] **Step 4: Verify Task 1**

Run:

```bash
python3 tests/test_workbench_bounded_input.py
python3 tests/test_easy_audit_fixture.py
python3 -m unittest tests.test_artifact_workbench_browser_control.WorkbenchBrowserControlTest.test_workbench_state_accepts_bounded_input_overlays_for_projected_inputs
python3 -m py_compile scripts/workbench_bounded_input.py scripts/workbench_projection.py scripts/playwright_cli_workbench_server.py
```

- [x] **Step 5: Checkpoint**

Commit and push with title:

```bash
git commit -m "Extract bounded input Python contract"
git push -u origin workbench/bounded-input-boundary
```

### Task 2: Browser Workflow Pairing Controller

**Files:**
- Create: `scripts/artifacts/core/workflow_pairing.js`
- Modify: `scripts/artifact_workbench/app.js`
- Modify: `scripts/playwright_cli_workbench_server.py` asset manifest if needed
- Test: `tests/workflow_pairing_check.js`
- Update if asset boundary changes: `scripts/AGENTS.md` or `scripts/artifacts/AGENTS.md`

- [x] **Step 1: Write failing browser primitive test**

The test should require `scripts/artifacts/core/workflow_pairing.js` and prove it can:

```javascript
workflowPairing.definitionForArtifact(definitions, artifact)
workflowPairing.domAnchorForDefinition(definition)
workflowPairing.targetLinkOptionsForDefinition(definition)
workflowPairing.selectorCandidatesForDefinition(definition)
```

Expected missing-module failure:

```bash
node tests/workflow_pairing_check.js
```

- [x] **Step 2: Extract pure pairing helpers from `app.js`**

Move selector normalization, definition selection, anchor creation, and target-link option selection out of the app shell. Keep DOM rendering, effect execution, persistence, and lifecycle scheduling in `app.js`.

- [x] **Step 3: Verify Task 2**

Run:

```bash
node tests/workflow_pairing_check.js
node --check scripts/artifacts/core/workflow_pairing.js
node --check scripts/artifact_workbench/app.js
node tests/workbench_shell_check.js
node tests/artifact_registry_check.js
```

- [x] **Step 4: Live smoke**

Run:

```bash
./eba dev demo
python3 scripts/playwright_cli_browser.py run-code scripts/playwright-snippets/artifact-workbench-bounded-input-check.js --session eba-workbench
```

- [x] **Step 5: Checkpoint**

Commit and push with title:

```bash
git commit -m "Extract workflow pairing browser helpers"
git push
```

### Task 3: Targeted Large-File Split Only If Boundary Is Real

**Files:**
- Candidate modify: `scripts/workbench_projection.py`
- Candidate modify: `scripts/playwright_cli_workbench_server.py`
- Candidate modify: `scripts/artifact_workbench/app.js`
- Candidate tests: focused tests touched in Tasks 1 and 2

- [ ] **Step 1: Re-measure remaining large-file responsibilities**

Run:

```bash
wc -l scripts/workbench_projection.py scripts/playwright_cli_workbench_server.py scripts/artifact_workbench/app.js
rg -n "bounded_input|workflow_input|workflowPairing|targetLinkOptionsForWorkflowDefinition" scripts tests
```

- [ ] **Step 2: Split only behavior that now has an owner**

Allowed splits:

- Move remaining Python bounded-input imports/wrappers into `scripts/workbench_bounded_input.py`.
- Move remaining browser pairing selection/helpers into `scripts/artifacts/core/workflow_pairing.js`.
- Leave unrelated projection, server route, and app-shell orchestration in place.

- [ ] **Step 3: Full branch verification**

Run:

```bash
./eba dev validate
./eba dev demo
python3 scripts/playwright_cli_browser.py run-code scripts/playwright-snippets/artifact-workbench-bounded-input-check.js --session eba-workbench
```

- [ ] **Step 4: Final checkpoint and PR readiness**

Commit, push, and inspect:

```bash
git status --short --branch
git log --oneline main..HEAD
gh pr create --fill
```
