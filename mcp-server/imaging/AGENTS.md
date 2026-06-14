# Imaging DOX

## Purpose

Pure Python image processing primitives for scale detection, stitching, crops,
renditions, and normalization.

## Ownership

- Owns Python modules in `mcp-server/imaging/`.
- Does not own MCP request schemas, browser capture, manifest projection, or UI
  rendering.

## Local Contracts

- Functions operate on local disk paths and return local disk paths or small
  structured metadata.
- Keep capture geometry concepts explicit: scale, trim, matte, rendered-height
  cap, codec, and subtype policy are separate responsibilities.
- Avoid hidden network, browser, model, or credential dependencies.

## Work Guidance

- Keep helpers deterministic and testable with synthetic fixtures.
- Preserve existing public exports in `__init__.py` unless callers and tests are
  updated together.

## Verification

- Run `mcp-server/.venv/bin/pytest -q mcp-server/tests` when behavior changes.

## Child DOX Index

No child AGENTS.md files yet.
