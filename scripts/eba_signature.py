from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.eba_control_plane import ControlPlaneError, current_turn_path, load_registry, read_json
except ModuleNotFoundError:
    from eba_control_plane import ControlPlaneError, current_turn_path, load_registry, read_json


FOOTER_RE = re.compile(
    r"(?s)^(?P<body>.*?)(?:\n{2,}EBA-Sigs:\n(?P<items>(?:- [^\n]+(?:\n|$))+))\s*$"
)
DEFAULT_MAX_SIGNATURES = 10


@dataclass(frozen=True)
class EbaSignature:
    worker_id: str
    turn_id: str
    signature: str
    head: str | None


def active_turn_packets(registry: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    workers = registry.get("workers", {})
    if not isinstance(workers, dict):
        raise ControlPlaneError(
            {"status": "blocked", "reason": "registry_invalid", "path": ".eba/registry.json"}
        )
    packets: list[tuple[str, dict[str, Any]]] = []
    for worker_id, worker in workers.items():
        if not isinstance(worker, dict):
            continue
        turn = worker.get("active_turn")
        if isinstance(turn, dict):
            packets.append((str(worker_id), turn))
    return packets


def current_short_head(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def current_eba_signature(repo_root: Path, worker_id: str | None = None) -> EbaSignature:
    if worker_id is None:
        current = read_json(current_turn_path(repo_root))
        if current:
            turn_id = str(current.get("turn_id") or "")
            current_worker_id = str(current.get("worker_id") or "")
            if current_worker_id and turn_id:
                return EbaSignature(
                    worker_id=current_worker_id,
                    turn_id=turn_id,
                    signature=f"{current_worker_id}/{turn_id}",
                    head=current_short_head(repo_root),
                )
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "no_current_turn",
                "next_step": "run ./eba begin --worker-id <id>",
            }
        )

    registry = load_registry(repo_root)
    packets = active_turn_packets(registry)
    if worker_id:
        packets = [(candidate_id, turn) for candidate_id, turn in packets if candidate_id == worker_id]
    if not packets:
        payload: dict[str, Any] = {
            "status": "blocked",
            "reason": "no_active_turn",
            "next_step": "run ./eba begin --worker-id <id>",
        }
        if worker_id:
            payload["worker_id"] = worker_id
        raise ControlPlaneError(payload)

    selected_worker_id, selected_turn = max(
        packets,
        key=lambda item: (
            int(item[1].get("started_at_ns") or 0),
            int(item[1].get("started_at") or 0),
            str(item[1].get("turn_id") or ""),
        ),
    )
    turn_id = str(selected_turn.get("turn_id") or "")
    if not turn_id:
        raise ControlPlaneError(
            {
                "status": "blocked",
                "reason": "state_invalid",
                "path": ".eba/registry.json",
                "error": "active turn missing turn_id",
            }
        )
    signature = f"{selected_worker_id}/{turn_id}"
    return EbaSignature(
        worker_id=selected_worker_id,
        turn_id=turn_id,
        signature=signature,
        head=current_short_head(repo_root),
    )


def signature_payload(signature: EbaSignature) -> dict[str, Any]:
    return {
        "worker_id": signature.worker_id,
        "turn_id": signature.turn_id,
        "signature": signature.signature,
        "head": signature.head,
        "footer": f"EBA-Sigs:\n- {signature.signature}\n",
    }


def footer_items(items_text: str) -> list[str]:
    items: list[str] = []
    for line in items_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def append_signature_footer(
    text: str,
    signature: str,
    *,
    max_signatures: int = DEFAULT_MAX_SIGNATURES,
) -> str:
    if max_signatures <= 0:
        max_signatures = DEFAULT_MAX_SIGNATURES
    stripped = text.rstrip()
    match = FOOTER_RE.match(stripped)
    if match:
        body = match.group("body").rstrip()
        items = footer_items(match.group("items"))
        if items and items[-1] == signature:
            return f"{stripped}\n"
        items.append(signature)
        items = items[-max_signatures:]
        item_text = "\n".join(f"- {item}" for item in items)
        return f"{body}\n\nEBA-Sigs:\n{item_text}\n"
    if not stripped:
        return f"EBA-Sigs:\n- {signature}\n"
    return f"{stripped}\n\nEBA-Sigs:\n- {signature}\n"
