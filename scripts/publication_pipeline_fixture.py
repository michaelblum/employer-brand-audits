#!/usr/bin/env python3
"""Compatibility entrypoint for publication pipeline fixture generation."""

from __future__ import annotations

try:
    from scripts.publication_pipeline import *  # noqa: F403
    from scripts.publication_pipeline import main
except ImportError:
    from publication_pipeline import *  # type: ignore # noqa: F403
    from publication_pipeline import main  # type: ignore


if __name__ == "__main__":
    raise SystemExit(main())
