# EBA Control Plane Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first provider-agnostic `./eba` control-plane foundation: worker identity, turn begin/end gates, corridor enforcement, generated handoff/work-card artifacts, and Python-enforced hard invariants.

**Architecture:** Keep Superpowers as the workflow discipline layer and keep `./eba` as a small Python-enforced project gate. Refactor `scripts/eba_cli.py` only enough to delegate control-plane behavior into `scripts/eba_control_plane.py`, store mutable state under `.eba/`, and require active authorized turns before selected `./eba dev ...` commands can run. Hard invariants stay in Python constants and functions, not mutable JSON policy.

**Tech Stack:** Python 3 standard library, Bash shim `./eba`, pytest-style CLI tests using `subprocess`, JSON state files under `.eba/`.

---

## Files

- Modify: `scripts/eba_cli.py`
  - Add top-level `begin` and `end` subcommands.
  - Gate `dev validate` and `dev demo` behind an active turn.
  - Leave `dev situation --json` usable for onboarding.
- Create: `scripts/eba_control_plane.py`
  - Own worker registry, turn state, begin/end packets, command authorization, corridor checks, artifact generation, and Python hard invariants.
- Create: `tests/test_eba_control_plane.py`
  - Exercise the CLI through subprocesses against isolated temporary repo copies.
- Modify: `AGENTS.md`
  - Add the manual fallback instruction once `begin`/`end` exist.
- Modify: `docs/superpowers/project-sop.md`
  - Add only the minimum command-surface language needed to avoid stale `./eba dev validate` guidance after begin/end gating.

## Non-Goals

- Do not add `.eba/policy.json`.
- Do not put hard invariants in mutable JSON.
- Do not add provider hook adapters in this slice.
- Do not implement child/subagent worker minting beyond reserving packet fields for `parent_worker_id`.
- Do not require `./eba begin` before `./eba dev situation --json`; onboarding must keep working.

## Task 1: Add Failing CLI Tests For Begin/End And Dev Gates

**Files:**
- Create: `tests/test_eba_control_plane.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    ignore = shutil.ignore_patterns(
        ".git",
        ".eba",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".venv",
    )
    shutil.copytree(REPO_ROOT, target, ignore=ignore)
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "test fixture"],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
        env={"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"},
    )
    return target


def eba(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["./eba", *args],
        cwd=repo,
        text=True,
        capture_output=True,
    )


def parse_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_situation_remains_available_without_begin(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "dev", "situation", "--json")

    assert result.returncode == 0, result.stderr
    payload = parse_json(result)
    assert payload["onboarding"]["token"] == "EBA-AGENTS-SOP-V1"


def test_dev_validate_blocks_without_active_turn(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "dev", "validate", "--json")

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["status"] == "blocked"
    assert payload["reason"] == "no_active_turn"
    assert payload["next_step"] == "run ./eba begin --worker-id <id>"


def test_begin_creates_turn_packet_and_allows_validate(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    begin = eba(repo, "begin", "--worker-id", "worker-test")
    assert begin.returncode == 0, begin.stderr
    begin_payload = parse_json(begin)
    assert begin_payload["status"] == "active"
    assert begin_payload["worker_id"] == "worker-test"
    assert begin_payload["turn_id"]
    assert begin_payload["corridor"]["allowed_paths"]
    assert "validate" in begin_payload["allowed_dev_commands"]

    validate = eba(repo, "dev", "validate", "--json")
    assert validate.returncode == 0, validate.stdout + validate.stderr
    validate_payload = parse_json(validate)
    assert validate_payload["status"] == "passed"


def test_begin_twice_for_same_worker_blocks(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "worker-test").returncode == 0

    second = eba(repo, "begin", "--worker-id", "worker-test")

    assert second.returncode != 0
    payload = parse_json(second)
    assert payload["status"] == "blocked"
    assert payload["reason"] == "active_turn_exists"
    assert payload["worker_id"] == "worker-test"
    assert payload["turn_id"]
    assert payload["next_step"] == "run ./eba end --worker-id worker-test or ask the human to authorize repair"


def test_end_writes_artifacts_and_closes_turn(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "worker-test").returncode == 0

    end = eba(repo, "end", "--worker-id", "worker-test")

    assert end.returncode == 0, end.stderr
    payload = parse_json(end)
    assert payload["status"] == "closed"
    assert payload["worker_id"] == "worker-test"
    assert payload["gate_results"]["corridor"]["status"] == "passed"
    assert payload["work_card"]["path"].startswith(".eba/work-cards/")
    assert payload["handoff"]["path"].startswith(".eba/handoffs/")
    assert (repo / payload["work_card"]["path"]).exists()
    assert (repo / payload["handoff"]["path"]).exists()

    blocked = eba(repo, "dev", "validate", "--json")
    assert blocked.returncode != 0
    assert parse_json(blocked)["reason"] == "no_active_turn"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_eba_control_plane.py -q
```

Expected: tests fail because `begin` and `end` are not recognized and `dev validate` does not require an active turn yet.

## Task 2: Add The Control-Plane Module

**Files:**
- Create: `scripts/eba_control_plane.py`

- [ ] **Step 1: Implement state paths, hard invariants, and JSON helpers**

```python
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any


ACTIVE_TURN_REQUIRED_COMMANDS = {"validate", "demo"}
ALLOWED_DEV_COMMANDS = {"situation", "validate", "demo"}
DEFAULT_ALLOWED_PATHS = [
    "AGENTS.md",
    "docs/superpowers/project-sop.md",
    "docs/superpowers/plans/",
    "scripts/",
    "tests/",
    ".eba/",
]
INSTRUCTION_BEARING_PATHS = [
    "AGENTS.md",
    ".claude/CLAUDE.md",
    ".codex/",
    ".eba/",
    "docs/superpowers/project-sop.md",
    "docs/decisions/",
]


class ControlPlaneError(Exception):
    def __init__(self, payload: dict[str, Any], exit_code: int = 2) -> None:
        super().__init__(payload.get("reason", "control_plane_error"))
        self.payload = payload
        self.exit_code = exit_code


def state_root(repo_root: Path) -> Path:
    return repo_root / ".eba"


def registry_path(repo_root: Path) -> Path:
    return state_root(repo_root) / "registry.json"


def turns_root(repo_root: Path, worker_id: str) -> Path:
    return state_root(repo_root) / "turns" / worker_id


def work_cards_root(repo_root: Path) -> Path:
    return state_root(repo_root) / "work-cards"


def handoffs_root(repo_root: Path) -> Path:
    return state_root(repo_root) / "handoffs"


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "registry_invalid" if path.name == "registry.json" else "state_invalid",
                "path": str(path),
                "error": str(exc),
            }
        ) from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned or "worker"
```

- [ ] **Step 2: Implement git helpers and active-turn lookup**

```python
def git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, text=True, capture_output=True)


def changed_files(repo_root: Path, base_ref: str | None = None) -> list[str]:
    if base_ref:
        result = git(repo_root, ["diff", "--name-only", base_ref, "--"])
    else:
        result = git(repo_root, ["status", "--short"])
    if result.returncode != 0:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "git_status_failed",
                "stderr": result.stderr.strip(),
            }
        )
    if base_ref:
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    paths = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        paths.append(line[3:] if len(line) > 3 else line)
    return paths


def current_head(repo_root: Path) -> str | None:
    result = git(repo_root, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def load_registry(repo_root: Path) -> dict[str, Any]:
    path = registry_path(repo_root)
    if not path.exists():
        return {"schema_version": "eba_registry.v1", "workers": {}}
    payload = read_json(path)
    if payload.get("schema_version") != "eba_registry.v1" or not isinstance(payload.get("workers"), dict):
        raise ControlPlaneError({"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"})
    return payload


def save_registry(repo_root: Path, registry: dict[str, Any]) -> None:
    write_json(registry_path(repo_root), registry)


def active_turn(registry: dict[str, Any], worker_id: str | None = None) -> tuple[str, dict[str, Any]] | None:
    workers = registry.get("workers", {})
    if worker_id:
        worker = workers.get(worker_id)
        if worker and worker.get("active_turn"):
            return worker_id, worker["active_turn"]
        return None
    for candidate_id, worker in workers.items():
        turn = worker.get("active_turn")
        if turn:
            return candidate_id, turn
    return None
```

- [ ] **Step 3: Implement begin**

```python
def begin_turn(repo_root: Path, worker_id: str | None) -> dict[str, Any]:
    registry = load_registry(repo_root)
    workers = registry.setdefault("workers", {})
    if worker_id is None:
        if active_turn(registry) or workers:
            raise ControlPlaneError(
                {
                    "status": "blocked",
                    "reason": "cold_bootstrap_denied",
                    "next_step": "rerun with an existing worker_id or ask the human to authorize bootstrap",
                }
            )
        if os.environ.get("EBA_BOOTSTRAP_AUTH") != "human-approved":
            raise ControlPlaneError(
                {
                    "status": "blocked",
                    "reason": "cold_bootstrap_denied",
                    "next_step": "rerun with --worker-id or ask the human to authorize bootstrap",
                }
            )
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    worker_id = slug(worker_id)
    existing = active_turn(registry, worker_id)
    if existing:
        _, turn = existing
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "active_turn_exists",
                "worker_id": worker_id,
                "turn_id": turn["turn_id"],
                "next_step": f"run ./eba end --worker-id {worker_id} or ask the human to authorize repair",
            }
        )
    turn_id = f"turn-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    packet = {
        "status": "active",
        "worker_id": worker_id,
        "turn_id": turn_id,
        "parent_worker_id": None,
        "role": "main",
        "corridor": {"allowed_paths": DEFAULT_ALLOWED_PATHS},
        "allowed_dev_commands": sorted(ALLOWED_DEV_COMMANDS),
        "required_checks_before_end": ["corridor", "instruction_sop_sweep"],
        "begin_head": current_head(repo_root),
        "started_at": int(time.time()),
    }
    workers[worker_id] = {"worker_id": worker_id, "active_turn": packet}
    save_registry(repo_root, registry)
    write_json(turns_root(repo_root, worker_id) / f"{turn_id}.json", packet)
    return packet
```

- [ ] **Step 4: Implement dev command assertion**

```python
def assert_dev_command_allowed(repo_root: Path, command: str) -> None:
    if command not in ACTIVE_TURN_REQUIRED_COMMANDS:
        return
    registry = load_registry(repo_root)
    found = active_turn(registry)
    if not found:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "no_active_turn",
                "command": f"./eba dev {command}",
                "next_step": "run ./eba begin --worker-id <id>",
            }
        )
    worker_id, turn = found
    if command not in turn.get("allowed_dev_commands", []):
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "dev_command_not_authorized",
                "worker_id": worker_id,
                "turn_id": turn.get("turn_id"),
                "command": f"./eba dev {command}",
            }
        )
```

- [ ] **Step 5: Implement corridor, SOP sweep, artifact generation, and end**

```python
def path_allowed(path: str, allowed_paths: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized == allowed.rstrip("/") or normalized.startswith(allowed.rstrip("/") + "/") for allowed in allowed_paths)


def instruction_bearing(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized == candidate.rstrip("/") or normalized.startswith(candidate.rstrip("/") + "/") for candidate in INSTRUCTION_BEARING_PATHS)


def sop_sweep(changes: list[str]) -> dict[str, Any]:
    checked = [path for path in changes if instruction_bearing(path)]
    if not checked:
        return {"status": "passed", "checked_files": []}
    return {
        "status": "blocked",
        "checked_files": checked,
        "reason": "instruction_bearing_changes_require_sop_sweep",
        "next_step": "run a dedicated SOP sweep before ending this turn",
    }


def end_turn(repo_root: Path, worker_id: str) -> dict[str, Any]:
    registry = load_registry(repo_root)
    found = active_turn(registry, worker_id)
    if not found:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "no_active_turn",
                "worker_id": worker_id,
                "next_step": f"run ./eba begin --worker-id {worker_id}",
            }
        )
    _, turn = found
    turn_id = turn["turn_id"]
    changes = changed_files(repo_root)
    allowed_paths = turn["corridor"]["allowed_paths"]
    violations = [path for path in changes if not path_allowed(path, allowed_paths)]
    corridor = {"status": "passed", "violations": [], "allowed_paths": allowed_paths}
    if violations:
        corridor = {"status": "blocked", "violations": violations, "allowed_paths": allowed_paths}
    sop = sop_sweep(changes)
    status = "closed" if corridor["status"] == "passed" and sop["status"] == "passed" else "blocked"
    base_name = f"{worker_id}-{turn_id}"
    work_card_path = work_cards_root(repo_root) / f"{base_name}.json"
    handoff_path = handoffs_root(repo_root) / f"{base_name}.json"
    payload = {
        "status": status,
        "worker_id": worker_id,
        "turn_id": turn_id,
        "changed_files": changes,
        "gate_results": {"corridor": corridor, "sop_sweep": sop},
        "next_steps": [] if status == "closed" else ["resolve blocking gate results, then rerun ./eba end"],
        "work_card": {"path": str(work_card_path.relative_to(repo_root))},
        "handoff": {"path": str(handoff_path.relative_to(repo_root))},
        "ended_at": int(time.time()),
    }
    write_json(work_card_path, payload)
    write_json(handoff_path, payload)
    if status == "closed":
        registry["workers"][worker_id]["active_turn"] = None
        save_registry(repo_root, registry)
    else:
        write_json(turns_root(repo_root, worker_id) / f"{turn_id}.blocked.json", payload)
        raise ControlPlaneError(payload)
    return payload
```

- [ ] **Step 6: Run compile check for the new module**

Run:

```bash
python3 -m py_compile scripts/eba_control_plane.py
```

Expected: no output and exit code `0`.

## Task 3: Wire The CLI Without Creating A Parallel Command Surface

**Files:**
- Modify: `scripts/eba_cli.py`

- [ ] **Step 1: Import control-plane helpers**

Add near the existing imports:

```python
from scripts.eba_control_plane import (
    ControlPlaneError,
    assert_dev_command_allowed,
    begin_turn,
    end_turn,
    print_json as print_control_json,
)
```

- [ ] **Step 2: Add command handlers**

Add below `command_demo`:

```python
def command_begin(args: argparse.Namespace) -> int:
    payload = begin_turn(REPO_ROOT, args.worker_id)
    print_control_json(payload)
    return 0


def command_end(args: argparse.Namespace) -> int:
    payload = end_turn(REPO_ROOT, args.worker_id)
    print_control_json(payload)
    return 0
```

- [ ] **Step 3: Register top-level begin/end parsers**

In `build_parser()`, before the `dev` parser block:

```python
    begin = subparsers.add_parser("begin", help="Begin an EBA worker turn")
    begin.add_argument("--worker-id")
    begin.set_defaults(func=command_begin)

    end = subparsers.add_parser("end", help="End an EBA worker turn")
    end.add_argument("--worker-id", required=True)
    end.set_defaults(func=command_end)
```

- [ ] **Step 4: Gate selected dev commands in `main()`**

Replace the current `main()` body after parsing with:

```python
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.family == "dev":
            assert_dev_command_allowed(REPO_ROOT, args.command)
        return args.func(args)
    except ControlPlaneError as exc:
        print_control_json(exc.payload)
        return exc.exit_code
```

- [ ] **Step 5: Run the new focused tests**

Run:

```bash
python3 -m pytest tests/test_eba_control_plane.py -q
```

Expected: all tests in `tests/test_eba_control_plane.py` pass.

## Task 4: Add Adversarial Gate Tests

**Files:**
- Modify: `tests/test_eba_control_plane.py`

- [ ] **Step 1: Add tests for corrupt registry, cold bootstrap, and corridor blocking**

```python
def test_corrupt_registry_fails_closed(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "worker-test").returncode == 0
    registry = repo / ".eba" / "registry.json"
    registry.write_text("{not json")

    result = eba(repo, "dev", "validate", "--json")

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["status"] == "blocked"
    assert payload["reason"] == "registry_invalid"


def test_cold_bootstrap_denied_without_human_auth(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "begin")

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["status"] == "blocked"
    assert payload["reason"] == "cold_bootstrap_denied"


def test_end_blocks_out_of_corridor_changes(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "worker-test").returncode == 0
    out_of_corridor = repo / "README.md"
    out_of_corridor.write_text("outside corridor\n")

    result = eba(repo, "end", "--worker-id", "worker-test")

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["status"] == "blocked"
    assert payload["gate_results"]["corridor"]["status"] == "blocked"
    assert "README.md" in payload["gate_results"]["corridor"]["violations"]
```

- [ ] **Step 2: Run the adversarial tests and fix only test-proven issues**

Run:

```bash
python3 -m pytest tests/test_eba_control_plane.py -q
```

Expected: all tests pass. If the corrupt-registry test fails because `.eba/registry.json` is not loaded before command gating, fix `load_registry()` or the command gate, not the test.

## Task 5: Add Minimal Provider-Neutral Docs Updates With SOP Sweep

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/project-sop.md`

- [ ] **Step 1: Update `AGENTS.md` startup fallback**

Add under `## Start Here` after the `./eba dev situation --json` bullet:

```markdown
- If you did not receive an `./eba begin` turn packet at session start, manually
  run `./eba begin --worker-id <stable-id>` before `./eba dev validate`,
  `./eba dev demo`, or substantive repo edits.
```

- [ ] **Step 2: Update `docs/superpowers/project-sop.md` command surface language**

In `## Command Surface`, add:

```markdown
- `./eba begin --worker-id <stable-id>` and `./eba end --worker-id <stable-id>`
  for turn-level worker identity, gate packets, corridor checks, and generated
  work-card/handoff artifacts.
```

- [ ] **Step 3: Run an SOP sweep for instruction-bearing changes**

Run:

```bash
rg -n "Claude in Chrome|computer screenshot|zoom|provider-specific browser-control|base64|./eba begin|./eba end|./eba dev validate|Superpowers" AGENTS.md docs/superpowers/project-sop.md docs/decisions scripts
```

Expected:
- Existing browser and base64 hard invariants are still present.
- New docs point to `./eba begin` and `./eba end`.
- No docs introduce mutable policy JSON for hard invariants.
- No project doc attributes the control plane to a specific AI provider.

## Task 6: Run Final Validation

**Files:**
- No new edits unless validation exposes a concrete failure.

- [ ] **Step 1: Run focused control-plane tests**

Run:

```bash
python3 -m pytest tests/test_eba_control_plane.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run compile checks**

Run:

```bash
python3 -m py_compile scripts/eba_cli.py scripts/eba_control_plane.py
```

Expected: no output and exit code `0`.

- [ ] **Step 3: Run project validation inside a turn**

Run:

```bash
./eba begin --worker-id validation
./eba dev validate --json
./eba end --worker-id validation
```

Expected:
- `begin` returns `status: active`.
- `validate` returns `status: passed`.
- `end` returns `status: closed` if only in-corridor files changed.

- [ ] **Step 4: Check repository status**

Run:

```bash
git status --short --branch
```

Expected: only the intended plan, test, CLI, control-plane, and minimal docs files are changed.

## Self-Review

- Spec coverage: This plan covers worker identity, begin/end gates, dev command gating, corridor enforcement, `.eba/` state, work-card/handoff artifact creation, Python hard invariants, and the no mutable policy-config rule.
- Explicit deferrals: Provider hook adapters, event-level base64 guard enforcement, and child/subagent worker minting are deferred because they need provider integration design after this foundation works.
- Placeholder scan: No task depends on `TBD`, unwired commands, or mutable policy JSON.
- Type consistency: `worker_id`, `turn_id`, `active_turn`, `allowed_dev_commands`, and gate result field names are consistent across tests, module code, and CLI wiring.

Plan complete and saved to `docs/superpowers/plans/2026-06-13-eba-control-plane-foundation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using `superpowers:executing-plans`, with checkpoints for review.
