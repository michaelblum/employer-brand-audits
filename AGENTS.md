# Employer Brand Audits Agent Entry Point

This is the provider-agnostic startup surface for agent sessions in this repo.
Provider-specific files such as `.claude/CLAUDE.md` should only point here.

## Start Here

- Read this file first.
- Use `./eba dev situation --json` for current repo and workbench state.
- If you did not receive an `./eba begin` turn packet at session start, manually
  run `./eba begin --worker-id <stable-id>` before `./eba dev validate`,
  `./eba dev demo`, or substantive repo edits.
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

For the current workflow-artifact-workbench implementation of the workflow artifact
workbench, prefer the command surface:

```bash
./eba dev demo
```

This starts or reuses the managed workbench, opens the surface when possible,
and prints the compact inspection recipe. Use `./eba dev demo --no-browser` in
headless contexts where opening a browser is not appropriate.

For routine browser control after the same active `./eba begin` turn gate has
been satisfied, use the managed workbench control surface:

```bash
./eba dev workbench reset
./eba dev workbench refresh
./eba dev workbench tabs
./eba dev workbench tab-select <index>
```

`reset` starts or reuses the managed `eba-workbench` browser session. Reusing an
existing session must navigate in place and must not resize or reposition the
window; if a human has moved the workbench to a display, agents should leave it
there. Use the same `./eba dev workbench` surface for snapshot/click/fill/press
operations instead of raw browser-control tools.

For controlled/debug use after the same active `./eba begin` turn gate has
been satisfied, the lower-level surface command is:

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
