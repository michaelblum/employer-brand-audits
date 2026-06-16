# Employer Brand Audits Agent Entry Point

This is the provider-agnostic startup surface for agent sessions in this repo.
Provider-specific files such as `.claude/CLAUDE.md` should only point here.

## Start Here

- Read this file first.
- Use `./eba dev situation --json` for current repo and workbench state.
- If you did not receive an `./eba begin` turn packet at session start, manually
  run `./eba begin --worker-id <stable-id>` before `./eba dev validate`,
  substantive repo edits, or interactive workbench commands such as `click`,
  `fill`, or `press`. View-only workbench/demo refreshes may use
  `./eba dev demo` or `./eba dev workbench ...` without opening a turn.
- After an active turn exists, include its `EBA-Sig` (`<worker-id>/<turn-id>`)
  in the first substantive session response and final/checkpoint responses.
- Before editing, follow the DOX Read Before Editing chain for the paths you
  expect to touch.
- Use `./eba dev validate` before checkpointing substantive code changes.
- Use `./eba dev demo` when recent work is tangible and the user should be able
  to inspect it directly.
- Architectural decisions live in `docs/decisions/ADR-*.md`.
- Workflow and implementation plans live in `docs/superpowers/`.

## Stack

This project is a provider-flexible agent workflow prototype for Employer Brand
Audits. It has a Python mechanical layer, Playwright CLI browser capture, an
MCP imaging server, and a local workflow artifact workbench.

- MCP server and image processing: `mcp-server/`
- MCP tests: `mcp-server/tests/`
- Browser automation: Playwright CLI and thin repo wrappers only
- Workflow artifact workbench implementation: `scripts/playwright_cli_workbench_server.py`,
  `scripts/playwright_cli_workbench_gate.py`, and `scripts/workflow_artifact_workbench/`
- Command surface for agents: `./eba dev ...`

## Hard Invariants

- Do not discard or overwrite user changes for workflow hygiene.
- Do not use Claude in Chrome, `computer` screenshot, `zoom`, or
  provider-specific browser-control tools for audit execution.
- Playwright CLI is the browser boundary. Checked-in JavaScript snippets
  executed through Playwright CLI are allowed when CLI commands are not
  expressive enough.
- Image bytes stay on disk. Do not route base64 image payloads through model
  prompts, tool arguments, or tool results.
- Viewer code owns interaction, centering, and zoom bounds. Artifact processing
  owns image normalization, rendered-height caps, codec policy, and subtype
  overrides.
- Do not attribute commits, issue comments, PR descriptions, release notes, or
  project docs to a specific AI provider.

## Project SOP

Use `docs/superpowers/project-sop.md` for standing operating rules. The short
version:

- SOP changes require explicit human approval and an `SOP sweep` as defined in
  `docs/superpowers/project-sop.md`.
- At a clear stopping point after real work, close with actionable options.
- Offer a checkpoint with a meaningful title/comment and push when reasonable
  for a team of one that wants remote visibility and agent analysis on the go.
- Offer to update issues, labels, epics, or workstream records when the work
  touches project-tracking conventions.
- Use `./eba dev gh ...` for agent-authored GitHub prose mutations so the
  current `EBA-Sig` footer is appended automatically.
- Recommend a handoff when context pressure is present or continuity would help.
- If context pressure is detected or imminent, explicitly offer to use the
  Handoff skill.
- If the work is tangible, offer a self-guided demo. Agents should refresh or
  prepare surfaces themselves and give the user a short recipe for what to
  inspect, not service-management chores.
- Handoffs must ask successor sessions to perform an onboarding response before
  changing code: report entrypoint/handoff paths, the `./eba dev situation
  --json` onboarding token, concise `Salience`, and any concerns,
  misalignment, or drift.
- After writing a handoff, follow the Handoff Boundary in
  `docs/superpowers/project-sop.md`: provide a ready-to-use successor prompt in
  chat, not just the handoff path.

## Browser And Demo Flow

For the current workflow-artifact-workbench implementation of the workflow
artifact workbench, prefer the command surface. For user requests to view or
refresh the workbench, run this fast path first:

```bash
./eba dev demo
```

This starts or reuses the managed workbench server, summons the browser surface
when possible, and prints the compact inspection recipe. Use `./eba dev demo
--no-browser` in headless contexts where opening a browser is not appropriate.

For routine browser control, use the managed workbench control surface:

```bash
./eba dev workbench reset
./eba dev workbench refresh
./eba dev workbench glance --json
./eba dev workbench context --json
./eba dev workbench tabs
./eba dev workbench tab-select <index>
```

Passive workbench reads such as `glance`, `context`, `tabs`, and `tab-select`
must not resize or reposition the browser window. Explicit human-visible summon
paths such as `demo`, `reset`, and `refresh` may close and relaunch the managed
`eba-workbench` browser session so the headed Chrome window is raised without
accumulating duplicate windows. After a fresh launch, the demo/reset/refresh
path may maximize the managed window and sync Playwright's fixed viewport to the
current display's visible bounds. Capture and smoke flows keep their fixed
deterministic viewport settings. Workbench `click`, `fill`, and `press` still
require an active turn. Use `./eba dev workbench context --json` for the current
full workbench context, available workflow manifests, and session-local
interaction overlays. Use `./eba dev workbench glance --json` for the fast
"what is on the workbench now?" read. Use the same `./eba dev workbench` surface
for snapshot/click/fill/press operations instead of raw browser-control tools.

For controlled/debug use, the lower-level surface command is:

```bash
python3 scripts/playwright_cli_workbench_gate.py surface artifacts/playwright-cli-public-page-matrix/latest/manifest.json
```

Do not treat the lower-level command as a bypass around `./eba dev demo`
gating.

## Validation

Default validation:

```bash
./eba dev validate
```

This runs the project’s current focused validation ladder:

- Python compile checks for top-level scripts that participate in capture,
  projection, normalization, and the current workbench server implementation.
- Projection shape checks for the normalized Mermaid/composite workbench
  contract.
- `node --check` for the workflow artifact workbench app, shared artifact primitives, and
  checked-in workflow artifact workbench smoke snippets.
- `mcp-server` pytest suite when `mcp-server/.venv` exists.
- `git diff --check`

## Provider-Specific Files

Provider files are compatibility pointers, not the source of project truth.
Keep provider-neutral policy in this file, `docs/superpowers/project-sop.md`,
ADRs, and the `./eba` command surface.

## DOX Framework

- DOX is a lightweight AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs
  must stay understandable from the nearest applicable AGENTS.md plus every
  parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path,
   read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child
   doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session
before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child
index changes. Update child docs when parent changes alter local rules. Remove
stale or contradictory text immediately. Small edits that do not change behavior
or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences,
  durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own
  purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user
  instructions; if there are no specific standards or instructions yet, leave it
  empty
- Verification must reflect an existing check; if no verification framework
  exists yet, leave it empty and update it when one exists

Default section order:

- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why
7. Run `./eba end --worker-id <id>` to actually close and gate the turn

DOX Closeout is the in-turn doc-and-verification pass; it is not the turn gate.
The corridor and SOP sweep run only at `./eba end`; finishing these steps
without it leaves the turn open and ungated.

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md

## Child DOX Index

Root owns project-wide policy, top-level command entrypoints, provider-neutral
startup rules, generated-state boundaries, and paths without a closer child
AGENTS.md.

- `data/AGENTS.md` - static project data such as KILOS framework inputs.
- `docs/AGENTS.md` - durable architecture, SOP, planning, prompt, and spike
  documents.
- `.github/AGENTS.md` - GitHub Actions workflows and CI validation entrypoints.
- `mcp-server/AGENTS.md` - stdio MCP server, imaging package, requirements, and
  MCP-local tests.
- `scripts/AGENTS.md` - `./eba` command implementation, browser/capture helpers,
  projection code, workflow artifact workbench assets, and checked-in
  Playwright snippets.
- `tests/AGENTS.md` - repo-level Python and Node validation checks outside the
  MCP package.

Root-owned paths with no child AGENTS.md:

- `.claude/` - provider compatibility pointers only; provider-neutral policy
  stays in root AGENTS.md, SOP, ADRs, and command surfaces.
- `.eba/` - generated control-plane state, work cards, and handoff records.
- `.playwright-cli/`, `artifacts/`, `chrome-profile/`, cache folders, and
  `__pycache__/` - generated or local runtime state, not durable source
  contracts.
- `eba`, `.gitignore`, and root-level notes - root command wrapper and
  compatibility/reference files.
