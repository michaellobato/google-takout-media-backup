#!/usr/bin/env python3
"""
Logging and state tracking helpers for Pass 2 processing.
"""

from __future__ import annotations

import os

from process_media_config import ProcessMediaConfig


def get_processed_files_log(cfg: ProcessMediaConfig | None = None):
    """Reads the progress log and returns a set of already processed file paths."""
    if cfg is None:
        raise ValueError("cfg is required for get_processed_files_log")
    if not os.path.exists(cfg.processed_log_file):
        return set()
    with open(cfg.processed_log_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)


def log_processed_file(file_path, cfg: ProcessMediaConfig | None = None):
    """Appends a successfully processed media file path to the log."""
    if cfg is None:
        raise ValueError("cfg is required for log_processed_file")
    with open(cfg.processed_log_file, 'a', encoding='utf-8') as f:
        f.write(file_path + '\n')


def normalize_archive_key(name):
    return f"archive:{os.path.normcase(name)}"


def normalize_standalone_key(path):
    normalized_path = os.path.normcase(os.path.abspath(os.path.normpath(path)))
    return f"standalone:{normalized_path}"


def normalize_work_item_key(raw_key):
    if raw_key.startswith("archive:"):
        return normalize_archive_key(raw_key[len("archive:"):].strip())
    if raw_key.startswith("standalone:"):
        return normalize_standalone_key(raw_key[len("standalone:"):].strip())
    return None


def get_processed_work_items(cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for get_processed_work_items")
    processed = set()
    if os.path.exists(cfg.processed_work_items_log_file):
        with open(cfg.processed_work_items_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                key = normalize_work_item_key(line.strip())
                if key:
                    processed.add(key)

    # Backwards compatibility: merge older logs if they exist.
    if os.path.exists(cfg.processed_archives_log_file):
        with open(cfg.processed_archives_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                name = line.strip()
                if name:
                    processed.add(normalize_archive_key(name))
    if os.path.exists(cfg.processed_standalone_log_file):
        with open(cfg.processed_standalone_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                path = line.strip()
                if path:
                    processed.add(normalize_standalone_key(path))

    return processed


def log_processed_work_item(work_item_key, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for log_processed_work_item")
    normalized_key = normalize_work_item_key(work_item_key)
    if not normalized_key:
        return
    with open(cfg.processed_work_items_log_file, 'a', encoding='utf-8') as f:
        f.write(normalized_key + '\n')


def log_fallback_used(media_path, reason, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for log_fallback_used")
    with open(cfg.fallback_used_log_file, 'a', encoding='utf-8') as f:
        f.write(f"{media_path}|{reason}\n")


def log_path_too_long(media_path, dest_path, path_length, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for log_path_too_long")
    with open(cfg.path_too_long_log_file, 'a', encoding='utf-8') as f:
        f.write(f"{media_path}|{dest_path}|{path_length}\n")


def log_exiftool_failure(media_path, error_msg, cfg: ProcessMediaConfig | None = None):
    if cfg is None:
        raise ValueError("cfg is required for log_exiftool_failure")
    with open(cfg.exiftool_failures_log_file, 'a', encoding='utf-8') as f:
        f.write(f"{media_path}|{error_msg}\n")
