#!/usr/bin/env python3
"""Focused checks for bounded-input projection and saved-state contracts."""

import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.workbench_bounded_input import (
    bounded_input_key,
    bounded_input_overlay_definition,
    bounded_input_overlay_definitions_for_step,
    bounded_input_state,
    clean_bounded_input_overlay,
)


class WorkbenchBoundedInputTest(unittest.TestCase):
    def test_bounded_input_contract_is_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        commands = validation_commands()
        self.assertIn([sys.executable, "tests/test_workbench_bounded_input.py"], commands)
        self.assertIn("scripts/workbench_bounded_input.py", commands[0])

    def test_overlay_definition_preserves_workflow_input_contract(self) -> None:
        overlay = bounded_input_overlay_definition(
            "l0-seed-intake",
            {
                "id": "workflow_template",
                "label": "Workflow template",
                "artifact_id": "l0-intake-flow",
                "input_type": "select",
                "placeholder": "Choose a workflow",
                "required": True,
                "status": "pending",
                "value": "foundational",
                "selector_candidates": [
                    '[data-workflow-step-id="l0-seed-intake"]',
                    "",
                    "g.node[data-id='intake']",
                ],
                "options": [
                    {"value": "foundational", "label": "Foundational audit"},
                    "tech-talent-audit",
                    {"missing": "value"},
                    None,
                ],
                "target_link": {
                    "color": "#38bdf8",
                    "speed": 0.75,
                    "geometry": {"highlightInset": 6},
                },
            },
        )

        self.assertEqual(
            overlay,
            {
                "id": "input:l0-seed-intake:workflow_template",
                "subtype": "bounded_input",
                "step_id": "l0-seed-intake",
                "input_id": "workflow_template",
                "label": "Workflow template",
                "input_type": "select",
                "required": True,
                "status": "pending",
                "value": "foundational",
                "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                "anchor": {
                    "type": "workflow_input",
                    "coordinate_space": "workflow_graph",
                    "artifact_id": "l0-intake-flow",
                    "step_id": "l0-seed-intake",
                    "input_id": "workflow_template",
                    "selector_candidates": [
                        '[data-workflow-step-id="l0-seed-intake"]',
                        "g.node[data-id='intake']",
                    ],
                },
                "placeholder": "Choose a workflow",
                "options": [
                    {"value": "foundational", "label": "Foundational audit"},
                    "tech-talent-audit",
                    {"missing": "value"},
                ],
                "target_link": {
                    "color": "#38bdf8",
                    "speed": 0.75,
                    "geometry": {"highlightInset": 6},
                },
            },
        )

    def test_overlay_definitions_reject_missing_identity(self) -> None:
        self.assertIsNone(bounded_input_overlay_definition("l0-seed-intake", None))
        self.assertIsNone(bounded_input_overlay_definition("", {"id": "company", "artifact_id": "flow"}))
        self.assertIsNone(bounded_input_overlay_definition("l0-seed-intake", {"artifact_id": "flow"}))
        self.assertIsNone(bounded_input_overlay_definition("l0-seed-intake", {"id": "company"}))

        self.assertEqual(
            bounded_input_overlay_definitions_for_step(
                "l0-seed-intake",
                [
                    {"id": "company", "artifact_id": "l0-intake-flow"},
                    {"id": "", "artifact_id": "l0-intake-flow"},
                    "not-a-dict",
                ],
            ),
            [
                {
                    "id": "input:l0-seed-intake:company",
                    "subtype": "bounded_input",
                    "step_id": "l0-seed-intake",
                    "input_id": "company",
                    "label": "Company",
                    "input_type": "text",
                    "required": True,
                    "status": "pending",
                    "value": None,
                    "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                    "anchor": {
                        "type": "workflow_input",
                        "coordinate_space": "workflow_graph",
                        "artifact_id": "l0-intake-flow",
                        "step_id": "l0-seed-intake",
                        "input_id": "company",
                    },
                }
            ],
        )

    def test_clean_bounded_input_overlay_accepts_only_projected_definitions(self) -> None:
        overlay = {
            "id": "input:l0-seed-intake:company",
            "subtype": "bounded_input",
            "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
            "anchor": {
                "type": "workflow_input",
                "coordinate_space": "workflow_graph",
                "artifact_id": "l0-intake-flow",
                "step_id": "l0-seed-intake",
                "input_id": "company",
                "selector_candidates": ["should-not-round-trip"],
            },
            "body": {"kind": "input_value", "value": "Acme Robotics"},
            "created_at_epoch": 1781564957,
            "updated_at_epoch": 1781564999,
        }

        self.assertEqual(
            clean_bounded_input_overlay(
                overlay,
                {"l0-intake-flow"},
                {("l0-seed-intake", "company")},
            ),
            {
                "id": "input:l0-seed-intake:company",
                "subtype": "bounded_input",
                "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                "anchor": {
                    "type": "workflow_input",
                    "coordinate_space": "workflow_graph",
                    "artifact_id": "l0-intake-flow",
                    "step_id": "l0-seed-intake",
                    "input_id": "company",
                },
                "body": {"kind": "input_value", "value": "Acme Robotics"},
                "created_at_epoch": 1781564957,
                "updated_at_epoch": 1781564999,
            },
        )
        self.assertIsNone(clean_bounded_input_overlay(overlay, {"l0-intake-flow"}, {("l0-seed-intake", "domain_hint")}))
        self.assertIsNone(clean_bounded_input_overlay(overlay, {"other-artifact"}, {("l0-seed-intake", "company")}))

    def test_bounded_input_state_merges_saved_values_with_defaults(self) -> None:
        definitions = [
            {"step_id": "l0-seed-intake", "input_id": "company", "value": "Default Co"},
            {"step_id": "l0-seed-intake", "input_id": "domain_hint", "value": "default.example"},
        ]
        overlays = [
            {
                "subtype": "bounded_input",
                "anchor": {"type": "workflow_input", "step_id": "l0-seed-intake", "input_id": "company"},
                "body": {"kind": "input_value", "value": "Acme Robotics"},
            }
        ]

        self.assertEqual(bounded_input_key(overlays[0]), ("l0-seed-intake", "company"))
        self.assertEqual(
            bounded_input_state(definitions, overlays),
            {
                "status": "bounded_inputs",
                "items": [
                    {
                        "step_id": "l0-seed-intake",
                        "input_id": "company",
                        "value": "Acme Robotics",
                        "status": "filled",
                    },
                    {
                        "step_id": "l0-seed-intake",
                        "input_id": "domain_hint",
                        "value": "default.example",
                        "status": "filled",
                    },
                ],
                "values": {
                    "l0-seed-intake.company": "Acme Robotics",
                    "l0-seed-intake.domain_hint": "default.example",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
