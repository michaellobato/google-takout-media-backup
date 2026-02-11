#!/usr/bin/env python3
"""
Workflow logic tests that exercise the Pass 2 pipeline via main()
inside a temporary sandbox (no real data touched).
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from test_helpers import load_process_media, assert_safe_paths, temp_dir
from process_media_exif import get_exif_datetime


def report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"{status}: {label} - {detail}")
    else:
        print(f"{status}: {label}")
    return passed


def find_exiftool_dir() -> Path | None:
    candidates = [
        Path("P:/MediaBackupProject/tools/exiftool-13.48_64"),
        Path(__file__).resolve().parent.parent / "tools" / "exiftool-13.48_64",
    ]
    for c in candidates:
        exe = c / "exiftool.exe"
        if exe.exists():
            return c
    return None


def ensure_tools(temp_root: Path, exiftool_src: Path) -> None:
    dest = temp_root / "tools" / "exiftool-13.48_64"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(exiftool_src, dest)


def write_tiny_jpeg(path: Path) -> None:
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


def exiftool_write(exiftool_exe: Path, args: list[str]) -> subprocess.CompletedProcess:
    cmd = [os.fspath(exiftool_exe)] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def to_ts(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def reset_sandbox(root: Path) -> None:
    for name in ["takeout-archives", "json-repository", "workbench", "output"]:
        shutil.rmtree(root / name, ignore_errors=True)
    for log in root.glob("*.log"):
        try:
            log.unlink()
        except Exception:
            pass
    os.makedirs(root / "takeout-archives", exist_ok=True)
    os.makedirs(root / "json-repository", exist_ok=True)
    os.makedirs(root / "workbench", exist_ok=True)
    os.makedirs(root / "output", exist_ok=True)


def create_zip_with_media(zip_path: Path, media_path: Path, arcname: str | None = None) -> None:
    if arcname is None:
        arcname = media_path.name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(media_path, arcname=arcname)


def run_main(
    module,
    temp_root: Path,
    *,
    is_live_run: bool = True,
    batch_size: int | None = 1,
    archive_name: str | None = None,
    force_extract: bool = True,
    clean_workbench: bool = True,
    show_status: bool = False,
):
    module.PROJECT_ROOT = temp_root
    module.FINAL_LIBRARY_DIR = temp_root / "output"
    module.main(
        is_live_run=is_live_run,
        batch_size=batch_size,
        archive_name=archive_name,
        force_extract=force_extract,
        clean_workbench=clean_workbench,
        show_status=show_status,
    )


def read_log_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def expect_dest_file(output_root: Path, dt: datetime, basename: str, ext: str = ".jpg") -> Path:
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    dest_dir = output_root / year / month / basename
    for candidate in [dest_dir / f"{basename}{ext}", dest_dir / f"{basename}{ext.lower()}"]:
        if candidate.exists():
            return candidate
    return dest_dir / f"{basename}{ext}"


def test_embedded_wins(module, temp_root: Path, exiftool_exe: Path) -> bool:
    reset_sandbox(temp_root)

    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    embedded_dt = datetime(2020, 5, 10, 17, 39, 0)
    exiftool_write(
        exiftool_exe,
        [
            "-overwrite_original",
            f"-DateTimeOriginal={embedded_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            f"-CreateDate={embedded_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            f"-FileModifyDate={embedded_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            os.fspath(media),
        ],
    )

    zip_path = temp_root / "takeout-archives" / "a.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_0001.jpg")

    json_path = temp_root / "json-repository" / "IMG_0001.jpg.json"
    json_path.write_text(
        json.dumps({
            "title": "IMG_0001.jpg",
            "photoTakenTime": {"timestamp": str(to_ts(datetime(2021, 6, 1)))},
        }),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", embedded_dt, "IMG_0001")
    read_dt = get_exif_datetime(os.fspath(dest), cfg=module.CONFIG)
    return report("Embedded wins over JSON", read_dt == embedded_dt, f"dest={dest}")


def test_primary_json_fallback(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "b.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_0002.jpg")

    json_dt = datetime(2021, 6, 1, 0, 0, 0)
    json_path = temp_root / "json-repository" / "IMG_0002.jpg.json"
    json_path.write_text(
        json.dumps({"title": "IMG_0002.jpg", "photoTakenTime": {"timestamp": str(to_ts(json_dt))}}),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", json_dt, "IMG_0002")
    read_dt = get_exif_datetime(os.fspath(dest), cfg=module.CONFIG)
    return report("Primary JSON fallback", read_dt == json_dt, f"dest={dest}")


def test_supplemental_fallback(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "c.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_0003.jpg")

    json_path = temp_root / "json-repository" / "IMG_0003.jpg.json"
    json_path.write_text(json.dumps({"title": "IMG_0003.jpg"}), encoding="utf-8")

    supp_dt = datetime(2019, 2, 3, 4, 5, 6)
    supp_path = temp_root / "json-repository" / "IMG_0003.jpg.supplemental-metadata.json"
    supp_path.write_text(
        json.dumps({"photoTakenTime": {"timestamp": str(to_ts(supp_dt))}}),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", supp_dt, "IMG_0003")
    read_dt = get_exif_datetime(os.fspath(dest), cfg=module.CONFIG)
    return report("Supplemental fallback", read_dt == supp_dt, f"dest={dest}")


def test_no_metadata_unmatched(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "d.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_0004.jpg")

    json_path = temp_root / "json-repository" / "IMG_0004.jpg.json"
    json_path.write_text(json.dumps({"title": "IMG_0004.jpg"}), encoding="utf-8")

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    expected = temp_root / "output" / "__NEEDS_REVIEW__" / "unmatched-media" / "IMG_0004.jpg"
    return report("No metadata -> needs review", expected.exists(), f"dest={expected}")


def test_exif_fallback_no_json(module, temp_root: Path, exiftool_exe: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    exif_dt = datetime(2018, 1, 2, 3, 4, 5)
    exiftool_write(
        exiftool_exe,
        [
            "-overwrite_original",
            f"-DateTimeOriginal={exif_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            f"-CreateDate={exif_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            f"-FileModifyDate={exif_dt.strftime('%Y:%m:%d %H:%M:%S')}",
            os.fspath(media),
        ],
    )

    zip_path = temp_root / "takeout-archives" / "e.zip"
    create_zip_with_media(zip_path, media, arcname="ORPHAN.jpg")

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", exif_dt, "ORPHAN")
    return report("EXIF fallback (no JSON)", dest.exists(), f"dest={dest}")


def test_supplemental_fallback_no_primary(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "f.zip"
    create_zip_with_media(zip_path, media, arcname="ORPHAN2.jpg")

    supp_dt = datetime(2017, 3, 4, 5, 6, 7)
    supp_path = temp_root / "json-repository" / "ORPHAN2.jpg.supplemental-metadata.json"
    supp_path.write_text(
        json.dumps({"photoTakenTime": {"timestamp": str(to_ts(supp_dt))}}),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", supp_dt, "ORPHAN2")
    read_dt = get_exif_datetime(os.fspath(dest), cfg=module.CONFIG)
    return report("Supplemental fallback (no primary)", read_dt == supp_dt, f"dest={dest}")


def test_path_too_long(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "g.zip"
    create_zip_with_media(zip_path, media, arcname="LONGNAME.jpg")

    json_dt = datetime(2020, 1, 1, 0, 0, 0)
    json_path = temp_root / "json-repository" / "LONGNAME.jpg.json"
    json_path.write_text(
        json.dumps({"title": "LONGNAME.jpg", "photoTakenTime": {"timestamp": str(to_ts(json_dt))}}),
        encoding="utf-8",
    )

    original_max = module.MAX_PATH_LENGTH
    module.MAX_PATH_LENGTH = 10
    try:
        module.configure_paths(temp_root, temp_root / "output")
        assert_safe_paths(module, temp_root)
        run_main(module, temp_root)
    finally:
        module.MAX_PATH_LENGTH = original_max

    expected = Path(module.PATH_TOO_LONG_DIR) / "LONGNAME.jpg"
    return report("Path too long handling", expected.exists(), f"dest={expected}")


def test_suffix_matching_workflow(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "i.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_0006(2).jpg")

    json_dt = datetime(2021, 8, 9, 10, 11, 12)
    json_path = temp_root / "json-repository" / "IMG_0006.jpg(2).json"
    json_path.write_text(
        json.dumps({"title": "IMG_0006.jpg", "photoTakenTime": {"timestamp": str(to_ts(json_dt))}}),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root)

    dest = expect_dest_file(temp_root / "output", json_dt, "IMG_0006(2)")
    return report("Suffix matching (workflow)", dest.exists(), f"dest={dest}")


def test_dry_run_no_destination_writes(module, temp_root: Path) -> bool:
    reset_sandbox(temp_root)
    media = temp_root / "src.jpg"
    write_tiny_jpeg(media)

    zip_path = temp_root / "takeout-archives" / "dryrun.zip"
    create_zip_with_media(zip_path, media, arcname="IMG_9999.jpg")

    json_dt = datetime(2021, 1, 2, 3, 4, 5)
    json_path = temp_root / "json-repository" / "IMG_9999.jpg.json"
    json_path.write_text(
        json.dumps({"title": "IMG_9999.jpg", "photoTakenTime": {"timestamp": str(to_ts(json_dt))}}),
        encoding="utf-8",
    )

    module.configure_paths(temp_root, temp_root / "output")
    assert_safe_paths(module, temp_root)
    run_main(module, temp_root, is_live_run=False)

    output_root = temp_root / "output"
    output_files = [p for p in output_root.rglob("*") if p.is_file()]
    if output_files:
        return report("Dry run avoids destination writes", False, f"files={output_files}")

    if Path(module.PROCESSED_LOG_FILE).exists():
        return report("Dry run avoids destination writes", False, "processed log should not be created")

    return report("Dry run avoids destination writes", True)


def main() -> int:
    print()
    print("=" * 70)
    print(" WORKFLOW LOGIC TESTS ".center(70))
    print("=" * 70)
    print()

    exiftool_dir = find_exiftool_dir()
    if not exiftool_dir:
        print("[SKIP] ExifTool not found. Skipping workflow tests.")
        return 0

    with temp_dir() as root:
        ensure_tools(root, exiftool_dir)
        module = load_process_media()

        # After configure_paths(), ExifTool should resolve under temp root tools
        module.configure_paths(root, root / "output")
        assert_safe_paths(module, root)

        exiftool_exe = root / "tools" / "exiftool-13.48_64" / "exiftool.exe"
        if not exiftool_exe.exists():
            print("[SKIP] ExifTool not found in temp tools. Skipping workflow tests.")
            return 0

        passed = True
        passed &= test_embedded_wins(module, root, exiftool_exe)
        passed &= test_primary_json_fallback(module, root)
        passed &= test_supplemental_fallback(module, root)
        passed &= test_no_metadata_unmatched(module, root)
        passed &= test_exif_fallback_no_json(module, root, exiftool_exe)
        passed &= test_supplemental_fallback_no_primary(module, root)
        passed &= test_path_too_long(module, root)
        passed &= test_suffix_matching_workflow(module, root)
        passed &= test_dry_run_no_destination_writes(module, root)

    print()
    if passed:
        print("[SUCCESS] Workflow logic tests passed.")
        return 0

    print("[ERROR] Workflow logic tests failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
