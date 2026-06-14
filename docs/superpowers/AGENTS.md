# Superpowers Docs DOX

## Purpose

Standing workflow policy and agent-facing planning artifacts for this project.

## Ownership

- Owns `project-sop.md`.
- Owns `plans/`, `specs/`, `prompts/`, and `spikes/`.
- Does not own code implementation or generated `.eba/` handoff/work-card state.

## Local Contracts

- `project-sop.md` is standing operating policy. Changes require explicit human
  approval and an SOP sweep.
- Plans and specs should be execution-grade and point to source files, commands,
  ADRs, and verification steps.
- Prompts and handoffs should be compact, successor-facing, and pointer-first.
- Spikes record investigation results and must not silently override accepted
  ADRs or SOP.

## Work Guidance

- Keep plans current with the actual command surface.
- Avoid provider attribution in docs intended as project truth.
- Preserve the Successor Onboarding Gate in handoff-related artifacts.

## Verification

- Run `git diff --check` for docs-only edits.
- Run `./eba end --worker-id <id>` for SOP or instruction-bearing edits.
- Run implementation checks named by a plan when changing both plan and code.

## Child DOX Index

No child AGENTS.md files yet. `plans/`, `specs/`, `prompts/`, and `spikes/`
remain owned by this AGENTS.md.
