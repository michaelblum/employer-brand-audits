from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any


REGISTRY_SCHEMA_VERSION = "eba_registry.v1"

ACTIVE_TURN_REQUIRED_COMMANDS = {"validate", "demo", "workbench"}
ALLOWED_DEV_COMMANDS = {"situation", "validate", "demo", "workbench"}
DEFAULT_ALLOWED_PATHS = [
    "AGENTS.md",
    "data/",
    "docs/",
    "mcp-server/",
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
        payload = json.loads(path.read_text())
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
    if not isinstance(payload, dict):
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "registry_invalid" if path.name == "registry.json" else "state_invalid",
                "path": str(path),
                "error": "expected JSON object",
            }
        )
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned or "worker"


def git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo_root, text=True, capture_output=True)


def git_status_porcelain_z(repo_root: Path) -> str:
    result = git(repo_root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if result.returncode != 0:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "git_status_failed",
                "stderr": result.stderr.strip(),
            }
        )
    return result.stdout


def git_diff_name_only(repo_root: Path, base_ref: str) -> list[str]:
    result = git(repo_root, ["diff", "--name-only", base_ref, "--"])
    if result.returncode != 0:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "git_diff_failed",
                "base_ref": base_ref,
                "stderr": result.stderr.strip(),
            }
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_files(repo_root: Path, base_ref: str | None = None) -> list[str]:
    if base_ref:
        return git_diff_name_only(repo_root, base_ref)
    paths: list[str] = []
    records = git_status_porcelain_z(repo_root).split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2]
        path = record[3:] if len(record) > 3 else ""
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            index += 1
        if path:
            paths.append(path)
    return paths


def current_head(repo_root: Path) -> str | None:
    result = git(repo_root, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def load_registry(repo_root: Path) -> dict[str, Any]:
    path = registry_path(repo_root)
    if not path.exists():
        if existing_control_plane_state(repo_root):
            raise ControlPlaneError(
                {
                    "status": "blocked",
                    "reason": "registry_missing_with_existing_state",
                    "path": ".eba/registry.json",
                    "next_step": "ask the human to authorize control-plane state repair",
                }
            )
        return {"schema_version": REGISTRY_SCHEMA_VERSION, "workers": {}}
    payload = read_json(path)
    if (
        payload.get("schema_version") != REGISTRY_SCHEMA_VERSION
        or not isinstance(payload.get("workers"), dict)
    ):
        raise ControlPlaneError(
            {"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"}
        )
    return payload


def save_registry(repo_root: Path, registry: dict[str, Any]) -> None:
    if (
        registry.get("schema_version") != REGISTRY_SCHEMA_VERSION
        or not isinstance(registry.get("workers"), dict)
    ):
        raise ControlPlaneError(
            {"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"}
        )
    write_json(registry_path(repo_root), registry)


def active_turn(
    registry: dict[str, Any], worker_id: str | None = None
) -> tuple[str, dict[str, Any]] | None:
    workers = registry.get("workers", {})
    if not isinstance(workers, dict):
        raise ControlPlaneError(
            {"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"}
        )
    if worker_id:
        worker = workers.get(worker_id)
        if isinstance(worker, dict) and isinstance(worker.get("active_turn"), dict):
            return worker_id, worker["active_turn"]
        return None
    for candidate_id, worker in workers.items():
        if not isinstance(worker, dict):
            continue
        turn = worker.get("active_turn")
        if isinstance(turn, dict):
            return candidate_id, turn
    return None


def existing_turn_state(repo_root: Path) -> bool:
    turns = state_root(repo_root) / "turns"
    return turns.exists() and any(turns.rglob("*.json"))


def existing_control_plane_state(repo_root: Path) -> bool:
    root = state_root(repo_root)
    if not root.exists():
        return False
    return any(root.iterdir())


def begin_turn(repo_root: Path, worker_id: str | None) -> dict[str, Any]:
    registry = load_registry(repo_root)
    workers = registry.setdefault("workers", {})
    if not isinstance(workers, dict):
        raise ControlPlaneError(
            {"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"}
        )
    if worker_id is None:
        if workers or active_turn(registry) or existing_turn_state(repo_root):
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
                "turn_id": turn.get("turn_id"),
                "next_step": f"run ./eba end --worker-id {worker_id} or ask the human to authorize repair",
            }
        )

    now = int(time.time())
    turn_id = f"turn-{now}-{uuid.uuid4().hex[:8]}"
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
        "started_at": now,
    }
    workers[worker_id] = {"worker_id": worker_id, "active_turn": packet}
    save_registry(repo_root, registry)
    write_json(turns_root(repo_root, worker_id) / f"{turn_id}.json", packet)
    return packet


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


def path_allowed(path: str, allowed_paths: list[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    for allowed in allowed_paths:
        normalized_allowed = allowed.replace("\\", "/").strip("/")
        if normalized == normalized_allowed or normalized.startswith(normalized_allowed + "/"):
            return True
    return False


def instruction_bearing(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized == "AGENTS.md" or normalized.endswith("/AGENTS.md"):
        return True
    for candidate in INSTRUCTION_BEARING_PATHS:
        normalized_candidate = candidate.replace("\\", "/").strip("/")
        if normalized == normalized_candidate or normalized.startswith(normalized_candidate + "/"):
            return True
    return False


def generated_control_plane_state(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return (
        normalized == ".eba/registry.json"
        or normalized.startswith(".eba/turns/")
        or normalized.startswith(".eba/work-cards/")
        or normalized.startswith(".eba/handoffs/")
    )


def required_text_check(
    repo_root: Path,
    *,
    name: str,
    path: str,
    required: list[str],
) -> dict[str, Any]:
    target = repo_root / path
    text = re.sub(r"\s+", " ", target.read_text()).lower() if target.exists() else ""
    missing = [
        value
        for value in required
        if re.sub(r"\s+", " ", value).lower() not in text
    ]
    return {
        "name": name,
        "path": path,
        "status": "passed" if not missing else "failed",
        "missing": missing,
    }


def concrete_sop_checks(repo_root: Path) -> list[dict[str, Any]]:
    checks = [
        required_text_check(
            repo_root,
            name="agents_turn_gate",
            path="AGENTS.md",
            required=["./eba begin", "./eba dev validate", "./eba dev demo"],
        ),
        required_text_check(
            repo_root,
            name="agents_browser_boundary",
            path="AGENTS.md",
            required=[
                "Playwright CLI",
                "Claude in Chrome",
                "computer",
                "zoom",
                "provider-specific browser-control",
            ],
        ),
        required_text_check(
            repo_root,
            name="agents_base64_boundary",
            path="AGENTS.md",
            required=["base64", "model prompts", "tool arguments", "tool results"],
        ),
        required_text_check(
            repo_root,
            name="agents_provider_attribution",
            path="AGENTS.md",
            required=["specific AI provider"],
        ),
        required_text_check(
            repo_root,
            name="sop_change_control",
            path="docs/superpowers/project-sop.md",
            required=["changes to this SOP require explicit human approval", "SOP sweep"],
        ),
        required_text_check(
            repo_root,
            name="sop_turn_commands",
            path="docs/superpowers/project-sop.md",
            required=["./eba begin", "./eba end", "./eba dev demo", "active `./eba begin` turn"],
        ),
        required_text_check(
            repo_root,
            name="adr_008_browser_boundary",
            path="docs/decisions/ADR-008-playwright-cli-browser-engine.md",
            required=[
                "**Status:** Accepted",
                "Playwright CLI is the browser engine for automated audits.",
            ],
        ),
    ]
    policy_path = state_root(repo_root) / "policy.json"
    checks.append(
        {
            "name": "no_mutable_hard_policy",
            "path": ".eba/policy.json",
            "status": "failed" if policy_path.exists() else "passed",
            "missing": [],
        }
    )
    return checks


def sop_sweep(repo_root: Path, changes: list[str]) -> dict[str, Any]:
    checked = [
        path
        for path in changes
        if instruction_bearing(path) and not generated_control_plane_state(path)
    ]
    skipped_generated_state = [path for path in changes if generated_control_plane_state(path)]
    if not checked:
        return {"status": "passed", "checked_files": [], "skipped_generated_state": skipped_generated_state}
    checks = concrete_sop_checks(repo_root)
    failed_checks = [check["name"] for check in checks if check["status"] == "failed"]
    if not failed_checks:
        return {
            "status": "passed",
            "checked_files": checked,
            "skipped_generated_state": skipped_generated_state,
            "checks": checks,
        }
    return {
        "status": "blocked",
        "checked_files": checked,
        "skipped_generated_state": skipped_generated_state,
        "checks": checks,
        "failed_checks": failed_checks,
        "reason": "sop_sweep_failed",
        "next_step": "restore the hard invariants or ask the human to approve the policy change",
    }


def end_turn(repo_root: Path, worker_id: str) -> dict[str, Any]:
    worker_id = slug(worker_id)
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
    sop = sop_sweep(repo_root, changes)
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
        blocked_packet = {**turn, "status": "blocked", "blocked_result": payload}
        registry["workers"][worker_id]["active_turn"] = blocked_packet
        save_registry(repo_root, registry)
        write_json(turns_root(repo_root, worker_id) / f"{turn_id}.blocked.json", payload)
        raise ControlPlaneError(payload)
    return payload
