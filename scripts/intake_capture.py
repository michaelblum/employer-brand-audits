#!/usr/bin/env python3
"""Turn filled workbench intake inputs into fresh L0/L1 capture artifacts."""

from __future__ import annotations

import json
import re
import shutil
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from scripts.url_stage_capture import REPO_ROOT, capture_url_stage, slugify_stage_name
except ModuleNotFoundError:
    from url_stage_capture import REPO_ROOT, capture_url_stage, slugify_stage_name


DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "intake-l0-l1"
OUTPUT_MARKER = ".intake-capture-output"
PROBE_TIMEOUT_SECONDS = 4
PROBE_BYTES = 48_000


@dataclass(frozen=True)
class IntakeCaptureRequest:
    company: str
    domain_hint: str
    talent_segment: str = ""
    workflow_template: str = "standard-audit"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        return str(resolved.relative_to(REPO_ROOT))
    return str(path)


def clean_slug(value: str) -> str:
    return slugify_stage_name(value) or "intake-capture"


def value_by_suffix(values: dict[str, Any], suffix: str) -> str:
    direct = values.get(suffix)
    if direct:
        return str(direct).strip()
    dotted_suffix = f".{suffix}"
    for key, value in values.items():
        if str(key).endswith(dotted_suffix) and value:
            return str(value).strip()
    return ""


def extract_intake_request(
    state: dict[str, Any],
    *,
    company: str | None = None,
    domain_hint: str | None = None,
    talent_segment: str | None = None,
    workflow_template: str | None = None,
) -> IntakeCaptureRequest:
    bounded_inputs = state.get("bounded_inputs") if isinstance(state.get("bounded_inputs"), dict) else {}
    values = bounded_inputs.get("values") if isinstance(bounded_inputs.get("values"), dict) else {}
    resolved_company = (company or value_by_suffix(values, "company")).strip()
    resolved_domain = (domain_hint or value_by_suffix(values, "domain_hint") or value_by_suffix(values, "domain")).strip()
    resolved_segment = (talent_segment or value_by_suffix(values, "talent_segment")).strip()
    resolved_template = (workflow_template or value_by_suffix(values, "workflow_template") or "standard-audit").strip()
    if not resolved_company:
        raise ValueError("I need the company name before I can collect L0/L1. Fill Company and say ready again.")
    if not resolved_domain:
        raise ValueError(
            "I need a domain or careers URL before I can collect L0/L1. "
            "Fill Domain hint with a website like apple.com or a careers URL and say ready again."
        )
    return IntakeCaptureRequest(
        company=resolved_company,
        domain_hint=resolved_domain,
        talent_segment=resolved_segment,
        workflow_template=resolved_template or "standard-audit",
    )


def normalize_domain_hint(domain_hint: str) -> tuple[str, str | None]:
    raw = domain_hint.strip()
    if not raw:
        return "", None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).split("/", 1)[0].strip().lower()
    if not host:
        return "", None
    host = re.sub(r"^https?://", "", host).strip("/")
    full_url = raw if "://" in raw and parsed.netloc and parsed.path not in {"", "/"} else None
    return host, full_url


def host_variants(host: str) -> list[str]:
    if host.startswith("www."):
        bare = host[4:]
        return [host, bare]
    return [f"www.{host}", host]


def build_candidate_urls(company: str, domain_hint: str) -> list[str]:
    host, explicit_url = normalize_domain_hint(domain_hint)
    if not host:
        inferred = re.sub(r"[^a-z0-9]+", "", company.lower())
        host = f"{inferred}.com" if inferred else ""
    paths = [
        "/careers/us/",
        "/careers/",
        "/jobs/",
        "/about/careers/",
        "/en/careers/",
        "/",
    ]
    candidates: list[str] = []
    if explicit_url:
        candidates.append(explicit_url)
    for variant in host_variants(host):
        for path in paths:
            candidates.append(f"https://{variant}{path}")
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def probe_url(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EBA-L0L1-Demo/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    # This probe is only an L0 reachability hint. Playwright/Chrome owns the
    # actual capture boundary, so avoid local Python trust-store drift blocking
    # a browser-capturable public page.
    with urlopen(request, timeout=PROBE_TIMEOUT_SECONDS, context=ssl._create_unverified_context()) as response:
        body = response.read(PROBE_BYTES).decode("utf-8", errors="ignore")
        final_url = response.geturl()
        status = getattr(response, "status", 200)
    text = f"{final_url}\n{body}".lower()
    keyword_hit = any(term in text for term in ["career", "careers", "jobs", "job search", "working at", "life at"])
    return {
        "url": url,
        "final_url": final_url,
        "status_code": status,
        "status": "usable" if 200 <= int(status) < 400 and keyword_hit else "reachable",
        "keyword_hit": keyword_hit,
    }


def discover_source_urls(request: IntakeCaptureRequest) -> tuple[list[dict[str, Any]], str]:
    results: list[dict[str, Any]] = []
    selected_url = ""
    for candidate in build_candidate_urls(request.company, request.domain_hint):
        try:
            result = probe_url(candidate)
        except Exception as exc:  # noqa: BLE001 - probe failures are evidence for the L0 list.
            result = {
                "url": candidate,
                "status": "failed",
                "error": str(exc)[:240],
            }
        results.append(result)
        if not selected_url and result.get("status") == "usable":
            selected_url = str(result.get("final_url") or result.get("url") or "")
            result["role"] = "careers_home"
            result["selected"] = True
            break
    if not selected_url:
        reachable = next((item for item in results if item.get("status") == "reachable"), None)
        if reachable:
            selected_url = str(reachable.get("final_url") or reachable.get("url") or "")
            reachable["role"] = "reachable_site_entry"
            reachable["selected"] = True
    if not selected_url:
        raise ValueError(
            "I could not reach a plausible careers entry URL. "
            "Please provide the exact careers URL in Domain hint and say ready again."
        )
    return results, selected_url


def prepare_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT not in resolved.parents:
        raise SystemExit(f"Refusing unsafe intake capture output directory: {resolved}")
    marker = resolved / OUTPUT_MARKER
    if resolved.exists() and any(resolved.iterdir()) and not marker.exists():
        raise SystemExit(f"Refusing to replace unmarked intake capture directory: {resolved}")
    shutil.rmtree(resolved, ignore_errors=True)
    resolved.mkdir(parents=True, exist_ok=True)
    marker.write_text("intake-capture-output\n", encoding="utf-8")
    return resolved


def intake_flow_markdown(request: IntakeCaptureRequest, selected_url: str) -> str:
    segment = request.talent_segment or "General employer brand audit"
    return f"""# L0 Intake

```mermaid
flowchart TB
  intake["L0 seed intake<br/>{request.company}<br/>{request.domain_hint}<br/>{segment}"]
  discover["L0 URL discovery<br/>{selected_url}"]
  capture["L1 source capture<br/>text + screenshot"]
  intake --> discover --> capture
```

| Field | Value |
| --- | --- |
| Company | {request.company} |
| Domain hint | {request.domain_hint} |
| Talent segment | {segment} |
| Workflow template | {request.workflow_template} |
| Selected L0 entry URL | {selected_url} |
"""


def manifest_required_inputs(request: IntakeCaptureRequest) -> list[dict[str, Any]]:
    return [
        {"id": "company", "label": "Company", "value": request.company, "input_type": "text", "status": "filled", "artifact_id": "l0-intake-flow"},
        {
            "id": "domain_hint",
            "label": "Domain or inferred-domain hint",
            "value": request.domain_hint,
            "input_type": "text",
            "status": "filled",
            "artifact_id": "l0-intake-flow",
        },
        {
            "id": "workflow_template",
            "label": "Workflow template",
            "value": request.workflow_template,
            "input_type": "select",
            "status": "filled",
            "artifact_id": "l0-intake-flow",
            "options": [
                {"value": "standard-audit", "label": "Standard audit"},
                {"value": "tech-talent-audit", "label": "Tech talent audit"},
            ],
        },
        {
            "id": "talent_segment",
            "label": "Talent segment or scope",
            "value": request.talent_segment,
            "input_type": "text",
            "status": "filled" if request.talent_segment else "pending",
            "artifact_id": "l0-intake-flow",
        },
    ]


def copy_stage_artifacts(output_dir: Path, stage_dir: Path) -> dict[str, Path]:
    paths = {
        "screenshot": output_dir / "l1-careers-screenshot.png",
        "web_snapshot": output_dir / "l1-web-snapshot.html",
        "web_snapshot_data": output_dir / "l1-web-snapshot-data.json",
    }
    shutil.copyfile(stage_dir / "page.full-page.png", paths["screenshot"])
    shutil.copyfile(stage_dir / "web-snapshot.html", paths["web_snapshot"])
    shutil.copyfile(stage_dir / "web-snapshot-data.json", paths["web_snapshot_data"])
    return paths


def visible_text_from_stage(stage_data_path: Path) -> str:
    data = json.loads(stage_data_path.read_text(encoding="utf-8"))
    projections = data.get("projections") if isinstance(data.get("projections"), dict) else {}
    visible_text = projections.get("visible_text") if isinstance(projections.get("visible_text"), dict) else {}
    text = str(visible_text.get("text") or "").strip()
    return text + "\n" if text else ""


def write_intake_capture_manifest(
    *,
    output_dir: Path,
    request: IntakeCaptureRequest,
    source_urls: list[dict[str, Any]],
    selected_url: str,
    stage_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_stage_artifacts(output_dir, stage_dir)
    write_json(output_dir / "l0-source-urls.json", source_urls)
    (output_dir / "l0-intake-flow.md").write_text(
        intake_flow_markdown(request, selected_url),
        encoding="utf-8",
    )
    (output_dir / "l1-careers-text.txt").write_text(
        visible_text_from_stage(output_dir / "l1-web-snapshot-data.json"),
        encoding="utf-8",
    )
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    slug = clean_slug(request.company)
    steps = [
        {
            "id": "l0-seed-intake",
            "layer": 0,
            "name": "L0 seed intake",
            "description": "Collect bounded workbench intake values for a company-specific capture run.",
            "status": "complete",
            "started_at": now,
            "completed_at": now,
            "required_inputs": manifest_required_inputs(request),
            "artifact_ids": ["l0-intake-flow"],
            "parent_step_ids": [],
        },
        {
            "id": "l0-url-discovery",
            "layer": 0,
            "name": "L0 URL discovery",
            "description": "Probe likely careers entry points from the supplied company/domain intake.",
            "status": "complete",
            "started_at": now,
            "completed_at": now,
            "required_inputs": ["company", "domain_hint"],
            "artifact_ids": ["l0-source-urls"],
            "parent_step_ids": ["l0-seed-intake"],
        },
        {
            "id": "l1-source-capture",
            "layer": 1,
            "name": "L1 source capture",
            "description": "Capture text, screenshot, and web snapshot evidence from the selected L0 URL.",
            "status": "complete",
            "started_at": now,
            "completed_at": now,
            "required_inputs": [],
            "artifact_ids": ["l1-careers-text", "l1-careers-screenshot", "l1-web-snapshot", "l1-web-snapshot-data"],
            "parent_step_ids": ["l0-url-discovery"],
        },
    ]
    artifacts = [
        {
            "id": "l0-intake-flow",
            "layer": 0,
            "type": "intake_flow",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l0-seed-intake",
            "parent_ids": [],
            "file_path": "l0-intake-flow.md",
            "params": {"slot": "intake.flow", "url": selected_url},
            "card": {"summary": f"{request.company} filled intake", "tags": {"layer": "L0"}},
        },
        {
            "id": "l0-source-urls",
            "layer": 0,
            "type": "url_list",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l0-url-discovery",
            "parent_ids": ["l0-intake-flow"],
            "file_path": "l0-source-urls.json",
            "params": {"slot": "l0.url_list", "url": selected_url},
            "card": {"summary": f"{request.company} L0 source URL candidates", "tags": {"layer": "L0"}},
        },
        {
            "id": "l1-careers-text",
            "layer": 1,
            "type": "text_capture",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l1-source-capture",
            "parent_ids": ["l0-source-urls"],
            "file_path": "l1-careers-text.txt",
            "params": {"slot": "l1.text_capture", "url": selected_url},
            "card": {"summary": f"{request.company} careers page text", "tags": {"layer": "L1"}},
        },
        {
            "id": "l1-careers-screenshot",
            "layer": 1,
            "type": "screenshot",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l1-source-capture",
            "parent_ids": ["l0-source-urls"],
            "file_path": "l1-careers-screenshot.png",
            "params": {"slot": "l1.screenshot", "url": selected_url},
            "card": {"summary": f"{request.company} careers page screenshot", "tags": {"layer": "L1"}},
        },
        {
            "id": "l1-web-snapshot",
            "layer": 1,
            "type": "html",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l1-source-capture",
            "parent_ids": ["l1-web-snapshot-data"],
            "file_path": "l1-web-snapshot.html",
            "params": {"slot": "l1.web_snapshot", "url": selected_url},
            "card": {"summary": f"{request.company} interactive web snapshot", "tags": {"layer": "L1"}},
        },
        {
            "id": "l1-web-snapshot-data",
            "layer": 1,
            "type": "web_snapshot_data",
            "status": "complete",
            "created_at": now,
            "produced_by_step_id": "l1-source-capture",
            "parent_ids": ["l0-source-urls"],
            "file_path": "l1-web-snapshot-data.json",
            "params": {"slot": "l1.web_snapshot_data", "url": selected_url},
            "card": {"summary": f"{request.company} web snapshot data", "tags": {"layer": "L1"}},
        },
    ]
    manifest = {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": f"intake-l0-l1-{slug}",
        "company": request.company,
        "domain": normalize_domain_hint(request.domain_hint)[0],
        "template_id": request.workflow_template,
        "talent_segment": request.talent_segment,
        "status": "complete",
        "created_at": now,
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "mermaid_source_visibility": "preview-hidden",
        },
        "required_inputs": manifest_required_inputs(request),
        "steps": steps,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def run_intake_capture(
    request: IntakeCaptureRequest,
    *,
    output_dir: Path | None = None,
    session: str = "eba-intake-l0-l1",
    width: int = 1365,
    height: int = 900,
) -> dict[str, Any]:
    slug = clean_slug(request.company)
    resolved_output = prepare_output_dir(output_dir or (DEFAULT_OUTPUT_ROOT / slug / "latest"))
    source_urls, selected_url = discover_source_urls(request)
    stage_dir = resolved_output / "url-stage"
    capture_url_stage(
        selected_url,
        slug=f"{slug}-l1",
        output_dir=stage_dir,
        session=session,
        width=width,
        height=height,
    )
    manifest_path = write_intake_capture_manifest(
        output_dir=resolved_output,
        request=request,
        source_urls=source_urls,
        selected_url=selected_url,
        stage_dir=stage_dir,
    )
    return {
        "status": "passed",
        "company": request.company,
        "domain_hint": request.domain_hint,
        "selected_url": selected_url,
        "source_urls": source_urls,
        "manifest": repo_relative(manifest_path),
        "artifact_root": repo_relative(resolved_output),
    }


def add_capture_intake_parser(workbench_subparsers: Any, fixture_choices: list[str]) -> Any:
    capture_intake = workbench_subparsers.add_parser(
        "capture-intake",
        help="Read filled bounded intake values and generate fresh L0/L1 capture artifacts",
    )
    capture_intake.add_argument("manifest", nargs="?", type=Path, help="Workbench manifest to read; defaults to active")
    capture_intake.add_argument("--fixture", choices=fixture_choices, help="Generate and read a named fixture")
    capture_intake.add_argument("--company", help="Override the workbench Company input")
    capture_intake.add_argument("--domain-hint", help="Override the workbench Domain hint input")
    capture_intake.add_argument("--talent-segment", help="Override the workbench Talent segment input")
    capture_intake.add_argument("--workflow-template", help="Override the workbench Workflow template input")
    capture_intake.add_argument("--output-dir", type=Path)
    capture_intake.add_argument("--capture-session", default="eba-intake-l0-l1")
    capture_intake.add_argument("--width", type=int, default=1365)
    capture_intake.add_argument("--height", type=int, default=900)
    capture_intake.add_argument("--no-browser", action="store_true", help="Do not switch the workbench to the generated L0/L1 manifest")
    capture_intake.add_argument("--json", action="store_true")
    return capture_intake
