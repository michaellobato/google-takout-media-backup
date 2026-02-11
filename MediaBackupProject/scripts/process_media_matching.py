#!/usr/bin/env python3
"""
Matching helpers for media files and JSON metadata.
"""

from __future__ import annotations

import re

from process_media_suffix import generate_json_candidates_for_media


def is_supplemental_json_name(filename: str) -> bool:
    lower = filename.lower()
    if ".supplemental-metadata" in lower:
        return True
    return re.search(r"\.sup(\(\d+\))?\.json$", lower, re.IGNORECASE) is not None


def match_json_for_media(media_filename: str, json_lookup: dict[str, str]) -> tuple[list[str], list[str]]:
    """Return (primary_paths, supplemental_paths) for a given media file."""
    candidates = generate_json_candidates_for_media(media_filename)
    primary: list[str] = []
    supplemental: list[str] = []

    for name in candidates:
        path = json_lookup.get(name.lower())
        if not path:
            continue
        if is_supplemental_json_name(name):
            supplemental.append(path)
        else:
            primary.append(path)

    return primary, supplemental
