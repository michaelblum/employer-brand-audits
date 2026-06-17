#!/usr/bin/env python3
"""Focused checks for local workbench server HTTP hardening."""

from __future__ import annotations

import http.client
import json
import sys
import threading
import unittest
from http import HTTPStatus
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.playwright_cli_workbench_server import WorkbenchServer


HARDENING_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "workbench-hardening" / "manifest.json"


class RunningWorkbenchServer:
    def __init__(self) -> None:
        self.server = WorkbenchServer(("127.0.0.1", 0), HARDENING_MANIFEST)
        self.host, self.port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "RunningWorkbenchServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def same_origin(self) -> str:
        return f"http://{self.host}:{self.port}"

    def request(
        self,
        method: str,
        path: str,
        body: bytes | str = b"",
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[http.client.HTTPResponse, bytes]:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            connection.request(method, path, body=payload, headers=headers or {})
            response = connection.getresponse()
            data = response.read()
            return response, data
        finally:
            connection.close()

    def request_with_content_length(
        self,
        method: str,
        path: str,
        content_length: int,
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[http.client.HTTPResponse, bytes]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            connection.putrequest(method, path)
            for key, value in (headers or {}).items():
                connection.putheader(key, value)
            connection.putheader("content-length", str(content_length))
            connection.endheaders()
            response = connection.getresponse()
            data = response.read()
            return response, data
        finally:
            connection.close()


class WorkbenchServerHardeningTests(unittest.TestCase):
    def test_hardening_tests_are_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        self.assertIn(
            [sys.executable, "tests/test_workbench_server_hardening.py"],
            validation_commands(),
        )

    def test_json_responses_send_nosniff(self) -> None:
        with RunningWorkbenchServer() as server:
            response, _ = server.request("GET", "/api/workbench-state")

        self.assertEqual(HTTPStatus.OK, response.status)
        self.assertEqual("nosniff", response.getheader("x-content-type-options"))

    def test_same_origin_mutation_still_updates_view_state(self) -> None:
        with RunningWorkbenchServer() as server:
            payload = json.dumps({"view": {"active_artifact_id": "l1-careers-text"}})
            response, data = server.request(
                "POST",
                "/api/workbench-state",
                payload,
                headers={
                    "content-type": "application/json",
                    "origin": server.same_origin,
                },
            )

        self.assertEqual(HTTPStatus.OK, response.status)
        body = json.loads(data)
        self.assertEqual("l1-careers-text", body["view"]["active_artifact_id"])

    def test_cross_origin_mutations_are_rejected_before_path_specific_handling(self) -> None:
        blocked_requests = [
            ("POST", "/api/workbench-state", "{}"),
            ("POST", "/api/workbench-context", "{}"),
            ("PUT", "/api/artifact-content/not-a-real-artifact", "content"),
        ]
        with RunningWorkbenchServer() as server:
            for method, path, payload in blocked_requests:
                with self.subTest(method=method, path=path):
                    response, data = server.request(
                        method,
                        path,
                        payload,
                        headers={
                            "content-type": "application/json",
                            "origin": "https://attacker.example",
                        },
                    )

                    self.assertEqual(HTTPStatus.FORBIDDEN, response.status)
                    body: Any = json.loads(data)
                    self.assertEqual("Cross-origin mutation rejected", body["error"])

    def test_cross_origin_mutation_cannot_bypass_with_spoofed_host_header(self) -> None:
        with RunningWorkbenchServer() as server:
            response, data = server.request(
                "POST",
                "/api/workbench-state",
                json.dumps({"view": {"active_artifact_id": "l1-careers-text"}}),
                headers={
                    "content-type": "application/json",
                    "origin": f"http://evil.test:{server.port}",
                    "host": f"evil.test:{server.port}",
                },
            )

        self.assertEqual(HTTPStatus.FORBIDDEN, response.status)
        self.assertEqual({"error": "Cross-origin mutation rejected"}, json.loads(data))

    def test_malformed_utf8_mutation_bodies_get_clean_json_400(self) -> None:
        invalid_utf8 = b'{"broken":"\xff"}'
        blocked_requests = [
            ("POST", "/api/workbench-state", invalid_utf8),
            ("PUT", "/api/artifact-content/l0-intake-flow", invalid_utf8),
        ]
        with RunningWorkbenchServer() as server:
            for method, path, payload in blocked_requests:
                with self.subTest(method=method, path=path):
                    response, data = server.request(
                        method,
                        path,
                        payload,
                        headers={
                            "content-type": "application/json",
                            "origin": server.same_origin,
                        },
                    )

                    self.assertEqual(HTTPStatus.BAD_REQUEST, response.status)
                    self.assertEqual("application/json; charset=utf-8", response.getheader("content-type"))
                    self.assertEqual("nosniff", response.getheader("x-content-type-options"))
                    self.assertEqual({"error": "Invalid UTF-8 request body"}, json.loads(data))

    def test_oversized_mutation_body_gets_clean_json_413(self) -> None:
        with RunningWorkbenchServer() as server:
            response, data = server.request_with_content_length(
                "POST",
                "/api/workbench-state",
                2 * 1024 * 1024,
                headers={"content-type": "application/json", "origin": server.same_origin},
            )

        self.assertEqual(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, response.status)
        self.assertEqual("application/json; charset=utf-8", response.getheader("content-type"))
        self.assertEqual("nosniff", response.getheader("x-content-type-options"))
        self.assertEqual({"error": "Request body too large"}, json.loads(data))


if __name__ == "__main__":
    unittest.main()
