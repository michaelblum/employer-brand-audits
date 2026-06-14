# Decisions DOX

## Purpose

Architecture decision records for durable product, workflow, browser, manifest,
artifact, and image-processing choices.

## Ownership

- Owns `ADR-*.md` files under `docs/decisions/`.
- Does not own implementation plans, specs, prompts, or SOP text.

## Local Contracts

- Each ADR must state date and status.
- Superseded ADRs stay as records and must point to the active replacement.
- ADR-008 is the active browser-engine boundary: Playwright CLI is the browser
  engine for automated audits.
- ADRs should describe stable decisions and consequences, not session diaries.

## Work Guidance

- Add a new ADR or amendment when a change alters architecture, manifest shape,
  browser execution boundaries, artifact layering, image-hosting policy, or
  capture strategy.
- Keep cross-ADR references current when superseding or amending decisions.

## Verification

- Run `git diff --check` for ADR-only edits.
- Run `./eba end --worker-id <id>` when ADR edits affect instruction-bearing
  policy or hard invariants.

## Child DOX Index

No child AGENTS.md files yet.
