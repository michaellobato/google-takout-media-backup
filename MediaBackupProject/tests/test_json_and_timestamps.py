#!/usr/bin/env python3
"""
Tests for JSON parsing and timestamp extraction logic.
"""

from __future__ import annotations

import json
import os
import sys

from test_helpers import temp_dir
from process_media_json import get_true_filename_from_json, get_timestamp_from_json


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_get_true_filename() -> bool:
    all_passed = True
    with temp_dir() as d:
        good = d / "good.json"
        missing = d / "missing.json"
        bad = d / "bad.json"

        good.write_text(json.dumps({"title": "IMG_0001.JPG"}), encoding="utf-8")
        missing.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
        bad.write_text("{not valid json", encoding="utf-8")

        result = get_true_filename_from_json(os.fspath(good))
        all_passed &= report("get_true_filename_from_json (valid)", result == "IMG_0001.JPG")

        result = get_true_filename_from_json(os.fspath(missing))
        all_passed &= report("get_true_filename_from_json (missing title)", result is None)

        result = get_true_filename_from_json(os.fspath(bad))
        all_passed &= report("get_true_filename_from_json (invalid json)", result is None)

    return all_passed


def test_get_timestamp_from_json() -> bool:
    all_passed = True
    with temp_dir() as d:
        photo_taken = d / "photo_taken.json"
        creation_only = d / "creation_only.json"
        invalid = d / "invalid.json"
        missing = d / "missing.json"

        photo_taken.write_text(
            json.dumps({"photoTakenTime": {"timestamp": "1700000000"}}),
            encoding="utf-8",
        )
        creation_only.write_text(
            json.dumps({"creationTime": {"timestamp": "1600000000"}}),
            encoding="utf-8",
        )
        invalid.write_text(
            json.dumps({"photoTakenTime": {"timestamp": "not-a-number"}}),
            encoding="utf-8",
        )
        missing.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

        result = get_timestamp_from_json(os.fspath(photo_taken))
        all_passed &= report("get_timestamp_from_json (photoTakenTime)", result == 1700000000)

        result = get_timestamp_from_json(os.fspath(creation_only))
        all_passed &= report("get_timestamp_from_json (creationTime fallback)", result == 1600000000)

        result = get_timestamp_from_json(os.fspath(invalid))
        all_passed &= report("get_timestamp_from_json (invalid timestamp)", result is None)

        result = get_timestamp_from_json(os.fspath(missing))
        all_passed &= report("get_timestamp_from_json (missing fields)", result is None)

    return all_passed


def main() -> int:
    print()
    print("=" * 70)
    print(" JSON + TIMESTAMP TESTS ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_get_true_filename()
    passed &= test_get_timestamp_from_json()

    print()
    if passed:
        print("[SUCCESS] JSON and timestamp tests passed.")
        return 0

    print("[ERROR] JSON and timestamp tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
