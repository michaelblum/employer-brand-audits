"""Neutral workbook-style profile and entity helpers for publication archetypes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH, load_project_profile, slugify


def load_workbook_profile(
    path: Path | None = None,
    *,
    default_path: Path = COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH,
) -> dict[str, Any]:
    profile = load_project_profile(path or default_path)
    if "workbook_entities" not in profile:
        profile["workbook_entities"] = [profile.get("client_full_name") or profile.get("client_name") or "Client"] + [
            competitor.get("name")
            for competitor in profile.get("competitors") or []
            if isinstance(competitor, dict)
        ]
    return profile


def workbook_entities(profile: dict[str, Any]) -> list[dict[str, Any]]:
    names = list(profile.get("workbook_entities") or [])
    if not names:
        names = [profile.get("client_full_name") or profile.get("client_name") or "Client"]
    entities = []
    for index, name_value in enumerate(names[:8]):
        name = str(name_value or f"Entity {index + 1}")
        role = "client" if index == 0 else "competitor"
        entities.append(
            {
                "entity_id": f"{role}-{slugify(name)}",
                "name": name,
                "role": role,
                "column_letter": chr(ord("C") + index),
                "careers_url": f"https://{slugify(name)}.example/careers",
                "dei_url": "" if index == 5 else f"https://{slugify(name)}.example/diversity",
                "headline": f"{name} careers headline",
            }
        )
    return entities


def workbook_source_roster(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(profile.get("project_id") or f"{slugify(str(profile.get('client_name') or 'client'))}-competitor-workbook"),
        "entities": [
            {
                "entity_id": entity["entity_id"],
                "name": entity["name"],
                "role": entity["role"],
                "column_letter": entity["column_letter"],
                "source_urls": {
                    "careers_url": entity["careers_url"],
                    "dei_url": entity["dei_url"] or "not_found",
                },
                "headline": entity["headline"],
            }
            for entity in workbook_entities(profile)
        ],
    }


def workbook_partner_orgs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    focus_values = ["gender", "ethnicity", "LGBTQ+", "socioeconomic", "disability", "caregivers"]
    return [
        {
            "partner_org_id": f"partner:{index:02d}",
            "name": f"Partner Network {index:02d}",
            "primary_geography": "Global" if index % 3 == 0 else "United States",
            "dei_focus": focus_values[index % len(focus_values)],
            "organisation_type": "network" if index % 2 else "benchmark",
            "source_sheet": "Partner orgs",
            "source_range": f"A{index + 7}:D{index + 7}",
        }
        for index in range(1, 31)
    ]


def load_competitor_workbook_profile(path: Path | None = None) -> dict[str, Any]:
    return load_workbook_profile(path, default_path=COMPETITOR_WORKBOOK_DEFAULT_PROFILE_PATH)
