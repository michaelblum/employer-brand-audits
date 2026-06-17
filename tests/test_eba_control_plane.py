from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.eba_control_plane import (
    ControlPlaneError,
    PROTECTED_SOP_CHECKS,
    begin_turn,
    changed_files,
    concrete_sop_checks,
    end_turn,
    gate_integrity_check,
    instruction_bearing,
    path_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {
            ".git",
            ".eba",
            ".playwright-cli",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "chrome-profile",
        } & set(names)
        if Path(directory).resolve() == REPO_ROOT and "artifacts" in names:
            ignored.add("artifacts")
        return ignored

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


def test_validation_commands_scope_pytest_to_control_plane_and_mcp_tests() -> None:
    from scripts.eba_cli import validation_commands

    pytest_commands = [
        command
        for command in validation_commands()
        if "pytest" in command or command[0].endswith("/pytest")
    ]
    if not pytest_commands:
        pytest.skip("mcp-server pytest venv is not present")

    venv_python = str(REPO_ROOT / "mcp-server" / ".venv" / "bin" / "python")
    pytest_bin = str(REPO_ROOT / "mcp-server" / ".venv" / "bin" / "pytest")
    assert pytest_commands == [
        [venv_python, "-m", "pytest", "-q", "tests/test_eba_control_plane.py"],
        [pytest_bin, "-q", "mcp-server/tests"],
    ]


def test_validation_commands_compile_easy_audit_fixture() -> None:
    from scripts.eba_cli import validation_commands

    compile_command = validation_commands()[0]

    assert "scripts/easy_audit_fixture.py" in compile_command


def test_ci_runs_eba_validate_inside_turn() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "validate.yml").read_text(
        encoding="utf-8"
    )

    assert "./eba begin --worker-id ci-validate" in workflow
    assert "./eba dev validate" in workflow
    assert "./eba end --worker-id ci-validate" in workflow


def test_easy_audit_fixture_route_generates_manifest(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "dev", "situation", "--fixture", "easy-audit", "--json")

    assert result.returncode == 0, result.stderr
    payload = parse_json(result)
    assert payload["artifact_workbench"]["manifest"] == "artifacts/easy-audit/latest/manifest.json"
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
    assert payload["reason"] == "no_current_turn"
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
        and validate_payload.get("reason") == "no_current_turn"
    )


def test_eba_sig_prints_newest_active_turn_signature(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "older-worker").returncode == 0
    assert eba(repo, "begin", "--worker-id", "current-worker").returncode == 0

    result = eba(repo, "sig", "--json")

    assert result.returncode == 0, result.stderr
    payload = parse_json(result)
    assert payload["worker_id"] == "current-worker"
    assert payload["signature"] == f"current-worker/{payload['turn_id']}"


def test_eba_sig_without_current_turn_does_not_use_stale_registry(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "stale-worker").returncode == 0
    (repo / ".eba" / "current-turn.json").unlink()

    result = eba(repo, "sig", "--json")

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["reason"] == "no_current_turn"


def test_dev_command_gate_prefers_current_turn_over_stale_registry(
    tmp_path: Path,
) -> None:
    from scripts.eba_control_plane import assert_dev_command_allowed

    repo = copy_repo(tmp_path)
    assert eba(repo, "begin", "--worker-id", "stale-worker").returncode == 0
    registry_path = repo / ".eba" / "registry.json"
    registry = json.loads(registry_path.read_text())
    registry["workers"]["stale-worker"]["active_turn"]["allowed_dev_commands"] = ["validate"]
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")
    assert eba(repo, "begin", "--worker-id", "current-worker").returncode == 0

    assert_dev_command_allowed(repo, "gh")


def test_dev_command_gate_can_force_active_turn_for_ungated_family(
    tmp_path: Path,
) -> None:
    from scripts.eba_control_plane import assert_dev_command_allowed

    repo = copy_repo(tmp_path)

    assert_dev_command_allowed(repo, "workbench")
    with pytest.raises(ControlPlaneError) as exc_info:
        assert_dev_command_allowed(repo, "workbench", require_active_turn=True)
    assert exc_info.value.payload["reason"] == "no_current_turn"

    assert eba(repo, "begin", "--worker-id", "current-worker").returncode == 0
    assert_dev_command_allowed(repo, "workbench", require_active_turn=True)


@pytest.mark.parametrize(
    "workbench_args",
    [
        ("click", "artifact-title"),
        ("fill", "comment-text", "hello"),
        ("press", "Enter"),
    ],
)
def test_workbench_interaction_commands_require_active_turn(
    tmp_path: Path,
    workbench_args: tuple[str, ...],
) -> None:
    repo = copy_repo(tmp_path)

    result = eba(repo, "dev", "workbench", *workbench_args)

    assert result.returncode != 0
    payload = parse_json(result)
    assert payload["reason"] == "no_current_turn"
    assert payload["command"] == "./eba dev workbench"


def test_begin_corridor_covers_dox_boundaries(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    begin = eba(repo, "begin", "--worker-id", "worker-test")

    assert begin.returncode == 0, begin.stderr
    allowed_paths = parse_json(begin)["corridor"]["allowed_paths"]
    for expected in [
        "AGENTS.md",
        "data/",
        "docs/",
        "mcp-server/",
        "scripts/",
        "tests/",
        ".github/",
        ".eba/",
    ]:
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
    assert parse_json(blocked)["reason"] == "no_current_turn"


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
    assert not instruction_bearing("scripts/artifact_workbench/app.js")


def test_signature_footer_appends_and_skips_consecutive_duplicate() -> None:
    from scripts.eba_signature import append_signature_footer

    body = "Update body\n"
    signed = append_signature_footer(body, "worker-one/turn-1")

    assert signed == "Update body\n\nEBA-Sigs:\n- worker-one/turn-1\n"
    assert append_signature_footer(signed, "worker-one/turn-1") == signed
    assert append_signature_footer(signed, "worker-two/turn-2") == (
        "Update body\n\nEBA-Sigs:\n- worker-one/turn-1\n- worker-two/turn-2\n"
    )
    many = "Update body\n\nEBA-Sigs:\n" + "\n".join(
        f"- worker/turn-{index}" for index in range(12)
    )
    capped = append_signature_footer(many, "worker/turn-12", max_signatures=10)
    assert "- worker/turn-0\n" not in capped
    assert "- worker/turn-2\n" not in capped
    assert capped.endswith("- worker/turn-12\n")


def test_trace_and_gh_command_authorization_shape() -> None:
    from scripts.eba_control_plane import ACTIVE_TURN_REQUIRED_COMMANDS, ALLOWED_DEV_COMMANDS

    assert "trace" in ALLOWED_DEV_COMMANDS
    assert "trace" not in ACTIVE_TURN_REQUIRED_COMMANDS
    assert "hooks" in ALLOWED_DEV_COMMANDS
    assert "hooks" not in ACTIVE_TURN_REQUIRED_COMMANDS
    assert "demo" in ALLOWED_DEV_COMMANDS
    assert "demo" not in ACTIVE_TURN_REQUIRED_COMMANDS
    assert "stage-url" in ALLOWED_DEV_COMMANDS
    assert "stage-url" not in ACTIVE_TURN_REQUIRED_COMMANDS
    assert "workbench" in ALLOWED_DEV_COMMANDS
    assert "workbench" not in ACTIVE_TURN_REQUIRED_COMMANDS
    assert "gh" in ALLOWED_DEV_COMMANDS
    assert "gh" in ACTIVE_TURN_REQUIRED_COMMANDS


def test_eba_control_plane_is_instruction_bearing() -> None:
    assert instruction_bearing("scripts/eba_control_plane.py")


def test_sop_gate_protects_its_check_set(tmp_path: Path) -> None:
    repo = copy_repo(tmp_path)

    checks = concrete_sop_checks(repo)

    assert PROTECTED_SOP_CHECKS <= {check["name"] for check in checks}
    integrity = next(check for check in checks if check["name"] == "sop_gate_integrity")
    assert integrity["status"] == "passed"


def test_gate_integrity_trips_when_a_protected_check_is_missing() -> None:
    result = gate_integrity_check({"agents_turn_gate"})

    assert result["status"] == "failed"
    assert "no_mutable_hard_policy" in result["missing"]


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
