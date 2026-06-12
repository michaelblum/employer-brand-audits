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

## Self-Guided Demo Policy

When tangible work can be experienced, the agent should prepare the surface
before handing it to the user:

1. Refresh or start the relevant surface.
2. Open and set it up when the local environment supports that.
3. Give a short recipe for what to inspect and evaluate.
4. Avoid making the user do agentic management tasks such as restarting
   services, finding ports, or navigating verbose setup instructions.

For the current review workbench, use:

```bash
./eba dev demo
```

Use `./eba dev demo --no-browser` only when opening a browser is inappropriate
or unavailable.

## Command Surface

Agents should prefer `./eba dev ...` for common project mechanisms:

- `./eba dev situation --json` for branch, dirt, ahead/behind, and workbench
  status.
- `./eba dev validate` for the current validation ladder.
- `./eba dev demo` for a prepared review-workbench inspection surface.

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
