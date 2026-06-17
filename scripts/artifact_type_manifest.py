#!/usr/bin/env python3
"""Read the browser artifact type script manifest."""

from __future__ import annotations

import json
import posixpath
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_TYPE_MANIFEST = Path(__file__).resolve().parent / "artifacts" / "types" / "manifest.json"
ARTIFACT_TYPE_ASSET_PREFIX = "/assets/artifacts/types"


def _entry_path(entry: Any) -> str:
    if isinstance(entry, str):
        value = entry
    elif isinstance(entry, dict):
        value = str(entry.get("path") or "")
    else:
        raise ValueError("Artifact type manifest entries must be strings or objects")
    value = value.strip()
    if not value:
        raise ValueError("Artifact type manifest entries must include a path")
    if value.startswith("/") or "\\" in value:
        raise ValueError(f"Artifact type path must be a relative POSIX path: {value}")
    normalized = posixpath.normpath(value)
    if normalized.startswith("../") or normalized == "..":
        raise ValueError(f"Artifact type path must stay inside scripts/artifacts/types: {value}")
    if not normalized.endswith(".js"):
        raise ValueError(f"Artifact type path must be a JavaScript file: {value}")
    return normalized


def read_artifact_type_manifest(manifest_path: Path = ARTIFACT_TYPE_MANIFEST) -> list[str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Artifact type manifest must be a list")
    paths = [_entry_path(entry) for entry in payload]
    if len(paths) != len(set(paths)):
        raise ValueError("Artifact type manifest paths must be unique")
    return paths


def artifact_type_asset_urls(manifest_path: Path = ARTIFACT_TYPE_MANIFEST) -> list[str]:
    return [
        f"{ARTIFACT_TYPE_ASSET_PREFIX}/{path}"
        for path in read_artifact_type_manifest(manifest_path)
    ]


def artifact_type_script_paths(manifest_path: Path = ARTIFACT_TYPE_MANIFEST) -> list[str]:
    type_dir = manifest_path.parent
    return [
        str((type_dir / path).resolve().relative_to(REPO_ROOT))
        for path in read_artifact_type_manifest(manifest_path)
    ]


def artifact_type_asset_entries(
    manifest_path: Path = ARTIFACT_TYPE_MANIFEST,
) -> list[tuple[str, Path, str]]:
    type_dir = manifest_path.parent
    return [
        (f"{ARTIFACT_TYPE_ASSET_PREFIX}/{path}", type_dir / path, "text/javascript")
        for path in read_artifact_type_manifest(manifest_path)
    ]
