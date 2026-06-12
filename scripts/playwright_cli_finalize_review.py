#!/usr/bin/env python3
"""Finalize a local human review draft after explicit agent-session approval."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write human-approval.json from review-draft.json. "
            "Run only after the user returns to the agent session and says ready."
        )
    )
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, value: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    if not manifest_path.exists() or manifest_path.name != "manifest.json":
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if REPO_ROOT not in manifest_path.parents:
        raise SystemExit(f"Manifest must be inside the repository: {manifest_path}")

    artifact_root = manifest_path.parent
    draft_path = artifact_root / "review-draft.json"
    approval_path = artifact_root / "human-approval.json"
    if not draft_path.exists():
        raise SystemExit(f"Review draft not found: {draft_path}")

    manifest = read_json(manifest_path)
    draft = read_json(draft_path)
    pages = manifest.get("pages", [])
    decisions = draft.get("decisions", {})
    if not isinstance(pages, list) or not isinstance(decisions, dict):
        raise SystemExit("Invalid manifest or draft shape")

    page_slugs = [page["slug"] for page in pages]
    missing = [slug for slug in page_slugs if slug not in decisions]
    if missing:
        raise SystemExit(f"Review draft is missing decisions for: {', '.join(missing)}")

    cleaned: dict[str, dict[str, str]] = {}
    for slug in page_slugs:
        decision = decisions[slug]
        value = decision.get("decision")
        if value not in {"accept", "needs_review", "reject"}:
            raise SystemExit(f"Invalid decision for {slug}: {value}")
        cleaned[slug] = {
            "decision": value,
            "comment": str(decision.get("comment", "")),
        }

    accepted_all = all(decision["decision"] == "accept" for decision in cleaned.values())
    approval = {
        "status": "approved" if accepted_all else "reviewed_with_exceptions",
        "accepted_all": accepted_all,
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "draft": str(draft_path.relative_to(REPO_ROOT)),
        "created_at_epoch": int(time.time()),
        "decision_counts": {
            "accept": sum(1 for decision in cleaned.values() if decision["decision"] == "accept"),
            "needs_review": sum(
                1 for decision in cleaned.values() if decision["decision"] == "needs_review"
            ),
            "reject": sum(1 for decision in cleaned.values() if decision["decision"] == "reject"),
        },
        "decisions": cleaned,
    }
    write_json_atomic(approval_path, approval)
    print(f"Wrote {approval_path}")
    print(f"status={approval['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
