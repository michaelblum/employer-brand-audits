# Data DOX

## Purpose

Static data inputs used by audit fixtures, analysis, and future pipeline logic.

## Ownership

- Owns `kilos-framework.json` and any future checked-in source data.
- Does not own generated audit artifacts, workbench output, browser profiles, or
  temporary capture data.

## Local Contracts

- Keep data files deterministic and reviewable in git.
- Preserve stable identifiers and semantics used by fixtures, tests, manifests,
  or reports.
- Document schema or meaning changes in the nearest relevant docs when they
  affect workflow behavior.

## Work Guidance

- Prefer structured JSON changes over ad hoc text blobs.
- Keep sample or fixture data distinct from generated runtime output.

## Verification

- Run `./eba dev validate` when data changes can affect fixtures, projections,
  or tests.
- Run focused tests when a data consumer is known.

## Child DOX Index

No child AGENTS.md files yet.
