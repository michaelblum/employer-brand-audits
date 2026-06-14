# MCP Server DOX

## Purpose

Mechanical stdio MCP server and Python imaging utilities for local file-based
image operations.

## Ownership

- Owns `server.py`, `requirements.txt`, `imaging/`, and `tests/`.
- Does not own browser automation, workflow workbench UI, or generated image
  artifacts.

## Local Contracts

- MCP tools are mechanical utilities; keep inputs and outputs as explicit disk
  paths.
- Do not route base64 image payloads through model prompts, tool arguments, or
  tool results.
- Keep audit/manifest coupling outside low-level imaging helpers unless a plan
  explicitly moves that boundary.
- Preserve normalization, rendered-height caps, codec policy, and subtype
  overrides as artifact-processing responsibilities.

## Work Guidance

- Prefer small pure functions in `imaging/` with server wiring in `server.py`.
- Add or update MCP-local tests with behavior changes.
- Keep dependencies in `requirements.txt` minimal and justified.

## Verification

- Run `mcp-server/.venv/bin/pytest -q mcp-server/tests` when the venv exists.
- Run `./eba dev validate` before checkpointing MCP changes.

## Child DOX Index

- `mcp-server/imaging/AGENTS.md` - image utility module contracts.
- `mcp-server/tests/AGENTS.md` - MCP-local pytest coverage.
