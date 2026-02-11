#!/usr/bin/env python3
"""
Simple test runner that executes all project test scripts.

Usage:
    python tests/test_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TEST_SCRIPTS = [
    "test_gps_validation.py",
    "test_integration.py",
    "test_suffix_logic.py",
    "test_string_gps.py",
    "test_media_io.py",
    "test_json_matching_rules.py",
    "test_json_and_timestamps.py",
    "test_filename_logic.py",
    "test_indexing_and_lookup.py",
    "test_paths_and_workbench.py",
    "test_workflow_logic.py",
]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    failures = 0

    print("=" * 70)
    print(" TEST ALL ".center(70))
    print("=" * 70)
    print()

    for name in TEST_SCRIPTS:
        path = script_dir / name
        if not path.exists():
            print(f"[FAIL] Missing test file: {path}")
            failures += 1
            continue

        print("-" * 70)
        print(f"Running: {name}")
        print("-" * 70)

        cp = subprocess.run([sys.executable, str(path)], cwd=str(script_dir))
        if cp.returncode != 0:
            print(f"[FAIL] {name} exited with code {cp.returncode}")
            failures += 1
        else:
            print(f"[PASS] {name}")
        print()

    print("=" * 70)
    print(" TEST SUMMARY ".center(70))
    print("=" * 70)
    print()

    if failures:
        print(f"[ERROR] {failures} test file(s) failed.")
        return 1

    print("[SUCCESS] All test files passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
