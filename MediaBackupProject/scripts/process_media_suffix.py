#!/usr/bin/env python3
"""
Filename and suffix handling helpers.
"""

from __future__ import annotations

import os
import re

# Google Takeout truncates the filename portion (excluding extension) to 47 characters.
# The full original filename is preserved in the JSON metadata "title" field.
GOOGLE_TAKEOUT_FILENAME_LIMIT = 47


def normalize_title_variants(true_filename: str) -> set[str]:
    """Handle titles that include a uniqueness suffix after the extension."""
    variants = {true_filename}
    match = re.match(r"^(?P<name>.+?)(?P<ext>\.[^.]+)(?P<suffix>\(\d+\))$", true_filename)
    if match:
        name = match.group("name")
        ext = match.group("ext")
        suffix = match.group("suffix")
        variants.add(f"{name}{suffix}{ext}")
    return variants


def generate_takeout_filename_candidates(true_filename: str, json_suffix: str | None = None) -> list[str]:
    """V5+ logic with edited suffix truncation and uniqueness placement variants.

    Args:
        true_filename: The filename from the JSON title field
        json_suffix: Optional suffix extracted from JSON filename (e.g., '(15)')
                     If provided, only generates candidates for this specific suffix.
                     If None, generates candidates for suffixes (1) through (30).
    """
    if not true_filename:
        return []
    candidates = set()
    base_variants = set()
    for variant in normalize_title_variants(true_filename):
        base_variants.add(variant)
        base_variants.add(variant.replace('&', '_').replace('?', '_'))
    base_filenames_to_process = base_variants
    for base_filename in base_filenames_to_process:
        name_part, extension = os.path.splitext(base_filename)
        name_to_process = name_part[:GOOGLE_TAKEOUT_FILENAME_LIMIT] if len(name_part) > GOOGLE_TAKEOUT_FILENAME_LIMIT else name_part
        candidates.add(name_to_process + extension)
        edited_name = (name_part + "-edited")[:GOOGLE_TAKEOUT_FILENAME_LIMIT]
        candidates.add(edited_name + extension)

        # If we know the specific suffix from the JSON filename, use it
        if json_suffix:
            candidates.add(name_to_process + json_suffix + extension)
            candidates.add(edited_name + json_suffix + extension)
            candidates.add(name_to_process + "-edited" + json_suffix + extension)
        else:
            # No suffix info - generate candidates for range (1) through (30)
            for i in range(1, 31):
                candidates.add(name_to_process + f"({i})" + extension)
                candidates.add(edited_name + f"({i})" + extension)
                candidates.add(name_to_process + f"-edited({i})" + extension)

    # Add .jpg/.jpeg variations
    extension_variations = set()
    for candidate in candidates:
        name, ext = os.path.splitext(candidate)
        if ext.lower() == '.jpeg':
            extension_variations.add(name + '.jpg')
        elif ext.lower() == '.jpg':
            extension_variations.add(name + '.jpeg')

    return list(candidates.union(extension_variations))


def extract_google_suffix(filename: str) -> str | None:
    """Extract Google's (1), (2) suffix from filename like 'IMG_123(1).MOV' -> '(1)'"""
    match = re.search(r'(\(\d+\))(\.[^.]+)$', filename)
    if match:
        return match.group(1)  # Returns '(1)', '(2)', etc.
    return None


def extract_suffix_from_json_filename(json_filename: str) -> str | None:
    """Extract Google's suffix from JSON filename like 'IMG_1234.jpg(15).json' -> '(15)'
    JSON files have pattern: basename.media_ext(N).json"""
    match = re.search(r'(\(\d+\))\.json$', json_filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_strict_media_suffix(filename: str) -> str | None:
    """Extract suffix only when it looks like a Google duplicate: (1) to (999).
    Supports suffix before or after extension.
    Returns '(N)' or None.
    """
    match = re.match(r"^(.+)\((\d{1,3})\)(\.[^.]+)$", filename)
    if match:
        return f"({match.group(2)})"
    match = re.match(r"^(.+\.[^.]+)\((\d{1,3})\)$", filename)
    if match:
        return f"({match.group(2)})"
    return None


def split_media_suffix(filename: str) -> tuple[str, str | None, str | None, str | None]:
    """Return (base_without_suffix, suffix, suffix_after_ext_variant, suffix_before_ext_variant)."""
    match = re.match(r"^(?P<name>.+)\((?P<num>\d{1,3})\)(?P<ext>\.[^.]+)$", filename)
    if match:
        suffix = f"({match.group('num')})"
        base_without_suffix = f"{match.group('name')}{match.group('ext')}"
        suffix_after_ext = f"{base_without_suffix}{suffix}"
        suffix_before_ext = filename
        return base_without_suffix, suffix, suffix_after_ext, suffix_before_ext
    match = re.match(r"^(?P<base>.+\.[^.]+)\((?P<num>\d{1,3})\)$", filename)
    if match:
        suffix = f"({match.group('num')})"
        base_without_suffix = match.group("base")
        name, ext = os.path.splitext(base_without_suffix)
        suffix_before_ext = f"{name}{suffix}{ext}"
        suffix_after_ext = filename
        return base_without_suffix, suffix, suffix_after_ext, suffix_before_ext
    return filename, None, None, None


def with_extension_variants(filename: str) -> set[str]:
    variants = {filename}
    name, ext = os.path.splitext(filename)
    if ext.lower() == ".jpg":
        variants.add(name + ".jpeg")
    elif ext.lower() == ".jpeg":
        variants.add(name + ".jpg")
    return variants


def generate_json_candidates_for_media(media_filename: str) -> list[str]:
    """Generate exact candidate JSON filenames for a media file.
    No suffix guessing; only matches the media's suffix if present.
    """
    base_without_suffix, suffix, suffix_after_ext, suffix_before_ext = split_media_suffix(media_filename)

    variants = {media_filename}
    if suffix and suffix_after_ext and suffix_before_ext:
        variants.add(suffix_after_ext)
        variants.add(suffix_before_ext)

    variants_with_ext = set()
    for variant in variants:
        variants_with_ext.update(with_extension_variants(variant))

    candidates = set()
    # Primary JSON candidates
    for variant in variants_with_ext:
        candidates.add(f"{variant}.json")

    # Supplemental JSON candidates
    if suffix:
        base_variants = set()
        for base in with_extension_variants(base_without_suffix):
            base_variants.add(base)
        for base in base_variants:
            candidates.add(f"{base}.supplemental-metadata{suffix}.json")
            candidates.add(f"{base}.sup{suffix}.json")
        for variant in variants_with_ext:
            candidates.add(f"{variant}.supplemental-metadata.json")
            candidates.add(f"{variant}.supplemental-metadata{suffix}.json")
            candidates.add(f"{variant}.sup.json")
            candidates.add(f"{variant}.sup{suffix}.json")
    else:
        for variant in variants_with_ext:
            candidates.add(f"{variant}.supplemental-metadata.json")
            candidates.add(f"{variant}.sup.json")

    return sorted(candidates)
