# Project SOP

## Purpose

Standing operating policy for agents working in this repository. This document
is provider-agnostic; provider-specific startup files should point to
`AGENTS.md`.

## End-Of-Work Options

After real work is done and the repo is at a clear definable stopping point,
end the response with options for the user:

- Checkpoint the work with a meaningful title and comment. Push if that is
  reasonable for a team of one that wants remote visibility and the ability to
  analyze work with agents while on the go.
- Update issues, labels, epics, or workstream records according to the
  project’s current conventions.
- Recommend a handoff when continuity would help.
- If context pressure is detected or imminent, offer to use the Handoff skill.
- If recent work is tangible, offer a self-guided demo.

## SOP Change Control

Changes to this SOP require explicit human approval. A request to add, remove,
or rewrite SOP policy counts as approval only when the user clearly asks for
that SOP change.

SOP changes also require an `SOP sweep` before finalizing, checkpointing, or
handing off the change. An `SOP sweep` is a separate session pass or a
dedicated sub-agent spawn that reviews docs, and code when relevant, for:

- contradictions;
- overloaded, competing, or ambiguous terms;
- superseded residue;
- drift potential;
- opportunistic refactoring or refinement opportunities.

Report opportunistic refactoring or refinement opportunities separately; do not
implement them without explicit approval. Record that the `SOP sweep` happened
in the final response, handoff, or commit message context. Do not treat the
sweep as authorization to expand scope beyond the approved SOP change.

## Successor Onboarding Gate

Handoffs must not invite a new session to change code immediately. A successor
session should first respond with:

1. Confirmation of onboarding, including links or paths to the entry point and
   handoff it used, plus the onboarding token from `./eba dev situation --json`.
2. A very concise alignment recital: short bulleted facts under a `Salience`
   heading, with pointers to the handoff and generated onboarding materials
   read. This should be brochure-short, not a second handoff.
3. A question asking whether the user sees any concerns, misalignment, or drift
   to address before further work begins.

Only after that first response should the successor proceed with code changes,
unless the user explicitly overrides this gate.

## Self-Guided Demo Policy

When tangible work can be experienced, the agent should prepare the surface
before handing it to the user:

1. Refresh or start the relevant surface.
2. Open and set it up when the local environment supports that.
3. Give a short recipe for what to inspect and evaluate.
4. Avoid making the user do agentic management tasks such as restarting
   services, finding ports, or navigating verbose setup instructions.

For the current review workbench, after an active `./eba begin` turn is in
place, use:

```bash
./eba dev demo
```

Use `./eba dev demo --no-browser` only when opening a browser is inappropriate
or unavailable.

For routine browser control after the same active turn is in place, use the
managed workbench control surface:

```bash
./eba dev workbench refresh
./eba dev workbench tabs
./eba dev workbench tab-select <index>
```

Agents should reuse the managed `eba-workbench` session when available. Reuse
must not resize or reposition the browser window.

## Command Surface

Agents should prefer `./eba dev ...` for common project mechanisms:

- `./eba dev situation --json` for branch, dirt, ahead/behind, and workbench
  status.
- `./eba begin --worker-id <stable-id>` and `./eba end --worker-id <stable-id>`
  for turn-level worker identity, gate packets, corridor checks, and generated
  work-card/handoff artifacts.
- `./eba dev validate` for the current validation ladder.
- `./eba dev demo` for a prepared review-workbench inspection surface.
- `./eba dev workbench` for managed `eba-workbench` refresh, tab, snapshot, and
  interaction controls.

Update the command surface as the project evolves and new repeated mechanisms
appear. Keep it small, typed, and honest; do not add routes that are not wired
or validated.

## Publication Boundary

Do not push, open PRs, or update GitHub issues unless the user asks or accepts
one of the end-of-work options. When pushing is accepted, preserve the branch
stack and state what was pushed.

## Handoff Boundary

Handoffs should be compact and successor-facing. Prefer external temp handoffs
for session relay unless the user asks for a durable repo-local artifact.
Reference commits, docs, and command output paths rather than restating large
source content.

Every handoff must include the Successor Onboarding Gate above.

After writing a handoff, the agent's chat response should include a ready-to-use
successor prompt that points to the handoff file and restates the onboarding
commands and first-response requirements. Do not end with only the handoff file
path unless the user explicitly asks for path-only output.
