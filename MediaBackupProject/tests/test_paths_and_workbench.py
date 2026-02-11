#!/usr/bin/env python3
"""
Tests for path helpers and workbench checks.
"""

from __future__ import annotations

import os
from dataclasses import replace

from test_helpers import temp_dir
from process_media_config import build_config
from process_media_paths import is_under_dir, resolve_archive_path, workbench_has_files


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def test_is_under_dir() -> bool:
    with temp_dir() as d:
        child = d / "child.txt"
        child.write_text("x", encoding="utf-8")
        ok1 = is_under_dir(os.fspath(child), os.fspath(d))
        ok2 = not is_under_dir(os.fspath(d), os.fspath(d / "nope"))
        return report("is_under_dir", ok1 and ok2)


def test_resolve_archive_path() -> bool:
    with temp_dir() as d:
        archive = d / "test.zip"
        archive.write_text("x", encoding="utf-8")
        cfg = replace(build_config(d, d / "output"), takeout_archives_dir=d)
        resolved = resolve_archive_path("test.zip", cfg=cfg)
        ok1 = os.path.normcase(resolved) == os.path.normcase(os.fspath(archive))
        ok2 = resolve_archive_path(os.fspath(archive), cfg=cfg) == os.fspath(archive)
        ok3 = resolve_archive_path("missing.zip", cfg=cfg) is None
        return report("resolve_archive_path", ok1 and ok2 and ok3)


def test_workbench_has_files() -> bool:
    with temp_dir() as d:
        cfg = replace(build_config(d, d / "output"), extract_target_dir=d)
        ok1 = workbench_has_files(cfg=cfg) is False
        (d / "file.txt").write_text("x", encoding="utf-8")
        ok2 = workbench_has_files(cfg=cfg) is True
        return report("workbench_has_files", ok1 and ok2)


def main() -> int:
    print()
    print("=" * 70)
    print(" PATHS + WORKBENCH TESTS ".center(70))
    print("=" * 70)
    print()

    passed = True
    passed &= test_is_under_dir()
    passed &= test_resolve_archive_path()
    passed &= test_workbench_has_files()

    print()
    if passed:
        print("[SUCCESS] Paths and workbench tests passed.")
        return 0

    print("[ERROR] Paths and workbench tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
