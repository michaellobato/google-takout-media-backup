#!/usr/bin/env python3
"""
JSON lookup and supplemental index helpers.
"""

from __future__ import annotations

import os
import re

from process_media_config import ProcessMediaConfig
from process_media_suffix import normalize_title_variants, extract_google_suffix


def build_json_lookup(json_dir, cfg: ProcessMediaConfig | None = None):
    """Build a case-insensitive lookup: filename -> full path."""
    if cfg is None:
        raise ValueError("cfg is required for build_json_lookup")
    if json_dir is None:
        json_dir = cfg.json_repository_dir
    lookup = {}
    for filename in os.listdir(json_dir):
        if not filename.lower().endswith(".json"):
            continue
        lookup[filename.lower()] = os.path.join(json_dir, filename)
    return lookup


def build_supplemental_index(cfg: ProcessMediaConfig | None = None):
    """Build index of supplemental metadata files.
    Index structure: {base_name_without_suffix: [list of supplemental file paths]}
    Example: 'img_3136.mov' -> ['IMG_3136.MOV.supplemental-metadata.json',
                                  'IMG_3136.MOV.supplemental-metadata(1).json']
    Also supports '.sup.json' and '.sup(N).json' variants.
    """
    if cfg is None:
        raise ValueError("cfg is required for build_supplemental_index")
    index = {}
    for filename in os.listdir(cfg.json_repository_dir):
        lower = filename.lower()
        if not lower.endswith(".json"):
            continue
        if ".supplemental-metadata" in lower:
            base_name = re.split(r"\.supplemental-metadata", filename, flags=re.IGNORECASE)[0]
        elif re.search(r"\.sup(\(\d+\))?\.json$", lower, re.IGNORECASE):
            base_name = re.sub(r"\.sup(\(\d+\))?\.json$", "", filename, flags=re.IGNORECASE)
        else:
            continue

        base_keys = set()
        for variant in normalize_title_variants(base_name):
            base_keys.add(variant.lower())
            suffix = extract_google_suffix(variant)
            if suffix:
                base_keys.add(variant.replace(suffix, '').lower())

        full_path = os.path.join(cfg.json_repository_dir, filename)
        for key in base_keys:
            if key not in index:
                index[key] = []
            if full_path not in index[key]:
                index[key].append(full_path)
    return index


def find_all_supplemental_for_basename(basename, supplemental_index):
    """Find ALL supplemental metadata files for a given media file.
    Handles Google's suffix pattern and '.sup.json' variants.
    Returns list of paths to ALL matching supplemental files.
    """
    variants = normalize_title_variants(basename)
    suffix = None
    base_without_suffix = None
    for variant in variants:
        found = extract_google_suffix(variant)
        if found:
            suffix = found
            base_without_suffix = variant.replace(found, '')
            break

    if not base_without_suffix:
        base_without_suffix = basename

    base_name_key = base_without_suffix.lower()
    candidates = supplemental_index.get(base_name_key, [])
    if not candidates:
        return []

    expected = set()
    variants_with_suffix = set(variants)
    if suffix:
        suffix_after_ext = f"{base_without_suffix}{suffix}"
        variants_with_suffix.add(suffix_after_ext)
    if suffix:
        for base_no in normalize_title_variants(base_without_suffix):
            expected.add(f"{base_no}.supplemental-metadata{suffix}.json")
            expected.add(f"{base_no}.sup{suffix}.json")
        for variant in variants_with_suffix:
            expected.add(f"{variant}.supplemental-metadata.json")
            expected.add(f"{variant}.supplemental-metadata{suffix}.json")
            expected.add(f"{variant}.sup.json")
            expected.add(f"{variant}.sup{suffix}.json")
    else:
        for variant in variants:
            expected.add(f"{variant}.supplemental-metadata.json")
            expected.add(f"{variant}.sup.json")

    expected_lower = {name.lower() for name in expected}
    matching = []
    for path in candidates:
        filename = os.path.basename(path)
        if filename.lower() in expected_lower:
            matching.append(path)

    return matching
