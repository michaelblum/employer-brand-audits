from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.eba_control_plane import (
    ControlPlaneError,
    begin_turn,
    changed_files,
    concrete_sop_checks,
    end_turn,
    instruction_bearing,
    path_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    ignore = shutil.ignore_patterns(
        ".git",
        ".eba",
        ".playwright-cli",
        "__pycache__",
        ".pytest_cache",
        "artifacts",
        "node_modules",
        ".venv",
        "chrome-profile",
    )
    shutil.copytree(REPO_ROOT, target, ignore=ignore)
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", "test fixture"],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
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


def test_cli_can_be_package_imported() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.eba_cli"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_validation_commands_scope_mcp_pytest_to_mcp_tests() -> None:
    from scripts.eba_cli import validation_commands

    mcp_pytest_commands = [
        command
        for command in validation_commands()
        if command[0].endswith("mcp-server/.venv/bin/pytest")
    ]
    if not mcp_pytest_commands:
        pytest.skip("mcp-server pytest venv is not present")

    assert mcp_pytest_commands == [[mcp_pytest_commands[0][0], "-q", "mcp-server/tests"]]


def test_validation_commands_compile_easy_audit_fixture() -> None:
    from scripts.eba_cli import validation_commands

    compile_command = validation_commands()[0]

    assert "scripts/easy_audit_fixture.py" in compile_command


def test_easy_audit_fixture_route_generates_manifest(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "dev", "situation", "--fixture", "easy-audit", "--json")

    assert result.returncode == 0, result.stderr
    payload = parse_json(result)
    assert payload["workflow_artifact_workbench"]["manifest"] == "artifacts/easy-audit/latest/manifest.json"
    assert (repo / "artifacts" / "easy-audit" / "latest" / "manifest.json").exists()


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
    validate_payload = parse_json(validate)
    assert not (
        validate.returncode != 0
        and validate_payload.get("status") == "blocked"
        and validate_payload.get("reason") == "no_active_turn"
    )


def test_begin_corridor_covers_dox_boundaries(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    begin = eba(repo, "begin", "--worker-id", "worker-test")

    assert begin.returncode == 0, begin.stderr
    allowed_paths = parse_json(begin)["corridor"]["allowed_paths"]
    for expected in ["AGENTS.md", "data/", "docs/", "mcp-server/", "scripts/", "tests/", ".eba/"]:
        assert expected in allowed_paths


def test_begin_corridor_still_excludes_generated_and_root_runtime_paths(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    begin = eba(repo, "begin", "--worker-id", "worker-test")

    assert begin.returncode == 0, begin.stderr
    allowed_paths = parse_json(begin)["corridor"]["allowed_paths"]
    assert not path_allowed("artifacts/easy-audit/latest/manifest.json", allowed_paths)
    assert not path_allowed("chrome-profile/Local State", allowed_paths)
    assert not path_allowed("eba", allowed_paths)


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
    assert (
        payload["next_step"]
        == "run ./eba end --worker-id worker-test or ask the human to authorize repair"
    )


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


def test_begin_with_worker_id_fails_closed_when_registry_missing_with_existing_state(
    tmp_path: Path,
) -> None:
    repo = copy_repo(tmp_path)
    old_turn = repo / ".eba" / "turns" / "worker-test" / "turn-old.json"
    old_turn.parent.mkdir(parents=True)
    old_turn.write_text("{}\n")

    with pytest.raises(ControlPlaneError) as exc_info:
        begin_turn(repo, "worker-test")

    assert exc_info.value.payload["status"] == "blocked"
    assert exc_info.value.payload["reason"] == "registry_missing_with_existing_state"


def test_changed_files_preserves_untracked_path_with_spaces_and_quotes(
    tmp_path: Path,
) -> None:
    repo = copy_repo(tmp_path)
    special_path = 'scripts/generated path "quoted".txt'
    target = repo / special_path
    target.write_text("generated\n")

    changes = changed_files(repo)

    assert special_path in changes
    assert path_allowed(special_path, ["scripts/"])


def test_instruction_bearing_detects_child_agents_files() -> None:
    assert instruction_bearing("AGENTS.md")
    assert instruction_bearing("scripts/AGENTS.md")
    assert instruction_bearing("mcp-server/imaging/AGENTS.md")
    assert not instruction_bearing("scripts/workflow_artifact_workbench/app.js")


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


def test_cold_bootstrap_denied_without_human_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = copy_repo(tmp_path)
    monkeypatch.delenv("EBA_BOOTSTRAP_AUTH", raising=False)

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


def test_end_passes_concrete_sop_sweep_for_approved_instruction_changes(
    tmp_path: Path,
) -> None:
    repo = copy_repo(tmp_path)
    assert begin_turn(repo, "worker-test")["status"] == "active"
    agents = repo / "AGENTS.md"
    sop = repo / "docs" / "superpowers" / "project-sop.md"
    agents.write_text(agents.read_text() + "\n")
    sop.write_text(sop.read_text() + "\n")

    payload = end_turn(repo, "worker-test")

    assert payload["status"] == "closed"
    sweep = payload["gate_results"]["sop_sweep"]
    assert sweep["status"] == "passed"
    assert "AGENTS.md" in sweep["checked_files"]
    assert "docs/superpowers/project-sop.md" in sweep["checked_files"]


def test_end_blocks_when_sop_sweep_detects_weakened_hard_invariant(
    tmp_path: Path,
) -> None:
    repo = copy_repo(tmp_path)
    assert begin_turn(repo, "worker-test")["status"] == "active"
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text().replace("base64", "encoded-image"))

    with pytest.raises(ControlPlaneError) as exc_info:
        end_turn(repo, "worker-test")

    payload = exc_info.value.payload
    sweep = payload["gate_results"]["sop_sweep"]
    assert sweep["status"] == "blocked"
    assert sweep["reason"] == "sop_sweep_failed"
    assert "agents_base64_boundary" in sweep["failed_checks"]


def test_adr_008_sop_check_tolerates_supersession_note(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    adr = repo / "docs" / "decisions" / "ADR-008-playwright-cli-browser-engine.md"
    adr.write_text(
        adr.read_text(encoding="utf-8").replace(
            "**Status:** Accepted",
            "**Status:** Superseded by ADR-009",
        ),
        encoding="utf-8",
    )

    check = next(check for check in concrete_sop_checks(repo) if check["name"] == "adr_008_browser_boundary")

    assert check["status"] == "passed"
