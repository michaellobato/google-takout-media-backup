#!/usr/bin/env python3
"""
Tests for media indexing and lookup helpers.
"""

from __future__ import annotations

import os

from test_helpers import temp_dir
from process_media_indexing import build_media_index, find_media_file_from_index


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_build_media_index() -> bool:
    with temp_dir() as d:
        (d / "A.JPG").write_text("x", encoding="utf-8")
        (d / "b.json").write_text("{}", encoding="utf-8")
        sub = d / "sub"
        sub.mkdir()
        (sub / "C.MOV").write_text("x", encoding="utf-8")

        index = build_media_index([os.fspath(d)])

        ok = "a.jpg" in index and "c.mov" in index and "b.json" not in index
        return report("build_media_index (skips json, lowercases)", ok)


def test_build_media_index_allowed_paths() -> bool:
    with temp_dir() as d:
        keep = d / "keep.jpg"
        skip = d / "skip.jpg"
        keep.write_text("x", encoding="utf-8")
        skip.write_text("x", encoding="utf-8")

        index = build_media_index([os.fspath(d)], allowed_paths={os.fspath(keep)})
        ok = list(index.keys()) == ["keep.jpg"]
        return report("build_media_index (allowed_paths)", ok, f"keys={list(index.keys())}")


def test_find_media_file_from_index() -> bool:
    with temp_dir() as d:
        p1 = d / "dup.jpg"
        p2 = d / "dup2.jpg"
        p1.write_text("x", encoding="utf-8")
        p2.write_text("x", encoding="utf-8")

        index = {"dup.jpg": [os.fspath(p1), os.fspath(p2)]}
        result = find_media_file_from_index(["dup.jpg"], {os.fspath(p1)}, index)
        ok = result == os.fspath(p2)
        return report("find_media_file_from_index (skips processed)", ok, f"result={result}")


def main() -> int:
    print()
    print("=" * 70)
    print(" INDEXING + LOOKUP TESTS ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_build_media_index()
    passed &= test_build_media_index_allowed_paths()
    passed &= test_find_media_file_from_index()

    print()
    if passed:
        print("[SUCCESS] Indexing and lookup tests passed.")
        return 0

    print("[ERROR] Indexing and lookup tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
