# Prompt: Workbench Gate Server Management And Turn-Based Approval Design

You are the next senior developer on the `employer-brand-audits` Playwright CLI migration.

Start from branch `migration/playwright-cli-engine`. The latest pushed commit should be:

```text
04b4b42 Fix workbench gate artifact image URLs
```

Do a quick status check first:

```bash
git status --short --branch
git log --oneline -8
```

Expected local noise from the prior environment:

```text
 M scripts/spike_hitl_capture.py
?? example.png
```

Do not touch, stage, commit, or rely on those files unless the user explicitly asks. `scripts/spike_hitl_capture.py` had pre-existing local modifications outside the committed migration work.

There may also be a transient local workbench server from the prior session:

```text
http://127.0.0.1:8765/
```

At handoff time it was running as PID `51884`, but treat that as stale process state. Verify with:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN || true
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/ || true
```

Stop only the workbench server process if needed; do not kill unrelated processes.

## Authoritative Direction

Read these first, in order:

```text
docs/decisions/ADR-008-playwright-cli-browser-engine.md
docs/decisions/ADR-005-screenshot-capture-strategy.md
.claude/CLAUDE.md
playwright-cli-vs-claude-in-chrome.md
scripts/playwright_cli_workbench_server.py
scripts/playwright_cli_finalize_approval.py
scripts/playwright_cli_public_page_matrix_smoke.py
```

Operating rules:

- Playwright CLI is the browser engine for audit execution.
- Claude in Chrome / Claude browser-control tooling is disabled for audit execution.
- Do not use `computer` screenshot / `zoom` or `javascript_tool` as capture primitives.
- Browser artifacts must be written to disk; do not route image bytes through the model.
- Keep proof tiers narrow. Do not claim browser parity or audit readiness just because local smoke tests pass.
- The workbench gate is a human-in-the-loop boundary. Browser clicks create only draft approval state; downstream audit steps must require agent-session confirmation and `human-approval.json`.

## Current Pushed Work

Relevant pushed commits on `migration/playwright-cli-engine`:

```text
e7c10a7 Add Playwright CLI smoke harness
36810d1 Expand Playwright CLI smoke proof
f427fb5 Add Playwright CLI capture modes smoke
a8c0902 Add Playwright CLI public page smoke
ff3d4af Add Playwright CLI public page matrix smoke
3db5afa Add Playwright CLI human workbench gate
e1a0a87 Open Playwright workbench gate from server
04b4b42 Fix workbench gate artifact image URLs
```

Important committed files:

```text
scripts/playwright_cli_browser.py
scripts/playwright_cli_smoke.py
scripts/playwright_cli_capture_modes_smoke.py
scripts/playwright_cli_public_page_smoke.py
scripts/playwright_cli_public_page_matrix_smoke.py
scripts/playwright_cli_workbench_server.py
scripts/playwright_cli_finalize_approval.py
scripts/playwright-snippets/extract-visible-text.js
scripts/playwright-snippets/settle-page.js
scripts/playwright-snippets/hide-obscuring-elements.js
scripts/playwright-snippets/restore-page.js
playwright-cli-vs-claude-in-chrome.md
```

Existing smoke/workbench commands:

```bash
python3 scripts/playwright_cli_smoke.py
python3 scripts/playwright_cli_capture_modes_smoke.py
python3 scripts/playwright_cli_public_page_smoke.py
python3 scripts/playwright_cli_public_page_matrix_smoke.py
python3 scripts/playwright_cli_workbench_server.py artifacts/playwright-cli-public-page-matrix/latest/manifest.json --open
python3 scripts/playwright_cli_finalize_approval.py artifacts/playwright-cli-public-page-matrix/latest/manifest.json
```

Ignored artifact directories:

```text
artifacts/playwright-cli-smoke/latest/
artifacts/playwright-cli-capture-modes/latest/
artifacts/playwright-cli-public-page/latest/
artifacts/playwright-cli-public-page-matrix/latest/
.playwright-cli/
```

## Current Workbench Gate Behavior

`scripts/playwright_cli_public_page_matrix_smoke.py` creates:

```text
artifacts/playwright-cli-public-page-matrix/latest/manifest.json
artifacts/playwright-cli-public-page-matrix/latest/<slug>/
```

`scripts/playwright_cli_workbench_server.py` serves a local carousel at `http://127.0.0.1:8765/`:

- one slide per captured page;
- wrap-around previous/next navigation;
- screenshots and links for viewport, full-page, element, text, snapshot, manifest, and log;
- exclusive `Accept` / `Needs changes` / `Reject` switch on each slide;
- `Accept` selected by default;
- comment input appears when `Needs changes` or `Reject` is selected;
- browser writes only:

```text
artifacts/playwright-cli-public-page-matrix/latest/approval-draft.json
```

The page must not trigger downstream audit work. The user must return to the agent session that drove the process and say `ready`. Only then should the agent run:

```bash
python3 scripts/playwright_cli_finalize_approval.py artifacts/playwright-cli-public-page-matrix/latest/manifest.json
```

That writes:

```text
artifacts/playwright-cli-public-page-matrix/latest/human-approval.json
```

Downstream audit steps should require `human-approval.json`, not `approval-draft.json`.

## Problem Found In Prior Session

The current server startup command is not fool-proof enough for turn-based agent sessions.

Observed behavior:

- Running `python3 scripts/playwright_cli_workbench_server.py ... --open` in a normal foreground tool call works while the tool session remains active.
- Starting it with ordinary shell backgrounding, for example `nohup ... &`, appeared to exit immediately in this execution environment with no useful traceback.
- Starting it through a Python `subprocess.Popen(..., start_new_session=True)` launcher kept it alive:

```python
subprocess.Popen(
    [sys.executable, "scripts/playwright_cli_workbench_server.py", "artifacts/playwright-cli-public-page-matrix/latest/manifest.json", "--port", "8765"],
    cwd=repo,
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=log,
    start_new_session=True,
)
```

This proved the issue is lifecycle management in the agent/tool environment, not the HTTP server itself.

The user explicitly said this is a critical component with tremendous utility and wants it done right:

1. Server management should be encapsulated in a simple fool-proof abstraction so future sessions do not have to troubleshoot or babysit it.
2. The team should brainstorm a clever way to use this in turn-based sessions before locking in the final protocol.

## Next Task

Do **not** jump straight into a large implementation. First propose a concise design, then implement the smallest useful lifecycle abstraction after the path is clear.

Recommended design target:

Add a dedicated manager script, for example:

```text
scripts/playwright_cli_workbench_gate.py
```

Potential commands:

```bash
python3 scripts/playwright_cli_workbench_gate.py start artifacts/playwright-cli-public-page-matrix/latest/manifest.json --open
python3 scripts/playwright_cli_workbench_gate.py status artifacts/playwright-cli-public-page-matrix/latest/manifest.json
python3 scripts/playwright_cli_workbench_gate.py stop artifacts/playwright-cli-public-page-matrix/latest/manifest.json
python3 scripts/playwright_cli_workbench_gate.py open artifacts/playwright-cli-public-page-matrix/latest/manifest.json
python3 scripts/playwright_cli_workbench_gate.py finalize artifacts/playwright-cli-public-page-matrix/latest/manifest.json
```

The manager should probably:

- write a PID file under the ignored artifact directory, for example `workbench-server.pid`;
- write logs under the ignored artifact directory, for example `workbench-server.log`;
- start the server with `subprocess.Popen(..., start_new_session=True)`;
- detect stale PID files and recover without user babysitting;
- verify health with HTTP checks before reporting success;
- open the local URL in the system browser only after health passes;
- make `status` report URL, PID, health, draft path, and approval path;
- make `stop` terminate only the PID it owns;
- keep `finalize` gated on explicit user/agent-session intent, not browser interaction;
- avoid committing generated PID/log/draft/approval artifacts.

Turn-based session design questions to brainstorm with the user:

- Should the manager print a compact "come back and say `ready`" token or phrase that future sessions can recognize?
- Should `approval-draft.json` include a session nonce or run id so the agent can prove it is finalizing the same approval session the user saw?
- Should `human-approval.json` record the finalized agent/session metadata and the matrix manifest checksum?
- Should non-accept decisions block downstream auditing, or should they allow downstream work with explicit exceptions?
- Should the workbench server expose a read-only status endpoint that the agent can poll when the user says `ready`?
- Should the page itself show a copyable "ready payload" that the user pastes back into the agent session?
- Should the manager support multiple simultaneous workbench gates by choosing ports automatically and writing the chosen URL into a state file?

Suggested first implementation slice:

1. Add `scripts/playwright_cli_workbench_gate.py` with `start/status/stop/open`.
2. Keep `finalize` in `scripts/playwright_cli_finalize_approval.py` for now, or delegate to it from the manager only after the user says `ready`.
3. Update `playwright-cli-vs-claude-in-chrome.md` so users run the manager, not the raw server.
4. Validate start/status/open/stop locally.
5. Commit and push only scoped code/docs.

Validation commands:

```bash
git diff --check
python3 -m py_compile scripts/playwright_cli_workbench_server.py scripts/playwright_cli_finalize_approval.py scripts/playwright_cli_workbench_gate.py
cd mcp-server && ./.venv/bin/pytest -q
python3 scripts/playwright_cli_workbench_gate.py start artifacts/playwright-cli-public-page-matrix/latest/manifest.json --open
python3 scripts/playwright_cli_workbench_gate.py status artifacts/playwright-cli-public-page-matrix/latest/manifest.json
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/
curl -fsS -o /tmp/eba-workbench-check.png -w '%{http_code} %{content_type} %{size_download}\n' http://127.0.0.1:8765/artifact/artifacts/playwright-cli-public-page-matrix/latest/mozilla-careers/viewport.png
python3 scripts/playwright_cli_workbench_gate.py stop artifacts/playwright-cli-public-page-matrix/latest/manifest.json
```

Commit and push only scoped changes. Do not include generated `artifacts/`, `.playwright-cli/`, `example.png`, or the pre-existing `scripts/spike_hitl_capture.py` modification.
