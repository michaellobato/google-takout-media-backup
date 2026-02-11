#!/usr/bin/env python3
"""
Configuration objects for Pass 2 processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessMediaConfig:
    project_root: Path
    workbench_dir: Path
    extract_target_dir: Path
    json_repository_dir: Path
    takeout_archives_dir: Path
    tools_dir: Path
    exiftool_dir_base: Path
    exiftool_dir_extra_files: Path
    exiftool_exe: Path
    exiftool_perl: Path
    exiftool_script: Path
    final_library_dir: Path
    needs_review_dir: Path
    orphan_media_dir: Path
    path_too_long_dir: Path
    processed_log_file: Path
    processed_work_items_log_file: Path
    fallback_used_log_file: Path
    processed_archives_log_file: Path
    processed_standalone_log_file: Path
    path_too_long_log_file: Path
    exiftool_failures_log_file: Path
    corrupt_archives_log_file: Path


def build_config(project_root: Path, final_library_dir: Path | None = None) -> ProcessMediaConfig:
    project_root = Path(project_root)

    workbench_dir = project_root / "workbench"
    extract_target_dir = workbench_dir / "Takeout"
    json_repository_dir = project_root / "json-repository"
    takeout_archives_dir = project_root / "takeout-archives"
    tools_dir = project_root / "tools"
    exiftool_dir_base = tools_dir / "exiftool-13.48_64"
    exiftool_dir_extra_files = exiftool_dir_base / "exiftool_files"

    exiftool_exe = exiftool_dir_base / "exiftool.exe"
    exiftool_perl = exiftool_dir_extra_files / "perl.exe"
    exiftool_script = exiftool_dir_extra_files / "exiftool.pl"

    if final_library_dir is None:
        final_library_dir = Path("Z:/Family Pictures and Videos")
    final_library_dir = Path(final_library_dir)
    needs_review_dir = final_library_dir / "__NEEDS_REVIEW__"
    orphan_media_dir = needs_review_dir / "unmatched-media"
    path_too_long_dir = needs_review_dir / "path-too-long"

    processed_log_file = workbench_dir / ".processed_files.log"
    processed_work_items_log_file = project_root / ".processed_work_items_pass2.log"
    fallback_used_log_file = project_root / ".fallback_metadata_used_pass2.log"
    processed_archives_log_file = project_root / ".processed_archives_pass2.log"
    processed_standalone_log_file = project_root / ".processed_standalone_pass2.log"
    path_too_long_log_file = project_root / ".path_too_long_pass2.log"
    exiftool_failures_log_file = project_root / ".exiftool_failures_pass2.log"
    corrupt_archives_log_file = project_root / ".corrupt_archives.log"

    return ProcessMediaConfig(
        project_root=project_root,
        workbench_dir=workbench_dir,
        extract_target_dir=extract_target_dir,
        json_repository_dir=json_repository_dir,
        takeout_archives_dir=takeout_archives_dir,
        tools_dir=tools_dir,
        exiftool_dir_base=exiftool_dir_base,
        exiftool_dir_extra_files=exiftool_dir_extra_files,
        exiftool_exe=exiftool_exe,
        exiftool_perl=exiftool_perl,
        exiftool_script=exiftool_script,
        final_library_dir=final_library_dir,
        needs_review_dir=needs_review_dir,
        orphan_media_dir=orphan_media_dir,
        path_too_long_dir=path_too_long_dir,
        processed_log_file=processed_log_file,
        processed_work_items_log_file=processed_work_items_log_file,
        fallback_used_log_file=fallback_used_log_file,
        processed_archives_log_file=processed_archives_log_file,
        processed_standalone_log_file=processed_standalone_log_file,
        path_too_long_log_file=path_too_long_log_file,
        exiftool_failures_log_file=exiftool_failures_log_file,
        corrupt_archives_log_file=corrupt_archives_log_file,
    )
