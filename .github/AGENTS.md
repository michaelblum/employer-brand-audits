# GitHub Automation DOX

## Purpose

Owns GitHub Actions workflows and GitHub-hosted validation entrypoints.

## Ownership

- `.github/workflows/` contains CI workflows that validate pull requests and
  protected branch updates.

## Local Contracts

- CI must exercise repository-owned command surfaces rather than duplicating
  validation logic inline.
- The PR validation workflow is the durable backstop for gate self-protection:
  it runs `./eba dev validate` from a checkout that review can inspect.
- Do not add secrets, publication, release, or mutation steps without explicit
  user approval.

## Work Guidance

- Keep workflow steps minimal and aligned with local `./eba` commands.
- Prefer pinning setup actions by major version unless the project adds a
  stricter supply-chain policy.

## Verification

- Run `./eba dev validate` after workflow changes when the local environment can
  execute the same command path.

## Child DOX Index

This scope has no child AGENTS.md files.
