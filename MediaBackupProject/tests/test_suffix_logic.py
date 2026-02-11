#!/usr/bin/env python3
"""
Suffix Logic Test Suite (Strict Matching)

These tests validate the strict suffix rules used by the media-driven
matching logic in scripts/2-process-media.py:
- Only numeric (1–3 digit) suffixes are treated as Google duplicates.
- Unsuffixed media must NOT match suffixed JSON.
- Suffixed media must match ONLY the same suffix (before/after extension).
- No suffix guessing or (1..30) expansion.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_suffix import (
    extract_strict_media_suffix,
    generate_json_candidates_for_media,
)


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_extract_strict_media_suffix() -> bool:
    cases = [
        ("IMG_1234(2).JPG", "(2)"),
        ("IMG_1234.JPG(2)", "(2)"),
        ("IMG_1234(0).JPG", "(0)"),
        ("IMG_1234(2020).JPG", None),
        ("IMG_1234.JPG", None),
    ]
    ok = True
    for name, expected in cases:
        result = extract_strict_media_suffix(name)
        ok = ok and (result == expected)
        report("extract_strict_media_suffix", result == expected, f"{name} -> {result} (expected {expected})")
    return ok


def test_candidates_unsuffixed() -> bool:
    candidates = {c.lower() for c in generate_json_candidates_for_media("IMG_1234.JPG")}
    required = {
        "img_1234.jpg.json",
        "img_1234.jpeg.json",
        "img_1234.jpg.supplemental-metadata.json",
        "img_1234.jpg.sup.json",
        "img_1234.jpeg.supplemental-metadata.json",
        "img_1234.jpeg.sup.json",
    }
    forbidden = {
        "img_1234(1).jpg.json",
        "img_1234.jpg(1).json",
        "img_1234.jpg.supplemental-metadata(1).json",
        "img_1234.jpg.sup(1).json",
    }
    ok = required.issubset(candidates) and not (forbidden & candidates)
    detail = f"missing={sorted(required - candidates)}"
    return report("Candidates (unsuffixed)", ok, None if ok else detail)


def test_candidates_suffixed() -> bool:
    candidates = {c.lower() for c in generate_json_candidates_for_media("IMG_1234(2).JPG")}
    required = {
        "img_1234(2).jpg.json",
        "img_1234.jpg(2).json",
        "img_1234.jpg.supplemental-metadata(2).json",
        "img_1234(2).jpg.supplemental-metadata.json",
        "img_1234(2).jpg.supplemental-metadata(2).json",
        "img_1234.jpg(2).supplemental-metadata.json",
        "img_1234.jpg(2).supplemental-metadata(2).json",
        "img_1234(2).jpg.sup.json",
        "img_1234(2).jpg.sup(2).json",
        "img_1234.jpg.sup(2).json",
        "img_1234.jpg(2).sup.json",
        "img_1234.jpg(2).sup(2).json",
    }
    forbidden = {
        "img_1234.jpg.json",
        "img_1234.jpg.supplemental-metadata.json",
        "img_1234.jpg.sup.json",
        "img_1234(1).jpg.json",
    }
    ok = required.issubset(candidates) and not (forbidden & candidates)
    detail = f"missing={sorted(required - candidates)}"
    return report("Candidates (suffixed)", ok, None if ok else detail)


def test_candidates_ignore_year_suffix() -> bool:
    candidates = {c.lower() for c in generate_json_candidates_for_media("IMG_1234(2020).JPG")}
    forbidden = {
        "img_1234.jpg(2020).json",
        "img_1234.jpg.supplemental-metadata(2020).json",
        "img_1234.jpg.sup(2020).json",
    }
    ok = not (forbidden & candidates)
    return report("Candidates (ignore year-like suffix)", ok)


def test_real_world_scenario() -> bool:
    candidates = {c.lower() for c in generate_json_candidates_for_media("MOVIE(26).mp4")}
    required = {
        "movie(26).mp4.json",
        "movie.mp4(26).json",
        "movie.mp4.supplemental-metadata(26).json",
        "movie(26).mp4.supplemental-metadata.json",
        "movie(26).mp4.sup.json",
        "movie.mp4.sup(26).json",
    }
    ok = required.issubset(candidates)
    detail = f"missing={sorted(required - candidates)}"
    return report("Real-world suffix scenario", ok, None if ok else detail)


def main() -> int:
    print()
    print("=" * 70)
    print(" SUFFIX LOGIC TEST SUITE ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_extract_strict_media_suffix()
    passed &= test_candidates_unsuffixed()
    passed &= test_candidates_suffixed()
    passed &= test_candidates_ignore_year_suffix()
    passed &= test_real_world_scenario()

    print()
    if passed:
        print("[SUCCESS] ALL TESTS PASSED! Strict suffix logic is correct.")
        return 0

    print("[ERROR] SOME TESTS FAILED! Do not run on real data yet.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
