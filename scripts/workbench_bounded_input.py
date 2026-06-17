#!/usr/bin/env python3
"""Bounded workflow-input projection and saved-state helpers."""

from __future__ import annotations

import time
from typing import Any


BOUNDED_INPUT_VALUE_MAX_LENGTH = 5000


def bounded_input_overlay_definition(step_id: str, item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    input_id = str(item.get("id") or "").strip()
    item_anchor = item.get("anchor") if isinstance(item.get("anchor"), dict) else {}
    artifact_id = str(item.get("artifact_id") or item_anchor.get("artifact_id") or "").strip()
    if not step_id or not input_id or not artifact_id:
        return None
    input_type = str(item.get("input_type") or "text").strip() or "text"
    anchor: dict[str, Any] = {
        "type": "workflow_input",
        "coordinate_space": "workflow_graph",
        "artifact_id": artifact_id,
        "step_id": step_id,
        "input_id": input_id,
    }
    selector_candidates = item.get("selector_candidates") or item_anchor.get("selector_candidates")
    if isinstance(selector_candidates, list):
        anchor["selector_candidates"] = [
            str(selector).strip()
            for selector in selector_candidates
            if str(selector).strip()
        ]
    overlay: dict[str, Any] = {
        "id": f"input:{step_id}:{input_id}",
        "subtype": "bounded_input",
        "step_id": step_id,
        "input_id": input_id,
        "label": str(item.get("label") or input_id.replace("_", " ").title()),
        "input_type": input_type,
        "required": bool(item.get("required", True)),
        "status": str(item.get("status") or "pending"),
        "value": item.get("value"),
        "subject": {"kind": "workflow_step", "id": step_id},
        "anchor": anchor,
    }
    if item.get("placeholder") is not None:
        overlay["placeholder"] = str(item.get("placeholder") or "")
    options = item.get("options")
    if isinstance(options, list):
        overlay["options"] = [
            option
            for option in options
            if isinstance(option, (str, int, float)) or isinstance(option, dict)
        ]
    target_link = item.get("target_link") or item_anchor.get("target_link")
    if isinstance(target_link, dict):
        overlay["target_link"] = target_link
    return overlay


def bounded_input_overlay_definitions_for_step(step_id: str, required_inputs: list[Any]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    for item in required_inputs:
        overlay = bounded_input_overlay_definition(step_id, item)
        if overlay is not None:
            overlays.append(overlay)
    return overlays


def bounded_input_key(overlay: dict[str, Any]) -> tuple[str, str]:
    anchor = overlay.get("anchor") if isinstance(overlay.get("anchor"), dict) else {}
    return str(anchor.get("step_id") or ""), str(anchor.get("input_id") or "")


def bounded_input_value(overlay: dict[str, Any] | None, default: Any = None) -> str:
    if overlay is None:
        return "" if default is None else str(default)
    body = overlay.get("body") if isinstance(overlay.get("body"), dict) else {}
    return str(body.get("value") or "")


def clean_bounded_input_overlay(
    overlay: dict[str, Any],
    artifact_ids: set[str],
    definition_keys: set[tuple[str, str]],
) -> dict[str, Any] | None:
    subject = overlay.get("subject")
    if not isinstance(subject, dict) or str(subject.get("kind") or "") != "workflow_step":
        return None
    anchor = overlay.get("anchor")
    if not isinstance(anchor, dict) or str(anchor.get("type") or "") != "workflow_input":
        return None
    artifact_id_value = str(anchor.get("artifact_id") or "")
    step_id = str(anchor.get("step_id") or subject.get("id") or "")
    input_id = str(anchor.get("input_id") or "")
    if artifact_id_value not in artifact_ids:
        return None
    if (step_id, input_id) not in definition_keys:
        return None
    body = overlay.get("body")
    if not isinstance(body, dict) or str(body.get("kind") or "") != "input_value":
        return None
    try:
        created_at_epoch = int(overlay.get("created_at_epoch") or time.time())
        updated_at_epoch = (
            int(overlay["updated_at_epoch"])
            if overlay.get("updated_at_epoch") is not None
            else None
        )
    except (TypeError, ValueError):
        return None
    return {
        "id": str(overlay.get("id") or f"input:{step_id}:{input_id}"),
        "subtype": "bounded_input",
        "subject": {"kind": "workflow_step", "id": step_id},
        "anchor": {
            "type": "workflow_input",
            "coordinate_space": "workflow_graph",
            "artifact_id": artifact_id_value,
            "step_id": step_id,
            "input_id": input_id,
        },
        "body": {"kind": "input_value", "value": str(body.get("value") or "")[:BOUNDED_INPUT_VALUE_MAX_LENGTH]},
        "created_at_epoch": created_at_epoch,
        "updated_at_epoch": updated_at_epoch,
    }


def bounded_input_state(
    definitions: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
) -> dict[str, Any]:
    overlays_by_key = {
        bounded_input_key(overlay): overlay
        for overlay in overlays
        if isinstance(overlay, dict) and str(overlay.get("subtype") or "") == "bounded_input"
    }
    items: list[dict[str, Any]] = []
    values: dict[str, str] = {}
    for definition in definitions:
        if not isinstance(definition, dict):
            continue
        step_id = str(definition.get("step_id") or "")
        input_id = str(definition.get("input_id") or "")
        if not step_id or not input_id:
            continue
        key = (step_id, input_id)
        value = bounded_input_value(overlays_by_key.get(key), definition.get("value"))
        value_key = f"{step_id}.{input_id}"
        values[value_key] = value
        item = {
            **definition,
            "value": value,
            "status": "filled" if value else "pending",
        }
        items.append(item)
    return {
        "status": "bounded_inputs",
        "items": items,
        "values": values,
    }
