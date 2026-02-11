#!/usr/bin/env python3
"""
Path and workbench helpers for Pass 2 processing.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile

from process_media_config import ProcessMediaConfig


def is_under_dir(path, root_dir):
    try:
        p = os.path.abspath(os.fspath(path))
        r = os.path.abspath(os.fspath(root_dir))
        return os.path.commonpath([p, r]) == r
    except ValueError:
        return False


def workbench_has_files(cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for workbench_has_files")
    if not os.path.isdir(cfg.extract_target_dir):
        return False
    for _, _, files in os.walk(cfg.extract_target_dir):
        if files:
            return True
    return False


def resolve_archive_path(archive_name, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for resolve_archive_path")
    if not archive_name:
        return None
    if os.path.isabs(archive_name) and os.path.exists(archive_name):
        return archive_name
    candidate = os.path.join(cfg.takeout_archives_dir, archive_name)
    if os.path.exists(candidate):
        return candidate
    return None


def extract_archive_to_workbench(archive_path, force_extract, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for extract_archive_to_workbench")
    if not archive_path:
        sys.exit("FATAL: No archive specified for extraction.")
    if not archive_path.lower().endswith(".zip"):
        sys.exit(f"FATAL: Archive must be a .zip file: '{archive_path}'")
    if force_extract:
        shutil.rmtree(cfg.extract_target_dir, ignore_errors=True)
        os.makedirs(cfg.extract_target_dir, exist_ok=True)
    elif workbench_has_files(cfg):
        sys.exit("FATAL: Workbench is not empty. Use --force-extract to overwrite.")
    else:
        os.makedirs(cfg.extract_target_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'r') as archive:
        archive.extractall(cfg.extract_target_dir)
    print(f"Extracted archive to workbench: '{archive_path}'")


def validate_path_length(path, max_length: int):
    """Check if path exceeds Windows 11 MAX_PATH limit (260 chars).
    Returns (is_valid, path_length)"""
    path_str = os.fspath(path)
    path_length = len(path_str)
    return path_length < max_length, path_length
