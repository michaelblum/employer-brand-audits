#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts.eba_control_plane import ControlPlaneError
    from scripts.eba_signature import append_signature_footer, current_eba_signature
except ModuleNotFoundError:
    from eba_control_plane import ControlPlaneError
    from eba_signature import append_signature_footer, current_eba_signature


REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: eba_commit_msg_hook.py <commit-msg-file>", file=sys.stderr)
        return 2
    message_path = Path(argv[1])
    try:
        signature = current_eba_signature(REPO_ROOT)
    except ControlPlaneError:
        return 0

    original = message_path.read_text(encoding="utf-8")
    updated = append_signature_footer(original, signature.signature)
    if updated != original:
        message_path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
