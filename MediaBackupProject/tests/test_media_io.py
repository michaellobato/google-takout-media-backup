#!/usr/bin/env python3
"""
Integration-lite tests that exercise real file IO against 2-process-media.py.

Focus areas:
- Supplemental metadata matching (with and without suffixes)
- Media extension normalization (ExifTool-driven)
- Embedded GPS detection (valid vs 0,0)
- Path length validation edge cases

These tests use temporary directories and tiny sample media files.
They do NOT touch your real Takeout archives or output library.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from process_media_config import build_config
from process_media_exif import (
    normalize_media_extension,
    get_embedded_gps,
    get_exif_datetime,
)
from process_media_json_lookup import (
    build_supplemental_index,
    find_all_supplemental_for_basename,
)
from process_media_paths import validate_path_length

SCRIPT_DIR = Path(__file__).resolve().parent


def find_exiftool() -> Path | None:
    candidates = [
        SCRIPT_DIR.parent / "tools" / "exiftool-13.48_64" / "exiftool.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def with_exiftool(cfg, exiftool: Path | None):
    if not exiftool:
        return cfg
    extra = exiftool.parent / "exiftool_files"
    return replace(
        cfg,
        exiftool_exe=exiftool,
        exiftool_dir_base=exiftool.parent,
        exiftool_dir_extra_files=extra,
        exiftool_perl=extra / "perl.exe",
        exiftool_script=extra / "exiftool.pl",
    )


def write_tiny_jpeg(path: Path) -> None:
    # 1x1 white JPEG
    data = (
        b"/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhISEhIVFhUVFRUVFRUV"
        b"FRUVFRUVFRUWFhUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisB"
        b"CgoKDg0OGxAQGy0lICYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0t"
        b"LS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAQMBEQACEQEDEQH/xAAbAAACAgMB"
        b"AAAAAAAAAAAAAAAFBgMEAAIBB//EAD0QAAIBAwMCBAQEBgEFAAAAAAABAgMR"
        b"BBIhMQVBUQYiYXGBEzKRobHwFBUjQrHhM0JSYnL/xAAYAQADAQEAAAAAAAAA"
        b"AAAAAAAAAQIDBP/EAB0RAQADAQEBAQAAAAAAAAAAAAABAhEDIRIxQfD/2gAM"
        b"AwEAAhEDEQA/AKwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        b"AAAAAAAAAAAAAAAAAAAAAP/2Q=="
    )
    path.write_bytes(base64.b64decode(data))


def exiftool_write(exiftool: Path, args: list[str]) -> subprocess.CompletedProcess:
    cmd = [os.fspath(exiftool)] + args
    return subprocess.run(cmd, capture_output=True, text=True)


FAILURE_COUNT = 0


def record_result(label: str, status: str, detail: str | None = None):
    global FAILURE_COUNT
    prefix = {
        "pass": "[PASS]",
        "fail": "[FAIL]",
        "warn": "[WARN]",
        "skip": "[SKIP]",
    }[status]
    if status == "fail":
        FAILURE_COUNT += 1
    if detail:
        print(f"{prefix} {label} - {detail}")
    else:
        print(f"{prefix} {label}")


def test_supplemental_matching() -> str:
    temp_dir = Path(tempfile.mkdtemp())
    try:
        unsuffixed = temp_dir / "IMG_0001.JPG.supplemental-metadata.json"
        suffixed = temp_dir / "IMG_0001.JPG.supplemental-metadata(1).json"
        unsuffixed.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
        suffixed.write_text(json.dumps({"foo": "baz"}), encoding="utf-8")

        cfg = replace(build_config(temp_dir, temp_dir / "output"), json_repository_dir=temp_dir)
        index = build_supplemental_index(cfg=cfg)

        # Happy path: unsuffixed should be indexed
        base_key = "img_0001.jpg"
        if base_key not in index:
            record_result("Supplemental index (unsuffixed)", "fail", "missing base key")
            return "fail"
        record_result("Supplemental index (unsuffixed)", "pass")

        # Edge case: suffix matching works when index contains suffixed entries
        manual_index = {base_key: [os.fspath(unsuffixed), os.fspath(suffixed)]}
        match = find_all_supplemental_for_basename("IMG_0001(1).JPG", manual_index)
        if match and Path(match[0]).name == suffixed.name:
            record_result("Supplemental suffix matching", "pass")
        else:
            record_result("Supplemental suffix matching", "fail", "suffix match failed")
            return "fail"

        # Index should include suffixed supplemental files
        if any(Path(p).name == suffixed.name for p in index.get(base_key, [])):
            record_result("Supplemental index includes suffixed files", "pass")
        else:
            record_result(
                "Supplemental index includes suffixed files",
                "fail",
                "missing suffixed supplemental file in index",
            )
            return "fail"

        return "pass"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_supplemental_suffix_variants() -> str:
    temp_dir = Path(tempfile.mkdtemp())
    try:
        expected = [
            "IMG_1234.JPG.supplemental-metadata(2).json",
            "IMG_1234(2).JPG.supplemental-metadata.json",
            "IMG_1234(2).JPG.supplemental-metadata(2).json",
            "IMG_1234.JPG(2).supplemental-metadata.json",
            "IMG_1234.JPG(2).supplemental-metadata(2).json",
            "IMG_1234(2).JPG.sup.json",
            "IMG_1234(2).JPG.sup(2).json",
            "IMG_1234.JPG.sup(2).json",
            "IMG_1234.JPG(2).sup.json",
            "IMG_1234.JPG(2).sup(2).json",
        ]
        non_matching = [
            "IMG_1234.JPG.supplemental-metadata.json",
            "IMG_1234.JPG.sup.json",
        ]

        for name in expected + non_matching:
            (temp_dir / name).write_text("{}", encoding="utf-8")

        cfg = replace(build_config(temp_dir, temp_dir / "output"), json_repository_dir=temp_dir)
        index = build_supplemental_index(cfg=cfg)
        matches = find_all_supplemental_for_basename("IMG_1234(2).JPG", index)
        matched_names = {Path(p).name for p in matches}

        expected_set = set(expected)
        missing = sorted(expected_set - matched_names)
        unexpected = sorted(set(non_matching) & matched_names)

        if missing:
            record_result("Supplemental suffix variants", "fail", f"missing: {missing}")
            return "fail"
        if unexpected:
            record_result("Supplemental suffix variants", "fail", f"unexpected: {unexpected}")
            return "fail"

        record_result("Supplemental suffix variants", "pass")
        return "pass"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_normalize_extension(exiftool: Path | None) -> str:
    if not exiftool:
        record_result("Normalize media extension", "skip", "ExifTool not found")
        return "skip"

    temp_dir = Path(tempfile.mkdtemp())
    try:
        wrong_path = temp_dir / "tiny.png"
        write_tiny_jpeg(wrong_path)

        cfg = with_exiftool(build_config(temp_dir, temp_dir / "output"), exiftool)
        new_path = Path(normalize_media_extension(wrong_path, cfg=cfg))
        if new_path.suffix.lower() == ".jpg" and new_path.exists() and not wrong_path.exists():
            record_result("Normalize media extension", "pass")
            return "pass"

        record_result("Normalize media extension", "fail", f"returned {new_path}")
        return "fail"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_embedded_gps(exiftool: Path | None) -> str:
    if not exiftool:
        record_result("Embedded GPS detection", "skip", "ExifTool not found")
        return "skip"

    temp_dir = Path(tempfile.mkdtemp())
    try:
        media_path = temp_dir / "gps.jpg"
        write_tiny_jpeg(media_path)

        # Write valid GPS
        cp = exiftool_write(exiftool, [
            "-overwrite_original",
            "-GPSLatitude=45.5231",
            "-GPSLongitude=-122.6765",
            os.fspath(media_path),
        ])
        if cp.returncode != 0:
            record_result("Embedded GPS detection", "fail", cp.stderr.strip())
            return "fail"

        cfg = with_exiftool(build_config(temp_dir, temp_dir / "output"), exiftool)
        has_gps, gps_valid = get_embedded_gps(os.fspath(media_path), cfg=cfg)
        if has_gps and gps_valid:
            record_result("Embedded GPS detection (valid)", "pass")
        else:
            record_result("Embedded GPS detection (valid)", "fail", f"{has_gps}, {gps_valid}")
            return "fail"

        # Write Null Island (0,0) - should be invalid
        exiftool_write(exiftool, [
            "-overwrite_original",
            "-GPSLatitude=0",
            "-GPSLongitude=0",
            os.fspath(media_path),
        ])
        has_gps, gps_valid = get_embedded_gps(os.fspath(media_path), cfg=cfg)
        if has_gps and not gps_valid:
            record_result("Embedded GPS detection (0,0)", "pass")
        else:
            record_result(
                "Embedded GPS detection (0,0)",
                "fail",
                f"returned {has_gps}, {gps_valid}",
            )
            return "fail"

        # Near-zero should also be treated as invalid (within epsilon)
        exiftool_write(exiftool, [
            "-overwrite_original",
            "-GPSLatitude=0.00005",
            "-GPSLongitude=0.00005",
            os.fspath(media_path),
        ])
        has_gps, gps_valid = get_embedded_gps(os.fspath(media_path), cfg=cfg)
        if has_gps and not gps_valid:
            record_result("Embedded GPS detection (near-zero)", "pass")
        else:
            record_result(
                "Embedded GPS detection (near-zero)",
                "fail",
                f"returned {has_gps}, {gps_valid}",
            )
            return "fail"

        return "pass"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_embedded_gps_string_output() -> str:
    class DummyResult:
        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run_exiftool(args, **kwargs):
        # Simulate non-numeric DMS output from ExifTool
        return DummyResult("0 deg 0' 0.00\" N\n0 deg 0' 0.00\" E\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        cfg = build_config(temp_root, temp_root / "output")
        has_gps, gps_valid = get_embedded_gps("dummy.jpg", cfg=cfg, run_exiftool_fn=fake_run_exiftool)
        if has_gps and not gps_valid:
            record_result("Embedded GPS detection (string output)", "pass")
            return "pass"
        record_result("Embedded GPS detection (string output)", "fail", f"{has_gps}, {gps_valid}")
        return "fail"


def test_exif_datetime_quicktime_tags() -> str:
    class DummyResult:
        def __init__(self, stdout: str, returncode: int = 1):
            self.stdout = stdout
            self.returncode = returncode

    captured_args = {}

    def fake_run_exiftool(args, **kwargs):
        captured_args["args"] = args
        return DummyResult("2022:03:14 03:16:16\n", returncode=1)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        cfg = build_config(temp_root, temp_root / "output")
        dt = get_exif_datetime("dummy.mp4", cfg=cfg, run_exiftool_fn=fake_run_exiftool)

        if dt is None:
            record_result("Embedded datetime (QuickTime tags)", "fail", "no datetime parsed")
            return "fail"

        args = " ".join(captured_args.get("args", []))
        required_tags = ["-MediaCreateDate", "-TrackCreateDate", "-QuickTime:CreateDate"]
        if not all(tag in args for tag in required_tags):
            record_result("Embedded datetime (QuickTime tags)", "fail", f"missing tags in args: {args}")
            return "fail"

        record_result("Embedded datetime (QuickTime tags)", "pass")
        return "pass"


def test_exif_timestamp_roundtrip(exiftool: Path | None) -> str:
    if not exiftool:
        record_result("Embedded timestamp read/write", "skip", "ExifTool not found")
        return "skip"

    temp_dir = Path(tempfile.mkdtemp())
    try:
        media_path = temp_dir / "time.jpg"
        write_tiny_jpeg(media_path)

        exif_dt = "2020:05:10 17:39:00"
        cp = exiftool_write(exiftool, [
            "-overwrite_original",
            f"-DateTimeOriginal={exif_dt}",
            f"-CreateDate={exif_dt}",
            f"-FileModifyDate={exif_dt}",
            os.fspath(media_path),
        ])
        if cp.returncode != 0:
            record_result("Embedded timestamp read/write", "fail", cp.stderr.strip())
            return "fail"

        cfg = with_exiftool(build_config(temp_dir, temp_dir / "output"), exiftool)
        read_dt = get_exif_datetime(os.fspath(media_path), cfg=cfg)
        expected = datetime.strptime(exif_dt, "%Y:%m:%d %H:%M:%S")
        if read_dt == expected:
            record_result("Embedded timestamp read/write", "pass")
            return "pass"

        record_result("Embedded timestamp read/write", "fail", f"read={read_dt}")
        return "fail"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_validate_path_length() -> str:
    ok, length = validate_path_length("123456789", 10)
    if not ok or length != 9:
        record_result("Path length validation (under)", "fail")
        return "fail"
    record_result("Path length validation (under)", "pass")
    ok, length = validate_path_length("1234567890", 10)
    if ok or length != 10:
        record_result("Path length validation (limit)", "fail")
        return "fail"
    record_result("Path length validation (limit)", "pass")
    return "pass"


def main() -> int:
    print()
    print("=" * 70)
    print(" MEDIA IO TESTS ".center(70))
    print("=" * 70)
    print()

    exiftool = find_exiftool()

    results = []
    results.append(test_supplemental_matching())
    results.append(test_supplemental_suffix_variants())
    results.append(test_normalize_extension(exiftool))
    results.append(test_embedded_gps(exiftool))
    results.append(test_embedded_gps_string_output())
    results.append(test_exif_datetime_quicktime_tags())
    results.append(test_exif_timestamp_roundtrip(exiftool))
    results.append(test_validate_path_length())

    failures = max(FAILURE_COUNT, results.count("fail"))
    if failures:
        print()
        print(f"[ERROR] {failures} test(s) failed.")
        return 1

    print()
    print("[SUCCESS] Media IO tests completed (warnings possible).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
