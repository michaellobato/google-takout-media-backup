#!/usr/bin/env python3
"""
Tests for filename/suffix normalization and candidate generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_suffix import (
    normalize_title_variants,
    extract_google_suffix,
    extract_suffix_from_json_filename,
    generate_takeout_filename_candidates,
)


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_normalize_title_variants() -> bool:
    variants = normalize_title_variants("IMG_1234.jpg(1)")
    return report(
        "normalize_title_variants (suffix after ext)",
        "IMG_1234(1).jpg" in variants and "IMG_1234.jpg(1)" in variants,
        f"variants={sorted(variants)}",
    )


def test_extract_google_suffix() -> bool:
    ok1 = extract_google_suffix("IMG_1234(2).MOV") == "(2)"
    ok2 = extract_google_suffix("IMG_1234.MOV") is None
    return report("extract_google_suffix", ok1 and ok2)


def test_extract_suffix_from_json_filename() -> bool:
    ok1 = extract_suffix_from_json_filename("IMG_1234.jpg(15).json") == "(15)"
    ok2 = extract_suffix_from_json_filename("IMG_1234.jpg.json") is None
    return report("extract_suffix_from_json_filename", ok1 and ok2)


def test_generate_candidates_with_suffix() -> bool:
    candidates = generate_takeout_filename_candidates("IMG_0001.jpg", "(15)")
    required = {"IMG_0001(15).jpg", "IMG_0001-edited(15).jpg"}
    forbidden = {"IMG_0001(1).jpg", "IMG_0001(2).jpg"}
    ok = required.issubset(set(candidates)) and not (forbidden & set(candidates))
    return report("generate_takeout_filename_candidates (with suffix)", ok)


def test_generate_candidates_extension_variants() -> bool:
    candidates = generate_takeout_filename_candidates("PHOTO.jpeg", None)
    ok = "PHOTO.jpg" in candidates
    return report("generate_takeout_filename_candidates (ext variants)", ok)


def main() -> int:
    print()
    print("=" * 70)
    print(" FILENAME LOGIC TESTS ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_normalize_title_variants()
    passed &= test_extract_google_suffix()
    passed &= test_extract_suffix_from_json_filename()
    passed &= test_generate_candidates_with_suffix()
    passed &= test_generate_candidates_extension_variants()

    print()
    if passed:
        print("[SUCCESS] Filename logic tests passed.")
        return 0

    print("[ERROR] Filename logic tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
