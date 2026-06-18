# Publication Pipeline DOX

## Purpose

Reusable publication-pipeline fixture package for intake-driven workbench-visible
pipeline archetypes.

## Ownership

- Owns publication sample-profile loading, guarded output preparation,
  archetype-specific record generation, manifest construction, demo recipes,
  and publication composite-group metadata written into manifests.
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
- Recursive output cleanup must go through `prepare_output_dir()`. It must
  reject paths outside repo `artifacts/`, refuse non-empty arbitrary artifact
  directories that lack `.publication-fixture-output`, and only recursively
  clear marker-owned outputs or a generator's own default output directory.
- Keep public pipeline families addressable through one module per archetype.
  Archetype loaders, record builders, view-body builders, manifest builders,
  and generators belong in those modules; `core.py` is for shared primitives
  such as IO, output preparation, profile normalization, URL-stage import,
  generic evidence helpers, HTML rendering, and manifest helpers.
- Keep reusable view/table rendering and workbook-style entity/profile helpers
  in neutral helper modules such as `html_views.py` and `workbook_shared.py`.
  Archetype modules must not import shared behavior from sibling archetypes.
- Publication view bundle grouping must be declared in generated manifest
  artifact facets; generic workbench projection code must consume only that
  manifest metadata.

## Work Guidance

- Prefer adding archetype-specific code to the nearest archetype module before
  expanding `core.py`.
- Prefer neutral helper modules for behavior reused by multiple archetypes;
  avoid making one archetype module the dependency owner for another.
- Keep demo recipe copy in `demo_recipes.py`, not `eba_cli.py`.
- Keep publication-specific projection grouping metadata in
  `projection_groups.py` for manifest generation, not generic workbench
  projection code.
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
