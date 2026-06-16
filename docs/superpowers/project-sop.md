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

## DOX Operating Policy

DOX is the repository's `AGENTS.md` hierarchy. It is the local-contract layer
for instructions, ownership, and durable workflow rules; this SOP remains the
standing process layer.

Before editing, agents must re-read the applicable DOX chain in the current
session: the root `AGENTS.md`, then every child `AGENTS.md` found from the repo
root to each path they expect to touch. If a parent lists a child whose scope
contains the target path, read that child before editing.

Every meaningful change requires a DOX pass before closeout:

- update the nearest owning `AGENTS.md` when purpose, ownership, workflow,
  contracts, required inputs or outputs, permissions, artifacts, or durable user
  preferences change;
- refresh affected Child DOX Index entries;
- remove stale or contradictory instructions;
- report any applicable docs intentionally left unchanged and why.

The DOX pass and Closeout are in-turn steps, not the turn gate. The corridor and
SOP sweep run only at `./eba end`.

DOX changes that alter this SOP or project-wide operating rules still require
the SOP Change Control process above, including an `SOP sweep`.

## Successor Onboarding Gate

Handoffs must not invite a new session to change code immediately. A successor
session should first respond with:

1. Confirmation of onboarding, including links or paths to the entry point and
   handoff it used, the onboarding token from `./eba dev situation --json`, and
   the active `EBA-Sig` when a turn is open.
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

For the current artifact workbench, use the command surface directly
for view-only user requests:

```bash
./eba dev demo
```

Use `./eba dev demo --no-browser` only when opening a browser is inappropriate
or unavailable.

For routine browser control, use the managed workbench control surface:

```bash
./eba dev workbench refresh
./eba dev workbench glance --json
./eba dev workbench context --json
./eba dev workbench live-smoke --fixture easy-audit --json
./eba dev workbench tabs
./eba dev workbench tab-select <index>
```

Passive workbench reads should reuse the managed `eba-workbench` session without
resizing or repositioning the browser window. Explicit human-visible summon
paths such as `demo`, `reset`, and `refresh` may close and relaunch the managed
browser session so a fresh headed Chrome window is raised without accumulating
duplicates; those paths may then maximize and sync the fixed viewport to the
current display's visible bounds. Workbench `click`, `fill`, and `press` still
require an active turn. For "what is on the workbench now?" questions, use
`glance` first; it returns the compact live context, current artifact, and
annotation summary. Use `live-smoke` after browser-loaded workbench asset or
app-shell changes when a bounded live boot/runtime check is warranted.

## Command Surface

Agents should prefer `./eba dev ...` for common project mechanisms:

- `./eba dev situation --json` for branch, dirt, ahead/behind, and workbench
  status.
- `./eba begin --worker-id <stable-id>` and `./eba end --worker-id <stable-id>`
  for turn-level worker identity, gate packets, DOX-aware corridor checks, and
  generated work-card/handoff artifacts.
- `./eba sig` for the current repo-private provenance signature.
- `./eba dev trace` for bounded local session archaeology.
- `./eba dev gh` for GitHub prose mutations with automatic `EBA-Sig` footers.
- `./eba dev hooks install` to install the local commit-message footer hook.
- `./eba dev validate` for the current validation ladder.
- `./eba dev demo` for a prepared artifact workbench inspection surface.
- `./eba dev workbench` for managed `eba-workbench` context, refresh, tab,
  snapshot, glance, live-smoke, and interaction controls.

Update the command surface as the project evolves and new repeated mechanisms
appear. Keep it small, typed, and honest; do not add routes that are not wired
or validated.

The DOX-aware turn corridor intentionally covers durable source and instruction
trees (`.github/`, `data/`, `docs/`, `mcp-server/`, `scripts/`, and `tests/`)
so child `AGENTS.md` files and their owning code can move through the same gate.
Generated and local runtime paths such as `artifacts/`, `.playwright-cli/`, and
`chrome-profile/` stay outside the corridor.

## Publication Boundary

Do not push, open PRs, or update GitHub issues unless the user asks or accepts
one of the end-of-work options. When pushing is accepted, preserve the branch
stack and state what was pushed.

## GitHub Provenance

Use the command surface, not hand-maintained ritual, for repo-private provenance:

- `./eba sig` prints the active `EBA-Sig`.
- `./eba dev gh ...` signs agent-authored issue bodies, PR bodies, and comments.
- `./eba dev hooks install` installs the local commit-message signing hook.
- `./eba dev trace ...` performs bounded local session archaeology.

Signed GitHub prose and commit messages end with:

```text
EBA-Sigs:
- <worker-id>/<turn-id>
```

Append the current signature, skip only a consecutive duplicate, and keep the
rolling footer bounded. Use provider-neutral worker IDs because signatures may
appear in GitHub. Do not paste work-card or handoff payloads into GitHub.

Preserve the Publication Boundary: ask before creating or updating issues,
labels, epics, PRs, or comments unless the user has already accepted that
specific action.

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
