#!/usr/bin/env python3
"""Serve a local artifact viewer with transient annotation state."""

import argparse
import json
import mimetypes
import posixpath
import shutil
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

try:
    from workbench_projection import project_workbench_manifest
except ModuleNotFoundError:
    from scripts.workbench_projection import project_workbench_manifest


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)

WORKBENCH_DIR = Path(__file__).resolve().parent / "workflow_artifact_workbench"
ARTIFACT_PRIMITIVES_DIR = Path(__file__).resolve().parent / "artifact_primitives"
WORKBENCH_INDEX = WORKBENCH_DIR / "index.html"
WORKBENCH_ASSETS = {
    "/assets/workflow-artifact-workbench.css": (WORKBENCH_DIR / "styles.css", "text/css"),
    "/assets/workflow-artifact-workbench.js": (WORKBENCH_DIR / "app.js", "text/javascript"),
    "/assets/workflow-artifact-workbench-icons.svg": (WORKBENCH_DIR / "icons.svg", "image/svg+xml"),
    "/assets/artifact-primitives/mermaid_renderer.js": (
        ARTIFACT_PRIMITIVES_DIR / "mermaid_renderer.js",
        "text/javascript",
    ),
    "/assets/artifact-primitives/markdown_renderer.js": (
        ARTIFACT_PRIMITIVES_DIR / "markdown_renderer.js",
        "text/javascript",
    ),
    "/assets/artifact-primitives/markdown_interactions.js": (
        ARTIFACT_PRIMITIVES_DIR / "markdown_interactions.js",
        "text/javascript",
    ),
    "/assets/artifact-primitives/image_viewer.js": (
        ARTIFACT_PRIMITIVES_DIR / "image_viewer.js",
        "text/javascript",
    ),
    "/assets/artifact-primitives/document_renderer.js": (
        ARTIFACT_PRIMITIVES_DIR / "document_renderer.js",
        "text/javascript",
    ),
    "/assets/artifact-primitives/vendor/mermaid.min.js": (
        ARTIFACT_PRIMITIVES_DIR / "vendor" / "mermaid.min.js",
        "text/javascript",
    ),
}


def read_workbench_html() -> str:
    return WORKBENCH_INDEX.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a local artifact viewer for supported workflow artifact manifests."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Matrix or ADR-002 audit manifest to view",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Deprecated no-op; use scripts/playwright_cli_workbench_gate.py surface to open the managed browser session",
    )
    return parser.parse_args()


def safe_manifest_path(path: Path) -> Path:
    manifest_path = path.resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if manifest_path.name != "manifest.json":
        raise SystemExit(f"Expected a supported manifest.json path: {manifest_path}")
    if REPO_ROOT not in manifest_path.parents:
        raise SystemExit(f"Manifest must be inside the repository: {manifest_path}")
    return manifest_path


def artifact_created_at(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(path.stat().st_mtime)


def safe_artifact_path(relative_path: str, artifact_root: Path) -> Path | None:
    candidate = (REPO_ROOT / relative_path).resolve()
    root = artifact_root.resolve()
    if not candidate.exists() or REPO_ROOT not in candidate.parents:
        return None
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def workbench_projected_artifact(artifact: dict[str, Any], artifact_root: Path) -> bool:
    artifact_type = artifact.get("type")
    if artifact_type not in {"image", "markdown", "json", "text", "log", "file"}:
        return False
    path = safe_artifact_path(str(artifact.get("path", "")), artifact_root)
    return path is not None


def collection_artifact(projected: dict[str, Any], artifact_root: Path) -> dict[str, Any]:
    path = safe_artifact_path(str(projected.get("path", "")), artifact_root)
    created_at_epoch = artifact_created_at(path) if path else None
    item = {
        "id": str(projected.get("id") or ""),
        "name": str(projected.get("name") or projected.get("id") or "Artifact"),
        "type": str(projected.get("type") or "file"),
        "kind": str(projected.get("kind") or projected.get("type") or "artifact"),
        "path": str(projected.get("path") or ""),
        "mime_type": str(projected.get("mime_type") or "application/octet-stream"),
        "capabilities": projected.get("capabilities") if isinstance(projected.get("capabilities"), list) else ["view"],
        "source_page": projected.get("source_page") if isinstance(projected.get("source_page"), dict) else None,
        "dimensions": projected.get("dimensions") if isinstance(projected.get("dimensions"), dict) else None,
        "created_at_epoch": created_at_epoch,
    }
    if path is not None:
        item["size_bytes"] = path.stat().st_size
    return item


def build_collection(manifest_path: Path, projection: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = projection or project_workbench_manifest(manifest_path)
    artifact_root = manifest_path.parent
    projected_artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), list) else []
    artifacts = [
        collection_artifact(projected, artifact_root)
        for projected in projected_artifacts
        if isinstance(projected, dict) and workbench_projected_artifact(projected, artifact_root)
    ]

    return {
        "id": f"artifact-collection:{manifest_path.relative_to(REPO_ROOT)}",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "source_format": payload.get("source", {}).get("format") if isinstance(payload.get("source"), dict) else None,
        "artifact_count": len(artifacts),
        "created_at_epoch": int(time.time()),
        "artifacts": artifacts,
    }


def clean_annotations(payload: Any, artifact_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return {}
    clean: dict[str, list[dict[str, Any]]] = {artifact_id_value: [] for artifact_id_value in artifact_ids}
    for item_id, annotations in payload.items():
        if item_id not in artifact_ids or not isinstance(annotations, list):
            continue
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            anchor = annotation.get("anchor")
            comment = str(annotation.get("comment", "")).strip()
            if not isinstance(anchor, dict) or not comment:
                continue
            clean_anchor = clean_annotation_anchor(anchor)
            if clean_anchor is None:
                continue
            try:
                clean[item_id].append(
                    {
                        "id": str(annotation.get("id") or f"{item_id}-{len(clean[item_id]) + 1}"),
                        "artifact_id": item_id,
                        "kind": str(annotation.get("kind") or "comment"),
                        "anchor": clean_anchor,
                        "comment": comment,
                        "created_at_epoch": int(annotation.get("created_at_epoch") or time.time()),
                        "updated_at_epoch": int(annotation["updated_at_epoch"])
                        if annotation.get("updated_at_epoch") is not None
                        else None,
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return clean


def clean_annotation_anchor(anchor: dict[str, Any]) -> dict[str, Any] | None:
    anchor_type = str(anchor.get("type") or "")
    if anchor_type == "image_region":
        rect = anchor.get("rect")
        if not isinstance(rect, dict):
            return None
        try:
            return {
                "type": "image_region",
                "coordinate_space": "natural_image",
                "rect": {
                    "x": int(rect["x"]),
                    "y": int(rect["y"]),
                    "width": int(rect["width"]),
                    "height": int(rect["height"]),
                },
            }
        except (KeyError, TypeError, ValueError):
            return None
    if anchor_type == "text_range":
        start = anchor.get("start")
        end = anchor.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None
        try:
            start_line = max(1, int(start["line"]))
            end_line = max(start_line, int(end["line"]))
            start_column = max(1, int(start.get("column", 1)))
            end_column = max(start_column if start_line == end_line else 1, int(end.get("column", 1)))
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "type": "text_range",
            "coordinate_space": "markdown_source",
            "start": {"line": start_line, "column": start_column},
            "end": {"line": end_line, "column": end_column},
            "excerpt": str(anchor.get("excerpt", ""))[:1000],
        }
    return None


class WorkbenchServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], manifest_path: Path):
        self.manifest_path = manifest_path
        self.artifact_root = manifest_path.parent
        self.workbench_projection = project_workbench_manifest(manifest_path)
        self.collection = build_collection(manifest_path, self.workbench_projection)
        self.artifacts_by_id = {item["id"]: item for item in self.collection["artifacts"]}
        self.annotations: dict[str, list[dict[str, Any]]] = {
            item["id"]: [] for item in self.collection["artifacts"]
        }
        self.updated_at_epoch = int(time.time())
        super().__init__(server_address, WorkbenchHandler)

    def annotation_state(self) -> dict[str, Any]:
        return {
            "status": "annotation_state",
            "collection": self.collection,
            "annotations": self.annotations,
            "updated_at_epoch": self.updated_at_epoch,
        }

    def replace_annotations(self, annotations: Any) -> None:
        artifact_ids = {item["id"] for item in self.collection["artifacts"]}
        self.annotations = clean_annotations(annotations, artifact_ids)
        self.updated_at_epoch = int(time.time())

    def artifact_path_by_id(self, artifact_id_value: str) -> Path | None:
        artifact = self.artifacts_by_id.get(artifact_id_value)
        if not artifact:
            return None
        return safe_artifact_path(str(artifact.get("path", "")), self.artifact_root)

    def write_markdown_artifact(self, artifact_id_value: str, content: str) -> dict[str, Any] | None:
        artifact = self.artifacts_by_id.get(artifact_id_value)
        if not artifact or artifact.get("type") != "markdown":
            return None
        path = self.artifact_path_by_id(artifact_id_value)
        if path is None:
            return None
        path.write_text(content, encoding="utf-8")
        artifact["created_at_epoch"] = artifact_created_at(path)
        artifact["size_bytes"] = path.stat().st_size
        return artifact


class WorkbenchHandler(BaseHTTPRequestHandler):
    server: WorkbenchServer

    def log_message(self, format: str, *args: object) -> None:
        print("[artifact-viewer] " + format % args, file=sys.stderr)

    def send_text(self, status: HTTPStatus, content: str, content_type: str = "text/plain") -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", f"{content_type}; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status: HTTPStatus, value: Any) -> None:
        data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.send_text(HTTPStatus.OK, read_workbench_html(), "text/html")
            return
        if parsed.path in WORKBENCH_ASSETS:
            self.serve_workbench_asset(parsed.path)
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path in {"/api/annotation-state", "/api/collection"}:
            self.send_json(HTTPStatus.OK, self.server.annotation_state())
            return
        if parsed.path == "/api/workbench-projection":
            self.send_json(HTTPStatus.OK, self.server.workbench_projection)
            return
        if parsed.path.startswith("/artifact/"):
            self.serve_artifact(parsed.path.removeprefix("/artifact/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_workbench_asset(self, asset_path: str) -> None:
        path, content_type = WORKBENCH_ASSETS[asset_path]
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_text(HTTPStatus.OK, path.read_text(encoding="utf-8"), content_type)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/annotation-state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("content-length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return
        self.server.replace_annotations(payload.get("annotations"))
        self.send_json(HTTPStatus.OK, self.server.annotation_state())

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/artifact-content/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        artifact_id_value = unquote(parsed.path.removeprefix("/api/artifact-content/"))
        length = int(self.headers.get("content-length", "0"))
        content = self.rfile.read(length).decode("utf-8")
        artifact = self.server.write_markdown_artifact(artifact_id_value, content)
        if artifact is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Markdown artifact not found"})
            return
        self.send_json(HTTPStatus.OK, {"status": "saved", "artifact": artifact})

    def serve_artifact(self, encoded_path: str) -> None:
        relative = Path(posixpath.normpath(unquote(encoded_path)))
        if relative.is_absolute() or ".." in relative.parts:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        artifact_path = safe_artifact_path(str(relative), self.server.artifact_root)
        if artifact_path is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(artifact_path.stat().st_size))
        self.end_headers()
        with artifact_path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)


def main() -> int:
    args = parse_args()
    manifest_path = safe_manifest_path(args.manifest)
    server = WorkbenchServer((args.host, args.port), manifest_path)
    host, port = server.server_address
    print(f"[artifact-viewer] serving {manifest_path}")
    print(f"[artifact-viewer] open http://{host}:{port}/")
    print(f"[artifact-viewer] annotation state http://{host}:{port}/api/annotation-state")
    print(f"[artifact-viewer] workbench projection http://{host}:{port}/api/workbench-projection")
    if args.open:
        print(
            "[artifact-viewer] --open is a no-op; use "
            "scripts/playwright_cli_workbench_gate.py surface for the managed eba-workbench browser session.",
            file=sys.stderr,
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[artifact-viewer] stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
