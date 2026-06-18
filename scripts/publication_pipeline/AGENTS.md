# Publication Pipeline DOX

## Purpose

Reusable publication-pipeline fixture package for intake-driven workbench-visible
pipeline archetypes.

## Ownership

- Owns publication sample-profile loading, guarded output preparation, record
  generation, manifest construction, demo recipes, and publication-specific
  workbench grouping metadata.
- `scripts/publication_pipeline_fixture.py` remains a compatibility wrapper for
  direct CLI execution and existing imports.
- `data/AGENTS.md` owns checked-in sample profile data.
- `tests/AGENTS.md` owns repo-level regression tests for these fixtures.

## Local Contracts

- Runnable defaults use fictional sample profiles from
  `data/publication-pipeline-profiles/`.
- Reference source names may appear only in docs that identify local reference
  files and in reference-reader tests that assert structural facts.
- Generated default artifacts must not contain reference-client,
  reference-competitor, source-label, or URL labels.
- Recursive output cleanup must go through `prepare_output_dir()` and must
  reject paths outside repo `artifacts/` before deletion.
- Keep public pipeline families addressable through one module per archetype,
  even when shared implementation remains in `core.py`.

## Work Guidance

- Prefer adding archetype-specific code to the nearest archetype module before
  expanding `core.py`.
- Keep demo recipe copy in `demo_recipes.py`, not `eba_cli.py`.
- Keep publication-specific projection grouping metadata in
  `projection_groups.py`, not generic workbench projection code.
- Keep direct script compatibility through `scripts/publication_pipeline_fixture.py`.

## Verification

- Run `python3 tests/test_publication_default_samples.py` for default no-leakage
  behavior.
- Run `python3 tests/test_publication_pipeline_structure.py` for cleanup,
  wrapper, recipe, and projection ownership.
- Run focused publication family tests for touched archetypes.
- Run `./eba dev validate` before checkpointing substantive changes.

## Child DOX Index

No child AGENTS.md files yet.
