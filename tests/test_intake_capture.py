from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_FOR_IMPORTS))

from scripts.intake_capture import (
    IntakeCaptureRequest,
    build_candidate_urls,
    extract_intake_request,
    write_intake_capture_manifest,
)
from scripts.intake_l0_l1_fixture import generate_intake_l0_l1_fixture
from scripts.workbench_projection import project_workbench_manifest


class IntakeCaptureTests(unittest.TestCase):
    def test_blank_fixture_projects_empty_intake_overlays_without_sample_subjects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = generate_intake_l0_l1_fixture(Path(tmp) / "blank")
            combined_text = "\n".join(path.read_text(encoding="utf-8") for path in manifest_path.parent.glob("*"))
            projection = project_workbench_manifest(manifest_path)

            self.assertNotIn("Acme Robotics", combined_text)
            self.assertNotIn("Apple", combined_text)
            self.assertIn("flowchart TB", combined_text)
            values = {
                item["input_id"]: item.get("value")
                for item in projection["workflow"]["input_overlays"]
            }
            self.assertEqual(values["company"], None)
            self.assertEqual(values["domain_hint"], None)
            self.assertEqual(values["talent_segment"], None)

    def test_capture_intake_parser_is_registered(self) -> None:
        from scripts.eba_cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "dev",
            "workbench",
            "capture-intake",
            "--company",
            "Apple",
            "--domain-hint",
            "apple.com",
            "--no-browser",
            "--json",
        ])

        self.assertEqual(args.command, "workbench")
        self.assertEqual(args.workbench_action, "capture-intake")
        self.assertEqual(args.company, "Apple")
        self.assertEqual(args.domain_hint, "apple.com")

    def test_extract_intake_request_uses_filled_bounded_inputs(self) -> None:
        state = {
            "bounded_inputs": {
                "values": {
                    "l0-seed-intake.company": "Apple",
                    "l0-seed-intake.domain_hint": "apple.com",
                    "l0-seed-intake.talent_segment": "Retail and corporate talent",
                    "l0-seed-intake.workflow_template": "standard-audit",
                }
            }
        }

        request = extract_intake_request(state)

        self.assertEqual(request.company, "Apple")
        self.assertEqual(request.domain_hint, "apple.com")
        self.assertEqual(request.talent_segment, "Retail and corporate talent")

    def test_extract_intake_request_blocks_when_domain_is_missing(self) -> None:
        state = {
            "bounded_inputs": {
                "values": {
                    "l0-seed-intake.company": "A Very Local Employer",
                    "l0-seed-intake.talent_segment": "Engineering",
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "domain"):
            extract_intake_request(state)

    def test_candidate_urls_include_apple_careers_entry_points(self) -> None:
        candidates = build_candidate_urls("Apple", "apple.com")

        self.assertEqual(candidates[0], "https://www.apple.com/careers/us/")
        self.assertIn("https://www.apple.com/careers/", candidates)
        self.assertIn("https://apple.com/careers/", candidates)

    def test_write_manifest_uses_intake_subject_and_l0_l1_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            stage_dir = output_dir / "url-stage"
            stage_dir.mkdir()
            stage_dir.joinpath("page.full-page.png").write_bytes(b"png")
            stage_dir.joinpath("web-snapshot.html").write_text("<html>Apple careers</html>", encoding="utf-8")
            stage_dir.joinpath("web-snapshot-data.json").write_text(
                json.dumps(
                    {
                        "source_url": "https://www.apple.com/careers/us/",
                        "title": "Apple Careers",
                        "projections": {
                            "visible_text": {
                                "text": "Apple careers\nRetail jobs\n",
                                "lines": ["Apple careers", "Retail jobs"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            manifest_path = write_intake_capture_manifest(
                output_dir=output_dir,
                request=IntakeCaptureRequest(
                    company="Apple",
                    domain_hint="apple.com",
                    talent_segment="Retail and corporate talent",
                    workflow_template="standard-audit",
                ),
                source_urls=[
                    {
                        "url": "https://www.apple.com/careers/us/",
                        "role": "careers_home",
                        "status": "selected",
                    }
                ],
                selected_url="https://www.apple.com/careers/us/",
                stage_dir=stage_dir,
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["company"], "Apple")
            self.assertEqual(manifest["domain"], "apple.com")
            self.assertEqual(
                [artifact["id"] for artifact in manifest["artifacts"]],
                [
                    "l0-intake-flow",
                    "l0-source-urls",
                    "l1-careers-text",
                    "l1-careers-screenshot",
                    "l1-web-snapshot",
                    "l1-web-snapshot-data",
                ],
            )
            self.assertIn("Apple", output_dir.joinpath("l0-intake-flow.md").read_text(encoding="utf-8"))
            self.assertIn("flowchart TB", output_dir.joinpath("l0-intake-flow.md").read_text(encoding="utf-8"))
            self.assertIn("Apple careers", output_dir.joinpath("l1-careers-text.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
