"""Neutral HTML view helpers for publication pipeline archetypes."""

from __future__ import annotations

from html import escape

from .core import table_rows


def publication_table_body(title: str, rows: list[list[str]]) -> str:
    return f"""    <section>
      <h2>{escape(title)}</h2>
      <table>
        <tr><th>Item</th><th>Detail</th><th>Evidence</th></tr>
{table_rows(rows)}
      </table>
    </section>
"""
