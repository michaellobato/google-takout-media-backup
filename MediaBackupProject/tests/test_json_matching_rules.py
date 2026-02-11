#!/usr/bin/env python3
"""
Tests for media-driven JSON matching rules (planned rewrite).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_suffix import generate_json_candidates_for_media
from process_media_matching import match_json_for_media


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_candidates_unsuffixed() -> bool:
    candidates = {c.lower() for c in generate_json_candidates_for_media("IMG_1234.JPG")}
    required = {
        "img_1234.jpg.json",
        "img_1234.jpg.supplemental-metadata.json",
        "img_1234.jpg.sup.json",
        "img_1234.jpeg.json",
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


def test_match_json_for_media() -> bool:
    lookup = {
        "img_1234.jpg.json": "P1",
        "img_1234.jpg.supplemental-metadata.json": "S1",
        "img_1234.jpg.sup.json": "S2",
        "img_1234.jpg(2).json": "P2",
        "img_1234.jpg.supplemental-metadata(2).json": "S3",
    }

    primary, supplemental = match_json_for_media("IMG_1234.JPG", lookup)
    ok1 = set(primary) == {"P1"} and set(supplemental) == {"S1", "S2"}

    primary2, supplemental2 = match_json_for_media("IMG_1234(2).JPG", lookup)
    ok2 = set(primary2) == {"P2"} and set(supplemental2) == {"S3"}

    return report("Match JSON for media", ok1 and ok2)


def main() -> int:
    print()
    print("=" * 70)
    print(" JSON MATCHING RULES TESTS ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_candidates_unsuffixed()
    passed &= test_candidates_suffixed()
    passed &= test_candidates_ignore_year_suffix()
    passed &= test_match_json_for_media()

    print()
    if passed:
        print("[SUCCESS] JSON matching rules tests passed.")
        return 0

    print("[ERROR] JSON matching rules tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
