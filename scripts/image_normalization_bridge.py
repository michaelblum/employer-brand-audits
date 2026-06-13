#!/usr/bin/env python3
"""Bridge top-level capture scripts to the MCP image normalizer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = REPO_ROOT / "mcp-server"
MCP_PYTHON = MCP_SERVER / ".venv" / "bin" / "python"


def normalizer_python() -> Path:
    if MCP_PYTHON.exists():
        return MCP_PYTHON
    return Path(sys.executable)


def normalize_image_artifact(
    image_path: Path,
    artifact_subtype: str,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    cmd = [
        str(normalizer_python()),
        "-m",
        "imaging.normalization",
        str(image_path),
        "--artifact-subtype",
        artifact_subtype,
    ]
    if policy_path is not None:
        cmd.extend(["--policy", str(policy_path)])

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(MCP_SERVER)
        if not existing_pythonpath
        else os.pathsep.join([str(MCP_SERVER), existing_pythonpath])
    )
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"image normalization failed for {image_path}: {detail}")
    return json.loads(completed.stdout)
