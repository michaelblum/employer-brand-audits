# Docs DOX

## Purpose

Durable project documentation: architecture decisions, operating policy, plans,
specs, prompts, spikes, and successor-facing workflow records.

## Ownership

- Owns `docs/decisions/` and `docs/superpowers/`.
- Root AGENTS.md owns project-wide startup instructions and the top-level DOX
  index.
- `docs/superpowers/project-sop.md` owns standing operating policy.

## Local Contracts

- Keep docs provider-neutral unless explicitly documenting a superseded
  provider-specific decision.
- Preserve accepted ADRs as decision records; use supersession or amendment
  notes instead of silently rewriting history.
- SOP changes require explicit human approval and an SOP sweep.
- Do not duplicate root DOX policy into every document; link local rules to the
  nearest owning AGENTS.md.

## Work Guidance

- Read relevant ADRs before changing architecture, browser boundaries, manifest
  schema, image processing, or workflow artifact behavior.
- Keep handoffs and prompts pointer-first: cite files, commits, issues, and
  commands instead of restating large source material.
- Delete stale or contradictory guidance rather than adding explanatory layers
  around it.

## Verification

- Run `git diff --check` for documentation-only edits.
- Run `./eba end --worker-id <id>` after instruction-bearing changes so the SOP
  sweep runs.
- Run `./eba dev validate` when docs and implementation change together.

## Child DOX Index

- `docs/decisions/AGENTS.md` - ADR standards and architecture decision records.
- `docs/superpowers/AGENTS.md` - SOP, implementation plans, design specs,
  prompts, and spikes.
