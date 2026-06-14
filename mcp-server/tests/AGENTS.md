# MCP Tests DOX

## Purpose

Pytest coverage for the MCP server and imaging package.

## Ownership

- Owns tests under `mcp-server/tests/`.
- Does not own repo-level tests under `/tests`.

## Local Contracts

- Tests should use local files and synthetic image fixtures.
- Keep tests focused on mechanical behavior and server serialization.

## Work Guidance

- Add regression coverage next to the module behavior being changed.
- Prefer explicit expected dimensions, paths, metadata, and errors.

## Verification

- Run `mcp-server/.venv/bin/pytest -q mcp-server/tests`.

## Child DOX Index

No child AGENTS.md files yet.
